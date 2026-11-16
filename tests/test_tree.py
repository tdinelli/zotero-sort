from zotero_sort.tree import Collection, CollectionTree


def test_paths_are_built_from_parents(tree):
    assert tree.paths() == [
        "Fuels",
        "Fuels/Ammonia",
        "Fuels/Soot",
        "Inbox",
        "Software",
    ]
    assert tree.key_of("Fuels/Soot") == "SOOT0000"
    assert tree.path_of("AMMONIA0") == "Fuels/Ammonia"
    assert tree.key_of("Fuels/Missing") is None


def test_leaf_paths_skip_parents_and_excluded(tree):
    assert tree.has_subcollections("FUELS000")
    assert not tree.has_subcollections("SOOT0000")
    assert tree.leaf_paths(exclude=["Inbox"]) == [
        "Fuels/Ammonia",
        "Fuels/Soot",
        "Software",
    ]


def test_from_api_treats_false_parent_as_top_level():
    raw = [
        {
            "key": "TOP00000",
            "data": {"name": "Top", "parentCollection": False},
            "meta": {"numItems": 3},
        },
        {
            "key": "CHILD000",
            "data": {"name": "Child", "parentCollection": "TOP00000"},
            "meta": {},
        },
    ]
    tree = CollectionTree.from_api(raw)
    assert tree.paths() == ["Top", "Top/Child"]
    assert tree.collection("TOP00000").item_count == 3
    assert tree.collection("CHILD000").item_count == 0


def test_orphaned_parent_key_falls_back_to_top_level():
    tree = CollectionTree(
        [
            Collection(
                key="ORPHAN00",
                name="Orphan",
                parent_key="GONE0000",
                item_count=0,
            )
        ]
    )
    assert tree.paths() == ["Orphan"]
