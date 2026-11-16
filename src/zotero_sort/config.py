"""
User configuration: `~/.config/zotero-sort/config.toml`, every key optional.
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from zotero_sort.errors import ConfigError


CONFIG_DIR_ENV_VAR = "ZOTERO_SORT_CONFIG_DIR"
DEFAULT_CONFIG_DIR = Path("~/.config/zotero-sort")
CONFIG_FILE_NAME = "config.toml"
API_KEY_URL = "https://www.zotero.org/settings/keys/new"


@dataclass(frozen=True)
class LibraryRef:
    """
    Which Zotero library to work on. `library_id` is None for the user library
    until resolved from the key.
    """

    kind: str  # "user" or "group"
    library_id: str | None = None

    @classmethod
    def parse(cls, value: str) -> "LibraryRef":
        if value == "user":
            return cls(kind="user")
        if (
            value.startswith("group:")
            and value.removeprefix("group:").isdigit()
        ):
            return cls(kind="group", library_id=value.removeprefix("group:"))
        raise ConfigError(
            f"config: library must be 'user' or 'group:<numeric id>', not {value!r}"
        )


@dataclass(frozen=True)
class Config:
    config_dir: Path
    api_key_file: Path
    library: LibraryRef
    inbox_name: str
    examples_per_collection: int
    notes_file: Path

    def read_api_key(self) -> str:
        try:
            api_key = self.api_key_file.read_text().strip()
        except FileNotFoundError:
            raise ConfigError(
                f"no API key at {self.api_key_file} (create one at {API_KEY_URL})"
            ) from None

        if not api_key:
            raise ConfigError(f"API key file {self.api_key_file} is empty")

        return api_key


def resolve_config_dir() -> Path:
    return Path(
        os.environ.get(CONFIG_DIR_ENV_VAR, DEFAULT_CONFIG_DIR)
    ).expanduser()


def load_config(config_dir: Path | None = None) -> Config:
    """
    Read config.toml from `config_dir` (default: $ZOTERO_SORT_CONFIG_DIR or
    ~/.config/zotero-sort).
    """
    config_dir = config_dir or resolve_config_dir()
    config_file = config_dir / CONFIG_FILE_NAME
    settings: dict = {}
    if config_file.exists():
        try:
            settings = tomllib.loads(config_file.read_text())
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"{config_file}: {error}") from None

    return config_from_settings(settings, config_dir)


def config_from_settings(settings: dict, config_dir: Path) -> Config:
    """
    Build a Config from parsed TOML, applying defaults and validating types.
    """
    known_keys = {
        "api_key_file",
        "library",
        "inbox",
        "examples_per_collection",
        "notes_file",
    }
    unknown_keys = set(settings) - known_keys

    if unknown_keys:
        raise ConfigError(
            f"config: unknown key(s) {sorted(unknown_keys)}; valid keys are {sorted(known_keys)}"
        )

    examples_per_collection = settings.get("examples_per_collection", 8)
    if (
        not isinstance(examples_per_collection, int)
        or examples_per_collection < 0
    ):
        raise ConfigError(
            "config: examples_per_collection must be a non-negative integer"
        )

    inbox_name = settings.get("inbox", "Inbox")
    if not isinstance(inbox_name, str) or not inbox_name or "/" in inbox_name:
        raise ConfigError(
            "config: inbox must be the name of a top-level collection"
        )

    return Config(
        config_dir=config_dir,
        api_key_file=Path(
            settings.get("api_key_file", "~/.zotero_api_key")
        ).expanduser(),
        library=LibraryRef.parse(settings.get("library", "user")),
        inbox_name=inbox_name,
        examples_per_collection=examples_per_collection,
        notes_file=Path(
            settings.get("notes_file", config_dir / "notes.md")
        ).expanduser(),
    )
