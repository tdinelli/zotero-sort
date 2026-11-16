"""
Library items: a compact summary of each item and duplicate detection by DOI
and title.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass


NON_CONTENT_ITEM_TYPES = {"note", "annotation"}
ABSTRACT_MAX_CHARS = 1500


@dataclass(frozen=True)
class ItemSummary:
    key: str
    item_type: str
    title: str
    first_author: str
    year: str
    publication: str
    doi: str
    abstract: str
    tags: tuple[str, ...]
    collection_keys: tuple[str, ...]
    date_added: str

    @classmethod
    def from_api(cls, raw_item: dict) -> "ItemSummary":
        data = raw_item["data"]
        first_creator = (data.get("creators") or [{}])[0]
        years_in_date = re.findall(r"\d{4}", data.get("date") or "")
        return cls(
            key=raw_item["key"],
            item_type=data["itemType"],
            title=data.get("title", ""),
            first_author=first_creator.get("lastName")
            or first_creator.get("name")
            or "",
            year=years_in_date[0] if years_in_date else "",
            publication=data.get("publicationTitle")
            or data.get("proceedingsTitle")
            or data.get("repository")
            or "",
            doi=data.get("DOI", ""),
            abstract=(data.get("abstractNote") or "")[:ABSTRACT_MAX_CHARS],
            tags=tuple(tag["tag"] for tag in data.get("tags", [])),
            collection_keys=tuple(data.get("collections", [])),
            date_added=data.get("dateAdded", ""),
        )

    @property
    def is_standalone_attachment(self) -> bool:
        """
        A file without a parent item, i.e. Zotero could not retrieve its
        metadata.
        """
        return self.item_type == "attachment"


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())


class DuplicateIndex:
    """
    Finds library items that share a DOI or a normalized title with a given
    item.
    """

    def __init__(self, items: Iterable[ItemSummary]) -> None:
        self._keys_by_doi: dict[str, set[str]] = {}
        self._keys_by_title: dict[str, set[str]] = {}
        for item in items:
            if item.doi:
                self._keys_by_doi.setdefault(item.doi.lower(), set()).add(
                    item.key
                )
            if normalize_title(item.title):
                self._keys_by_title.setdefault(
                    normalize_title(item.title), set()
                ).add(item.key)

    def find_duplicates(self, item: ItemSummary) -> list[str]:
        matches = set()
        if item.doi:
            matches |= self._keys_by_doi.get(item.doi.lower(), set())
        if normalize_title(item.title):
            matches |= self._keys_by_title.get(
                normalize_title(item.title), set()
            )
        matches.discard(item.key)

        return sorted(matches)
