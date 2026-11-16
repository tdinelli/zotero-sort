"""
`check`: compare notes.md with the live collection tree. Exit code 1 when there
are warnings.
"""

from zotero_sort.commands._shared import connect, fetch_tree
from zotero_sort.config import Config
from zotero_sort.drift import find_drift
from zotero_sort.notes import load_notes


def run(config: Config) -> int:
    client = connect(config)
    warnings = find_drift(
        fetch_tree(client),
        load_notes(config.notes_file),
        inbox_name=config.inbox_name,
        notes_file=config.notes_file,
        can_write=client.key_access.can_write,
    )
    for warning in warnings:
        print(f"WARN {warning}")
    if warnings:
        print(f"{len(warnings)} warning(s)")
        return 1
    print("ok: notes match the collection tree")
    return 0
