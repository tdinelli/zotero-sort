"""
The filing plan: which collections and tags each Inbox item gets.

Plan file format (JSON):

    [{"key": "ABCD1234", "collections": ["Parent/Child"], "tags": ["#review"]}]
"""

import json
from dataclasses import dataclass
from pathlib import Path

from zotero_sort.errors import PlanError
from zotero_sort.tree import CollectionTree


@dataclass(frozen=True)
class PlanEntry:
    item_key: str
    collection_paths: tuple[str, ...]
    tags: tuple[str, ...] = ()


def load_plan(plan_file: Path) -> list[PlanEntry]:
    try:
        raw_plan = json.loads(plan_file.read_text())
    except FileNotFoundError:
        raise PlanError(f"plan file not found: {plan_file}") from None
    except json.JSONDecodeError as error:
        raise PlanError(f"{plan_file} is not valid JSON: {error}") from None

    return parse_plan(raw_plan)


def parse_plan(raw_plan: object) -> list[PlanEntry]:
    if not isinstance(raw_plan, list):
        raise PlanError("plan must be a JSON list of entries")

    entries, seen_keys = [], set()
    for index, raw_entry in enumerate(raw_plan):
        if not isinstance(raw_entry, dict):
            raise PlanError(f"entry #{index} must be an object")

        item_key = raw_entry.get("key")
        collection_paths = raw_entry.get("collections")
        tags = raw_entry.get("tags", [])
        if not isinstance(item_key, str) or not item_key:
            raise PlanError(f"entry #{index}: `key` must be a non-empty string")

        if item_key in seen_keys:
            raise PlanError(
                f"entry #{index}: item {item_key} appears more than once"
            )
        if not is_string_list(collection_paths) or not collection_paths:
            raise PlanError(
                f"entry #{index} ({item_key}): `collections` must be a non-empty list of paths"
            )
        if not is_string_list(tags):
            raise PlanError(
                f"entry #{index} ({item_key}): `tags` must be a list of strings"
            )

        seen_keys.add(item_key)
        entries.append(
            PlanEntry(item_key, tuple(collection_paths), tuple(tags))
        )

    return entries


def is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(element, str) for element in value
    )


def validate_against_tree(
    entries: list[PlanEntry],
    tree: CollectionTree,
) -> None:
    unknown_paths = sorted(
        {
            path
            for entry in entries
            for path in entry.collection_paths
            if tree.key_of(path) is None
        }
    )
    if unknown_paths:
        raise PlanError(
            "unknown collections (create them first with `mkcol`): "
            + "; ".join(unknown_paths)
        )


def build_item_update(
    raw_item: dict,
    entry: PlanEntry,
    tree: CollectionTree,
    inbox_key: str | None,
) -> dict:
    """
    Partial-update payload: add the plan's collections and tags, drop the
    Inbox, keep everything else.

    The item's `version` is included so that Zotero rejects the write (412) if
    the item changed meanwhile.
    """
    data = raw_item["data"]
    current_collection_keys = set(data.get("collections", []))
    planned_collection_keys = {
        tree.key_of(path) for path in entry.collection_paths
    }
    new_collection_keys = (
        current_collection_keys - {inbox_key}
    ) | planned_collection_keys

    current_tags = data.get("tags", [])
    existing_tag_names = {tag["tag"] for tag in current_tags}
    added_tags = [
        {"tag": tag} for tag in entry.tags if tag not in existing_tag_names
    ]

    return {
        "key": raw_item["key"],
        "version": raw_item["version"],
        "collections": sorted(new_collection_keys),
        "tags": current_tags + added_tags,
    }
