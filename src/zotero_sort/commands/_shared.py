"""Helpers shared by several commands."""

from zotero_sort.api import ZoteroClient
from zotero_sort.config import Config
from zotero_sort.errors import ZoteroSortError
from zotero_sort.items import NON_CONTENT_ITEM_TYPES, ItemSummary
from zotero_sort.tree import CollectionTree


def connect(config: Config) -> ZoteroClient:
    return ZoteroClient.connect(config.read_api_key(), config.library)


def fetch_tree(client: ZoteroClient) -> CollectionTree:
    return CollectionTree.from_api(client.get_all("/collections"))


def fetch_library_items(client: ZoteroClient) -> list[ItemSummary]:
    """
    All top-level items except notes and annotations (standalone attachments
    are kept).
    """
    return [
        ItemSummary.from_api(raw_item)
        for raw_item in client.iter_all("/items/top")
        if raw_item["data"]["itemType"] not in NON_CONTENT_ITEM_TYPES
    ]


def require_inbox_key(tree: CollectionTree, inbox_name: str) -> str:
    inbox_key = tree.key_of(inbox_name)
    if inbox_key is None:
        raise ZoteroSortError(
            f"no top-level collection named {inbox_name!r} (create it in Zotero, or set `inbox`)"
        )
    return inbox_key
