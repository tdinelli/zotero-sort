"""
`context`: everything Claude needs to classify the Inbox, as one JSON document
on stdout.

The JSON keys are camelCase because SKILL.md refers to them by these names.
"""

import json

from zotero_sort.commands._shared import (
    connect,
    fetch_library_items,
    fetch_tree,
    require_inbox_key,
)
from zotero_sort.config import Config
from zotero_sort.drift import find_drift
from zotero_sort.items import DuplicateIndex, ItemSummary
from zotero_sort.notes import Notes, load_notes
from zotero_sort.tree import CollectionTree


def run(config: Config) -> int:
    client = connect(config)
    tree = fetch_tree(client)
    inbox_key = require_inbox_key(tree, config.inbox_name)
    library_items = fetch_library_items(client)
    notes = load_notes(config.notes_file)
    warnings = find_drift(
        tree,
        notes,
        inbox_name=config.inbox_name,
        notes_file=config.notes_file,
        can_write=client.key_access.can_write,
    )
    context = build_context(
        tree,
        library_items,
        notes,
        warnings,
        inbox_key=inbox_key,
        config=config,
    )
    print(json.dumps(context, indent=1, ensure_ascii=False))
    return 0


def build_context(
    tree: CollectionTree,
    library_items: list[ItemSummary],
    notes: Notes | None,
    warnings: list[str],
    *,
    inbox_key: str,
    config: Config,
) -> dict:
    notes = notes or Notes()
    items_by_key = {item.key: item for item in library_items}
    duplicate_index = DuplicateIndex(library_items)

    members_by_collection: dict[str, list[ItemSummary]] = {}
    for item in library_items:
        for collection_key in item.collection_keys:
            members_by_collection.setdefault(collection_key, []).append(item)

    def known_paths(
        collection_keys: tuple[str, ...],
        skip_key: str | None = None,
    ) -> list[str]:
        return [
            tree.path_of(key)
            for key in collection_keys
            if key in tree and key != skip_key
        ]

    inbox_items = [
        {
            "key": item.key,
            "itemType": item.item_type,
            "title": item.title,
            "firstAuthor": item.first_author,
            "year": item.year,
            "publication": item.publication,
            "DOI": item.doi,
            "abstract": item.abstract,
            "tags": list(item.tags),
            "alsoIn": known_paths(item.collection_keys, skip_key=inbox_key),
            "standaloneAttachment": item.is_standalone_attachment,
            "possibleDuplicates": [
                {
                    "key": duplicate_key,
                    "title": items_by_key[duplicate_key].title,
                    "collections": known_paths(
                        items_by_key[duplicate_key].collection_keys
                    ),
                }
                for duplicate_key in duplicate_index.find_duplicates(item)
            ],
        }
        for item in members_by_collection.get(inbox_key, [])
    ]

    collections = []
    for path in tree.paths():
        collection_key = tree.key_of(path)
        if collection_key == inbox_key:
            continue
        most_recent_first = sorted(
            members_by_collection.get(collection_key, []),
            key=lambda item: item.date_added,
            reverse=True,
        )
        collections.append(
            {
                "path": path,
                "items": tree.collection(collection_key).item_count,
                "hasSubcollections": tree.has_subcollections(collection_key),
                "notes": notes.notes_for(path),
                "examples": [
                    item.title
                    for item in most_recent_first[
                        : config.examples_per_collection
                    ]
                ],
            }
        )

    return {
        "inbox": {
            "name": config.inbox_name,
            "count": len(inbox_items),
            "items": inbox_items,
        },
        "generalRules": notes.general_rules,
        "tags": notes.tags,
        "collections": collections,
        "warnings": warnings,
        "notesFile": str(config.notes_file),
    }
