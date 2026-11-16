"""
Retry and write policy of ZoteroClient, with urlopen replaced by a scripted
fake (no network).
"""

import io
import json
import urllib.error
from email.message import Message

import pytest

from zotero_sort import api
from zotero_sort.api import KeyAccess, ZoteroClient
from zotero_sort.errors import ApiError, WriteError


class FakeResponse:
    def __init__(self, body, headers=None, status=200):
        self._body = json.dumps(body).encode() if body is not None else b""
        self.status = status
        self.headers = make_headers(headers)

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def make_headers(values: dict | None) -> Message:
    headers = Message()
    for name, value in (values or {}).items():
        headers[name] = str(value)
    return headers


def http_error(
    status: int,
    headers: dict | None = None,
) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://api.zotero.org/x",
        status,
        "error",
        make_headers(headers),
        io.BytesIO(b"boom"),
    )


@pytest.fixture
def fake_api(monkeypatch):
    """Script the responses; records every request that was sent."""
    script, sent_requests = [], []

    def fake_urlopen(request, timeout):
        sent_requests.append(request)
        outcome = script.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(api.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(api.time, "sleep", lambda seconds: None)
    return script, sent_requests


@pytest.fixture
def client() -> ZoteroClient:
    return ZoteroClient(
        "secret",
        "/users/1",
        KeyAccess(user_id="1", can_read=True, can_write=True),
    )


def test_connect_resolves_user_library_and_permissions(fake_api):
    script, sent_requests = fake_api
    script.append(
        FakeResponse(
            {
                "userID": 42,
                "access": {"user": {"library": True, "write": False}},
            }
        )
    )
    client = ZoteroClient.connect("secret", api.LibraryRef(kind="user"))
    assert client.library_prefix == "/users/42"
    assert client.key_access == KeyAccess(
        user_id="42", can_read=True, can_write=False
    )
    request = sent_requests[0]
    assert request.get_header("Zotero-api-key") == "secret"
    assert request.get_header("Zotero-api-version") == "3"
    assert "secret" not in request.full_url


def test_get_all_pages_through_results(fake_api, client):
    script, sent_requests = fake_api
    script += [
        FakeResponse(
            [{"key": str(n)} for n in range(100)], {"Total-Results": 150}
        ),
        FakeResponse(
            [{"key": str(n)} for n in range(100, 150)], {"Total-Results": 150}
        ),
    ]
    assert len(client.get_all("/items/top")) == 150
    assert "start=100" in sent_requests[1].full_url
    assert "limit=100" in sent_requests[1].full_url


def test_get_retries_rate_limits_and_server_errors(fake_api, client):
    script, sent_requests = fake_api
    script += [
        http_error(429, {"Retry-After": 2}),
        http_error(502),
        FakeResponse([], {"Total-Results": 0}),
    ]
    assert client.get("/collections").body == []
    assert len(sent_requests) == 3


def test_client_errors_are_not_retried(fake_api, client):
    script, sent_requests = fake_api
    script.append(http_error(403))
    with pytest.raises(ApiError, match="HTTP 403"):
        client.get("/collections")
    assert len(sent_requests) == 1


def test_item_update_is_not_retried_on_ambiguous_server_error(fake_api, client):
    """
    A 502 on a POST may have been applied already; repeating it blindly is
    unsafe.
    """
    script, sent_requests = fake_api
    script.append(http_error(502))
    with pytest.raises(ApiError, match="HTTP 502"):
        client.update_items(
            [{"key": "ITEM0001", "version": 1, "collections": []}]
        )
    assert len(sent_requests) == 1


def test_collection_creation_uses_a_write_token_and_can_be_retried(
    fake_api, client
):
    script, sent_requests = fake_api
    script += [
        http_error(502),
        FakeResponse({"successful": {"0": {"key": "NEW00001"}}, "failed": {}}),
    ]
    created = client.create_collections(
        [{"name": "New", "parentCollection": False}]
    )
    assert created["0"]["key"] == "NEW00001"
    write_tokens = {
        request.get_header("Zotero-write-token") for request in sent_requests
    }
    assert (
        len(write_tokens) == 1 and None not in write_tokens
    )  # same token on the retry


def test_per_object_failures_raise_write_error(fake_api, client):
    script, _ = fake_api
    script.append(
        FakeResponse(
            {
                "successful": {},
                "failed": {
                    "0": {"code": 412, "message": "Item has been modified"}
                },
            }
        )
    )
    with pytest.raises(WriteError, match="412 Item has been modified"):
        client.update_items(
            [{"key": "ITEM0001", "version": 1, "collections": []}]
        )


def test_writes_are_batched_by_fifty(fake_api, client):
    script, sent_requests = fake_api
    script += [FakeResponse({"successful": {}, "failed": {}}) for _ in range(3)]
    client.update_items(
        [{"key": f"ITEM{n:04}", "version": 1} for n in range(120)]
    )
    assert [len(json.loads(request.data)) for request in sent_requests] == [
        50,
        50,
        20,
    ]
