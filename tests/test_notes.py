from zotero_sort.notes import load_notes, parse_notes, render_skeleton


NOTES_TEXT = """\
Text before any section is ignored.

# General rules
- one to three collections
<!-- a comment
spanning lines -->

# Tags
- `#review`

# Collections
## Fuels/Ammonia
NH3 and NOx chemistry.

## Fuels/Soot

# Something else
ignored
"""


def test_parse_notes_reads_the_three_sections():
    notes = parse_notes(NOTES_TEXT)
    assert notes.general_rules == "- one to three collections"
    assert notes.tags == "- `#review`"
    assert notes.collection_notes == {
        "Fuels/Ammonia": "NH3 and NOx chemistry.",
        "Fuels/Soot": "",
    }
    assert notes.notes_for("Software") == ""


def test_headings_are_case_insensitive():
    notes = parse_notes("# GENERAL RULES\nbe brief\n# collections\n## A\nx\n")
    assert notes.general_rules == "be brief"
    assert notes.collection_notes == {"A": "x"}


def test_load_notes_returns_none_for_missing_file(tmp_path):
    assert load_notes(tmp_path / "missing.md") is None


def test_skeleton_round_trips_through_the_parser():
    skeleton = render_skeleton(["Fuels/Ammonia", "Software"])
    notes = parse_notes(skeleton)
    assert notes.collection_notes == {"Fuels/Ammonia": "", "Software": ""}
    assert notes.tags == ""  # the placeholder is a comment
    assert notes.general_rules
