"""
Minimal Zotero Web API v3 client
(https://www.zotero.org/support/dev/web_api/v3/basics).

Follows the API's guidance for well-behaved clients:
- sends `Zotero-API-Version` and a descriptive `User-Agent`; the key goes in a
  header, never in the URL;
- honours `Retry-After` (429/503) and `Backoff` headers, and retries transient
  failures with exponential backoff;
- retries a POST only when the server says it was not processed (429/503) or
  when it carries a `Zotero-Write-Token`, which makes object creation
  idempotent;
- pages through results with `start`/`limit` and the `Total-Results` header;
- writes at most 50 objects per request and reports per-object failures (e.g.
  412 version conflicts).
"""

import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from email.message import Message
from typing import Any

from zotero_sort import __version__
from zotero_sort.config import LibraryRef
from zotero_sort.errors import ApiError, WriteError


API_BASE_URL = "https://api.zotero.org"
API_VERSION = "3"
USER_AGENT = f"zotero-sort/{__version__}"
REQUEST_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 5
INITIAL_RETRY_DELAY_SECONDS = 1.0
PAGE_SIZE = 100  # maximum allowed by the API
WRITE_BATCH_SIZE = 50  # maximum objects per write request
ITEM_KEY_BATCH_SIZE = 50  # maximum keys in one itemKey= filter
SERVER_SAID_RETRY_STATUSES = {
    429,
    503,
}  # request was not processed, safe to repeat
TRANSIENT_STATUSES = {500, 502, 504}


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: Any
    headers: Message

    @property
    def total_results(self) -> int:
        return int(self.headers.get("Total-Results", 0))


@dataclass(frozen=True)
class KeyAccess:
    """What the API key is allowed to do, from GET /keys/current."""

    user_id: str
    can_read: bool
    can_write: bool


class ZoteroClient:
    """
    Talks to one library (`/users/<id>` or `/groups/<id>`) with one API key.
    """

    def __init__(
        self,
        api_key: str,
        library_prefix: str,
        key_access: KeyAccess,
    ) -> None:
        self._api_key = api_key
        self.library_prefix = library_prefix
        self.key_access = key_access
        self._next_request_not_before = 0.0  # monotonic time

    @classmethod
    def connect(cls, api_key: str, library: LibraryRef) -> "ZoteroClient":
        """
        Resolve the library and the key's permissions with a single GET
        /keys/current.
        """
        bootstrap = cls(
            api_key,
            library_prefix="",
            key_access=KeyAccess("", False, False),
        )
        key_info = bootstrap._request(
            "GET", f"{API_BASE_URL}/keys/current"
        ).body
        user_id = str(key_info["userID"])
        access = key_info.get("access", {})

        if library.kind == "user":
            library_prefix = f"/users/{user_id}"
            permissions = access.get("user", {})
        else:
            library_prefix = f"/groups/{library.library_id}"
            group_access = access.get("groups", {})
            permissions = group_access.get(
                library.library_id
            ) or group_access.get("all", {})

        key_access = KeyAccess(
            user_id=user_id,
            can_read=bool(permissions.get("library")),
            can_write=bool(permissions.get("write")),
        )

        return cls(api_key, library_prefix, key_access)

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> ApiResponse:
        return self._request("GET", self._url(path, params))

    def iter_all(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Iterator[dict]:
        """Yield every object of a multi-object endpoint, one page at a time."""
        start = 0
        while True:
            page = self.get(
                path,
                {
                    **(params or {}),
                    "limit": PAGE_SIZE,
                    "start": start,
                },
            )
            yield from page.body
            start += PAGE_SIZE
            if start >= page.total_results or not page.body:
                return

    def get_all(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict]:
        return list(self.iter_all(path, params))

    def get_items_by_key(self, item_keys: list[str]) -> list[dict]:
        """Fetch items by key, in batches of the API's maximum."""
        items: list[dict] = []
        for batch in batched(item_keys, ITEM_KEY_BATCH_SIZE):
            items += self.get(
                "/items",
                {
                    "itemKey": ",".join(batch),
                    "limit": len(batch),
                },
            ).body
        return items

    def create_collections(
        self,
        new_collections: list[dict],
    ) -> dict[str, dict]:
        """
        Create collections; returns the `successful` map
        (request index -> created object).
        """
        successful: dict[str, dict] = {}

        for batch in batched(new_collections, WRITE_BATCH_SIZE):
            successful |= self._write("/collections", batch, idempotent=True)

        return successful

    def update_items(self, item_updates: list[dict]) -> None:
        """
        Partially update items; each update must carry `key` and the `version`
        it was based on.
        """
        for batch in batched(item_updates, WRITE_BATCH_SIZE):
            self._write("/items", batch, idempotent=False)

    def _write(
        self,
        path: str,
        objects: list[dict],
        *,
        idempotent: bool,
    ) -> dict[str, dict]:
        extra_headers = (
            {"Zotero-Write-Token": secrets.token_hex(16)} if idempotent else {}
        )
        response = self._request(
            "POST",
            self._url(path),
            body=objects,
            extra_headers=extra_headers,
        )

        result = response.body or {}
        if result.get("failed"):
            raise WriteError(result["failed"])

        return result.get("successful", {})

    def _url(self, path: str, params: dict[str, Any] | None = None) -> str:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        return f"{API_BASE_URL}{self.library_prefix}{path}{query}"

    def _request(
        self,
        method: str,
        url: str,
        body: Any = None,
        extra_headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        headers = {
            "Zotero-API-Key": self._api_key,
            "Zotero-API-Version": API_VERSION,
            "User-Agent": USER_AGENT,
            **(extra_headers or {}),
        }

        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"

        can_retry_on_transient_error = (
            method == "GET" or "Zotero-Write-Token" in headers
        )

        retry_delay = INITIAL_RETRY_DELAY_SECONDS
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._wait_for_backoff()
            request = urllib.request.Request(
                url,
                data=payload,
                headers=headers,
                method=method,
            )

            try:
                with urllib.request.urlopen(
                    request,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                ) as response:
                    self._record_backoff(response.headers)
                    raw_body = response.read()
                    return ApiResponse(
                        response.status,
                        json.loads(raw_body) if raw_body else None,
                        response.headers,
                    )
            except urllib.error.HTTPError as error:
                self._record_backoff(error.headers)
                detail = error.read().decode(errors="replace")[:400]
                retryable = error.code in SERVER_SAID_RETRY_STATUSES or (
                    error.code in TRANSIENT_STATUSES
                    and can_retry_on_transient_error
                )
                if not retryable or attempt == MAX_ATTEMPTS:
                    raise ApiError(
                        method,
                        redact(url),
                        error.code,
                        detail,
                    ) from None
                time.sleep(
                    retry_after_seconds(error.headers, default=retry_delay)
                )
            except (urllib.error.URLError, TimeoutError) as error:
                if not can_retry_on_transient_error or attempt == MAX_ATTEMPTS:
                    raise ApiError(
                        method,
                        redact(url),
                        None,
                        str(getattr(error, "reason", error)),
                    ) from None
                time.sleep(retry_delay)

            retry_delay *= 2

        raise AssertionError("unreachable")

    def _record_backoff(self, headers: Message | None) -> None:
        """
        The API sends `Backoff: <seconds>` when it is under load; pause before
        the next request.
        """
        if headers and headers.get("Backoff", "").isdigit():
            self._next_request_not_before = time.monotonic() + int(
                headers["Backoff"]
            )

    def _wait_for_backoff(self) -> None:
        remaining = self._next_request_not_before - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)


def retry_after_seconds(headers: Message | None, default: float) -> float:
    value = headers.get("Retry-After", "") if headers else ""
    return float(value) if value.isdigit() else default


def redact(url: str) -> str:
    """
    URLs never contain the key (it is sent as a header), but strip the query
    string from error messages anyway.
    """
    return url.split("?", 1)[0]


def batched(sequence: list, size: int) -> Iterator[list]:
    for start in range(0, len(sequence), size):
        yield sequence[start : start + size]
