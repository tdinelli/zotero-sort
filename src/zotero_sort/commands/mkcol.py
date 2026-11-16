"""`mkcol`: create one collection; its parent must already exist."""

from zotero_sort.commands._shared import connect, fetch_tree
from zotero_sort.config import Config
from zotero_sort.errors import ZoteroSortError
from zotero_sort.tree import PATH_SEPARATOR


def run(config: Config, collection_path: str) -> int:
    client = connect(config)
    tree = fetch_tree(client)
    if tree.key_of(collection_path) is not None:
        print(f"exists: {collection_path}")
        return 0

    parent_path, _, name = collection_path.rpartition(PATH_SEPARATOR)
    if not name:
        raise ZoteroSortError(f"invalid collection path {collection_path!r}")

    parent_key = tree.key_of(parent_path) if parent_path else None
    if parent_path and parent_key is None:
        raise ZoteroSortError(
            f"parent collection {parent_path!r} does not exist (create it first)"
        )

    client.create_collections(
        [{"name": name, "parentCollection": parent_key or False}]
    )
    print(f"created: {collection_path}")

    return 0
