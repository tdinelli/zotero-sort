"""
The collection tree, addressed by slash-separated paths such as
"Fuels & Mechanisms/Soot".

Collection names that themselves contain "/" would make paths ambiguous;
Zotero allows them, this tool does not support them.
"""

from collections.abc import Iterable
from dataclasses import dataclass


PATH_SEPARATOR = "/"


@dataclass(frozen=True)
class Collection:
    key: str
    name: str
    parent_key: str | None
    item_count: int

    @classmethod
    def from_api(cls, raw_collection: dict) -> "Collection":
        data = raw_collection["data"]
        return cls(
            key=raw_collection["key"],
            name=data["name"],
            parent_key=data.get("parentCollection")
            or None,  # the API uses `false` for top-level collections
            item_count=raw_collection.get("meta", {}).get("numItems", 0),
        )


class CollectionTree:
    def __init__(self, collections: Iterable[Collection]) -> None:
        self._by_key = {
            collection.key: collection for collection in collections
        }
        self._parent_keys = {
            collection.parent_key for collection in self._by_key.values()
        }
        self._path_by_key = {key: self._build_path(key) for key in self._by_key}
        self._key_by_path = {
            path: key for key, path in self._path_by_key.items()
        }

    @classmethod
    def from_api(cls, raw_collections: Iterable[dict]) -> "CollectionTree":
        return cls(Collection.from_api(raw) for raw in raw_collections)

    def _build_path(self, key: str) -> str:
        collection = self._by_key[key]
        if (
            collection.parent_key is None
            or collection.parent_key not in self._by_key
        ):
            return collection.name
        return (
            self._build_path(collection.parent_key)
            + PATH_SEPARATOR
            + collection.name
        )

    def __contains__(self, key: str) -> bool:
        return key in self._by_key

    def collection(self, key: str) -> Collection:
        return self._by_key[key]

    def path_of(self, key: str) -> str:
        return self._path_by_key[key]

    def key_of(self, path: str) -> str | None:
        return self._key_by_path.get(path)

    def paths(self) -> list[str]:
        return sorted(self._key_by_path)

    def has_subcollections(self, key: str) -> bool:
        return key in self._parent_keys

    def leaf_paths(self, exclude: Iterable[str] = ()) -> list[str]:
        """
        Paths of collections without subcollections: the only ones items get
        filed into.
        """
        excluded = set(exclude)
        return [
            path
            for path in self.paths()
            if path not in excluded
            and not self.has_subcollections(self.key_of(path))
        ]
