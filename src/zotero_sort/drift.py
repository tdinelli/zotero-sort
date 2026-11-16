"""
Detect when the notes file no longer matches the live collection tree.
"""

from pathlib import Path

from zotero_sort.notes import Notes
from zotero_sort.tree import CollectionTree


def find_drift(
    tree: CollectionTree,
    notes: Notes | None,
    *,
    inbox_name: str,
    notes_file: Path,
    can_write: bool,
) -> list[str]:
    """
    Human-readable warnings; an empty list means notes and tree agree.

    Parents with subcollections never receive items directly, so they need no
    notes (notes for them are allowed).
    """
    warnings = []
    if not can_write:
        warnings.append(
            "API key has no write access: `apply` and `mkcol` will fail"
        )
    if notes is None:
        warnings.append(
            f"no notes file at {notes_file}: run `init` (classification will rely on examples only)"
        )
        return warnings

    leaf_paths = set(tree.leaf_paths(exclude=[inbox_name]))
    noted_paths = set(notes.collection_notes)
    all_paths = set(tree.paths())

    warnings += [
        f"collection missing from notes: {path}"
        for path in sorted(leaf_paths - noted_paths)
    ]
    warnings += [
        f"notes describe a collection that no longer exists (renamed or deleted?): {path}"
        for path in sorted(noted_paths - all_paths)
    ]
    warnings += [
        f"collection has an empty notes section: {path}"
        for path in sorted(leaf_paths & noted_paths)
        if not notes.notes_for(path)
    ]

    if not notes.tags:
        warnings.append("no tag vocabulary in notes: no tags will be suggested")

    return warnings
