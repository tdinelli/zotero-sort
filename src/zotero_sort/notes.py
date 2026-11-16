"""
The user's notes file (notes.md): general rules, tag vocabulary and
per-collection criteria.

Only three level-1 sections are read; anything else, and every
`<!-- comment -->`, is ignored:

    # General rules     free text that applies to every decision
    # Tags              the allowed tag vocabulary
    # Collections       one "## <full collection path>" section per collection
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


GENERAL_RULES_HEADING = "general rules"
TAGS_HEADING = "tags"
COLLECTIONS_HEADING = "collections"
HTML_COMMENT = re.compile(r"<!--.*?-->", flags=re.DOTALL)

SKELETON_HEADER = """\
# General rules

- File each item in 1-3 collections, the most specific subcollection that fits.
- If nothing fits, propose a new collection instead of forcing a bad fit.

# Tags

<!-- list the tags that may be suggested, e.g. `#review`, `#experiment`; leave empty for no tags -->

# Collections
"""


@dataclass(frozen=True)
class Notes:
    general_rules: str = ""
    tags: str = ""
    collection_notes: dict[str, str] = field(default_factory=dict)

    def notes_for(self, collection_path: str) -> str:
        return self.collection_notes.get(collection_path, "")


def parse_notes(text: str) -> Notes:
    general_rule_lines: list[str] = []
    tag_lines: list[str] = []
    lines_by_collection: dict[str, list[str]] = {}
    current_section: str | None = None
    current_collection: str | None = None

    for line in text.splitlines():
        if line.startswith("# "):
            current_section = line.removeprefix("# ").strip().lower()
            current_collection = None
        elif current_section == COLLECTIONS_HEADING and line.startswith("## "):
            current_collection = line.removeprefix("## ").strip()
            lines_by_collection[current_collection] = []
        elif current_section == GENERAL_RULES_HEADING:
            general_rule_lines.append(line)
        elif current_section == TAGS_HEADING:
            tag_lines.append(line)
        elif (
            current_section == COLLECTIONS_HEADING
            and current_collection is not None
        ):
            lines_by_collection[current_collection].append(line)

    return Notes(
        general_rules=clean_section(general_rule_lines),
        tags=clean_section(tag_lines),
        collection_notes={
            path: clean_section(lines)
            for path, lines in lines_by_collection.items()
        },
    )


def clean_section(lines: list[str]) -> str:
    return HTML_COMMENT.sub("", "\n".join(lines)).strip()


def load_notes(notes_file: Path) -> Notes | None:
    """
    None when the file does not exist: classification then relies on examples
    only.
    """
    if not notes_file.exists():
        return None
    return parse_notes(notes_file.read_text())


def render_skeleton(collection_paths: Iterable[str]) -> str:
    sections = "".join(f"\n## {path}\n\n" for path in collection_paths)
    return SKELETON_HEADER + sections
