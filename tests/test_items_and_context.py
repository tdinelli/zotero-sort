from pathlib import Path

from zotero_sort.commands.context import build_context
from zotero_sort.config import config_from_settings
from zotero_sort.items import DuplicateIndex, ItemSummary, normalize_title
from zotero_sort.notes import Notes

from .conftest import make_raw_item


def test_item_summary_extracts_fields():
    raw_item = make_raw_item(
        "ITEM0001",
        "A Title",
        ["INBOX000"],
        creators=[{"firstName": "Ada", "lastName": "Lovelace"}],
        date="March 2024",
        publicationTitle="Combustion and Flame",
        DOI="10.1/ABC",
        abstractNote="x" * 5000,
    )
    item = ItemSummary.from_api(raw_item)
    assert (item.first_author, item.year, item.publication, item.doi) == (
        "Lovelace",
        "2024",
        "Combustion and Flame",
        "10.1/ABC",
    )
    assert len(item.abstract) == 1500
    assert not item.is_standalone_attachment


def test_duplicates_match_by_doi_or_normalized_title():
    existing_by_doi = ItemSummary.from_api(
        make_raw_item("OLD00001", "Other title", [], DOI="10.1/abc")
    )
    existing_by_title = ItemSummary.from_api(
        make_raw_item("OLD00002", "Rate Constants: H + O2!", [])
    )
    new_item = ItemSummary.from_api(
        make_raw_item("NEW00001", "rate constants h o2", [], DOI="10.1/ABC")
    )
    index = DuplicateIndex([existing_by_doi, existing_by_title, new_item])
    assert index.find_duplicates(new_item) == ["OLD00001", "OLD00002"]
    assert normalize_title("H + O2 (+M)") == "ho2m"


def test_build_context_shape(tree):
    config = config_from_settings(
        {"examples_per_collection": 1}, Path("/config")
    )
    library_items = [
        ItemSummary.from_api(
            make_raw_item(
                "NEW00001", "NH3 shock tube", ["INBOX000"], DOI="10.1/x"
            )
        ),
        ItemSummary.from_api(
            make_raw_item(
                "OLD00001", "NH3 older", ["AMMONIA0"], dateAdded="2024-01-01"
            )
        ),
        ItemSummary.from_api(
            make_raw_item(
                "OLD00002",
                "NH3 newer",
                ["AMMONIA0"],
                dateAdded="2025-01-01",
                DOI="10.1/X",
            )
        ),
    ]
    notes = Notes(
        general_rules="rules",
        tags="#review",
        collection_notes={"Fuels/Ammonia": "NH3"},
    )

    context = build_context(
        tree,
        library_items,
        notes,
        ["a warning"],
        inbox_key="INBOX000",
        config=config,
    )

    assert context["inbox"]["count"] == 1
    inbox_item = context["inbox"]["items"][0]
    assert inbox_item["possibleDuplicates"] == [
        {
            "key": "OLD00002",
            "title": "NH3 newer",
            "collections": ["Fuels/Ammonia"],
        }
    ]
    assert inbox_item["alsoIn"] == []
    ammonia = next(
        collection
        for collection in context["collections"]
        if collection["path"] == "Fuels/Ammonia"
    )
    assert ammonia == {
        "path": "Fuels/Ammonia",
        "items": 2,
        "hasSubcollections": False,
        "notes": "NH3",
        "examples": ["NH3 newer"],
    }
    assert "Inbox" not in [
        collection["path"] for collection in context["collections"]
    ]
    assert (context["generalRules"], context["tags"], context["warnings"]) == (
        "rules",
        "#review",
        ["a warning"],
    )
