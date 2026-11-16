from pathlib import Path

import pytest

from zotero_sort.config import (
    Config,
    LibraryRef,
    config_from_settings,
    load_config,
)
from zotero_sort.errors import ConfigError


def test_defaults(tmp_path):
    config = load_config(tmp_path)
    assert config.library == LibraryRef(kind="user")
    assert config.inbox_name == "Inbox"
    assert config.examples_per_collection == 8
    assert config.notes_file == tmp_path / "notes.md"
    assert config.api_key_file == Path("~/.zotero_api_key").expanduser()


def test_config_file_overrides_defaults(tmp_path):
    (tmp_path / "config.toml").write_text(
        'library = "group:12345"\ninbox = "To sort"\nexamples_per_collection = 3\n'
    )
    config = load_config(tmp_path)
    assert config.library == LibraryRef(kind="group", library_id="12345")
    assert (config.inbox_name, config.examples_per_collection) == ("To sort", 3)


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"libary": "user"}, "unknown key"),
        ({"library": "group:abc"}, "library must be"),
        ({"examples_per_collection": -1}, "non-negative"),
        ({"inbox": "Parent/Inbox"}, "top-level"),
    ],
)
def test_invalid_settings_are_rejected(settings, message):
    with pytest.raises(ConfigError, match=message):
        config_from_settings(settings, Path("/config"))


def test_invalid_toml_is_reported(tmp_path):
    (tmp_path / "config.toml").write_text("library = ")
    with pytest.raises(ConfigError, match="config.toml"):
        load_config(tmp_path)


def test_api_key_errors(tmp_path):
    config: Config = config_from_settings(
        {"api_key_file": str(tmp_path / "key")}, tmp_path
    )
    with pytest.raises(ConfigError, match="no API key"):
        config.read_api_key()
    (tmp_path / "key").write_text("\n")
    with pytest.raises(ConfigError, match="empty"):
        config.read_api_key()
    (tmp_path / "key").write_text(" secret \n")
    assert config.read_api_key() == "secret"
