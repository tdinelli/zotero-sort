"""`collections`: print the collection tree with item counts."""

from zotero_sort.commands._shared import connect, fetch_tree
from zotero_sort.config import Config
from zotero_sort.tree import PATH_SEPARATOR


INDENT = "    "


def run(config: Config) -> int:
    tree = fetch_tree(connect(config))
    for path in tree.paths():
        depth = path.count(PATH_SEPARATOR)
        name = path.rsplit(PATH_SEPARATOR, 1)[-1]
        item_count = tree.collection(tree.key_of(path)).item_count
        print(f"{INDENT * depth}{name}  ({item_count})")
    return 0
