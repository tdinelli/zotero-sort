"""
Exception hierarchy. The CLI turns every `ZoteroSortError` into a one-line
message and exit code 1.
"""


class ZoteroSortError(Exception):
    """Base class for all expected, user-facing errors."""


class ConfigError(ZoteroSortError):
    """Invalid or missing configuration (config.toml, API key file, notes file)."""


class PlanError(ZoteroSortError):
    """The plan file is malformed or refers to unknown items or collections."""


class ApiError(ZoteroSortError):
    """The Zotero API answered with an error status, or could not be reached."""

    def __init__(
        self,
        method: str,
        url: str,
        status: int | None,
        detail: str,
    ) -> None:
        self.method = method
        self.url = url
        self.status = status
        self.detail = detail
        status_text = (
            f"HTTP {status}" if status is not None else "network error"
        )
        super().__init__(f"{status_text} on {method} {url}: {detail}")


class WriteError(ZoteroSortError):
    """A write request succeeded as a whole but some objects in it were rejected."""

    def __init__(self, failed_objects: dict[str, dict]) -> None:
        self.failed_objects = failed_objects
        reasons = "; ".join(
            f"#{index}: {failure.get('code')} {failure.get('message', '')}".strip()
            for index, failure in failed_objects.items()
        )
        super().__init__(
            f"{len(failed_objects)} object(s) rejected by Zotero: {reasons}"
        )
