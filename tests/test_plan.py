import json

import pytest

from zotero_sort.errors import PlanError
from zotero_sort.plan import (
    PlanEntry,
    build_item_update,
    load_plan,
    parse_plan,
    validate_against_tree,
)

from .conftest import make_raw_item


def test_parse_plan_accepts_valid_entries():
    entries = parse_plan(
        [{"key": "ITEM0001", "collections": ["Software"], "tags": ["#review"]}]
    )
    assert entries == [PlanEntry("ITEM0001", ("Software",), ("#review",))]


@pytest.mark.parametrize(
    ("raw_plan", "message"),
    [
        ({"key": "X"}, "JSON list"),
        (["not an object"], "must be an object"),
        ([{"collections": ["A"]}], "`key`"),
        ([{"key": "X", "collections": []}], "`collections`"),
        ([{"key": "X", "collections": "A"}], "`collections`"),
        ([{"key": "X", "collections": ["A"], "tags": "#review"}], "`tags`"),
        (
            [
                {"key": "X", "collections": ["A"]},
                {"key": "X", "collections": ["B"]},
            ],
            "more than once",
        ),
    ],
)
def test_parse_plan_rejects_malformed_entries(raw_plan, message):
    with pytest.raises(PlanError, match=message):
        parse_plan(raw_plan)


def test_load_plan_reports_bad_json(tmp_path):
    plan_file = tmp_path / "plan.json"
    plan_file.write_text("[{")
    with pytest.raises(PlanError, match="not valid JSON"):
        load_plan(plan_file)
    plan_file.write_text(
        json.dumps([{"key": "ITEM0001", "collections": ["Software"]}])
    )
    assert load_plan(plan_file)[0].item_key == "ITEM0001"


def test_validate_against_tree_lists_unknown_paths(tree):
    entries = [
        PlanEntry("ITEM0001", ("Software", "Fuels/Nope")),
        PlanEntry("ITEM0002", ("Also/Missing",)),
    ]
    with pytest.raises(PlanError, match="Also/Missing; Fuels/Nope"):
        validate_against_tree(entries, tree)


def test_build_item_update_moves_out_of_inbox_and_keeps_other_collections(tree):
    raw_item = make_raw_item(
        "ITEM0001",
        "Ammonia pyrolysis",
        ["INBOX000", "SOFTWARE"],
        tags=[{"tag": "#review"}, {"tag": "auto", "type": 1}],
    )
    entry = PlanEntry(
        "ITEM0001", ("Fuels/Ammonia",), ("#review", "#experiment")
    )

    update = build_item_update(raw_item, entry, tree, inbox_key="INBOX000")

    assert update == {
        "key": "ITEM0001",
        "version": 7,
        "collections": ["AMMONIA0", "SOFTWARE"],
        "tags": [
            {"tag": "#review"},
            {"tag": "auto", "type": 1},
            {"tag": "#experiment"},
        ],
    }
