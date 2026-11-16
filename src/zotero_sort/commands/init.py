"""`init`: write a notes.md skeleton with one section per leaf collection."""

from zotero_sort.commands._shared import connect, fetch_tree
from zotero_sort.config import Config
from zotero_sort.errors import ZoteroSortError
from zotero_sort.notes import render_skeleton


def run(config: Config, *, overwrite: bool) -> int:
    notes_file = config.notes_file
    if notes_file.exists() and not overwrite:
        raise ZoteroSortError(
            f"{notes_file} already exists (edit it, or use --force to overwrite)"
        )
    leaf_paths = fetch_tree(connect(config)).leaf_paths(
        exclude=[config.inbox_name]
    )
    notes_file.parent.mkdir(parents=True, exist_ok=True)
    notes_file.write_text(render_skeleton(leaf_paths))
    print(f"wrote {notes_file} with {len(leaf_paths)} collection sections")

    return 0
