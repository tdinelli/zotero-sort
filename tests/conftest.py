import pytest

from zotero_sort.tree import Collection, CollectionTree


@pytest.fixture
def tree() -> CollectionTree:
    """Inbox
    Fuels/            (parent only)
        Ammonia
        Soot
    Software
    """
    return CollectionTree(
        [
            Collection(
                key="INBOX000", name="Inbox", parent_key=None, item_count=1
            ),
            Collection(
                key="FUELS000", name="Fuels", parent_key=None, item_count=0
            ),
            Collection(
                key="AMMONIA0",
                name="Ammonia",
                parent_key="FUELS000",
                item_count=2,
            ),
            Collection(
                key="SOOT0000", name="Soot", parent_key="FUELS000", item_count=0
            ),
            Collection(
                key="SOFTWARE", name="Software", parent_key=None, item_count=1
            ),
        ]
    )


def make_raw_item(
    key: str, title: str, collections: list[str], **data_fields
) -> dict:
    """An item as returned by the Zotero API."""
    return {
        "key": key,
        "version": 7,
        "data": {
            "key": key,
            "itemType": "journalArticle",
            "title": title,
            "collections": collections,
            **data_fields,
        },
    }
