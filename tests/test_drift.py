from pathlib import Path

from zotero_sort.drift import find_drift
from zotero_sort.notes import Notes


NOTES_FILE = Path("/config/notes.md")


def drift(tree, notes, can_write=True):
    return find_drift(
        tree,
        notes,
        inbox_name="Inbox",
        notes_file=NOTES_FILE,
        can_write=can_write,
    )


def complete_notes() -> Notes:
    return Notes(
        general_rules="rules",
        tags="#review",
        collection_notes={
            "Fuels/Ammonia": "NH3",
            "Fuels/Soot": "soot",
            "Software": "codes",
        },
    )


def test_matching_notes_give_no_warnings(tree):
    assert drift(tree, complete_notes()) == []


def test_parent_collections_need_no_notes_but_may_have_them(tree):
    notes = complete_notes()
    notes.collection_notes["Fuels"] = "parent notes are fine"
    assert drift(tree, notes) == []


def test_renamed_collection_is_reported_on_both_sides(tree):
    notes = complete_notes()
    notes.collection_notes["Old Software"] = notes.collection_notes.pop(
        "Software"
    )
    assert drift(tree, notes) == [
        "collection missing from notes: Software",
        "notes describe a collection that no longer exists (renamed or deleted?): Old Software",
    ]


def test_empty_section_and_missing_tags_are_reported(tree):
    notes = Notes(
        general_rules="",
        tags="",
        collection_notes={
            "Fuels/Ammonia": "NH3",
            "Fuels/Soot": "",
            "Software": "x",
        },
    )
    assert drift(tree, notes) == [
        "collection has an empty notes section: Fuels/Soot",
        "no tag vocabulary in notes: no tags will be suggested",
    ]


def test_missing_notes_file_and_read_only_key(tree):
    warnings = drift(tree, None, can_write=False)
    assert warnings[0].startswith("API key has no write access")
    assert str(NOTES_FILE) in warnings[1]
    assert len(warnings) == 2
