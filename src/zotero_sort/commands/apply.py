"""
`apply`: file items as described in a plan file. `--dry-run` only prints what
would change.
"""

from pathlib import Path

from zotero_sort.commands._shared import connect, fetch_tree
from zotero_sort.config import Config
from zotero_sort.errors import PlanError
from zotero_sort.plan import build_item_update, load_plan, validate_against_tree


TITLE_PREVIEW_CHARS = 60


def run(config: Config, plan_file: Path, *, dry_run: bool) -> int:
    plan_entries = load_plan(plan_file)
    client = connect(config)
    tree = fetch_tree(client)
    validate_against_tree(plan_entries, tree)
    inbox_key = tree.key_of(config.inbox_name)

    entry_by_key = {entry.item_key: entry for entry in plan_entries}
    raw_items = client.get_items_by_key(list(entry_by_key))
    missing_keys = sorted(
        set(entry_by_key) - {raw_item["key"] for raw_item in raw_items}
    )
    if missing_keys:
        raise PlanError(
            f"items not found in the library: {', '.join(missing_keys)}"
        )

    item_updates = []
    for raw_item in raw_items:
        entry = entry_by_key[raw_item["key"]]
        item_updates.append(build_item_update(raw_item, entry, tree, inbox_key))
        title_preview = raw_item["data"].get("title", "")[:TITLE_PREVIEW_CHARS]
        tag_text = f"   tags: {' '.join(entry.tags)}" if entry.tags else ""
        print(
            f"{raw_item['key']}  {title_preview!r}\n    -> {', '.join(entry.collection_paths)}{tag_text}"
        )

    if dry_run:
        print(f"\n[dry run] {len(item_updates)} items would be updated")
        return 0

    client.update_items(item_updates)
    remaining_in_inbox = (
        len(client.get_all(f"/collections/{inbox_key}/items/top"))
        if inbox_key
        else 0
    )
    print(
        f"\n{len(item_updates)} items updated; {remaining_in_inbox} left in {config.inbox_name}"
    )
    return 0
