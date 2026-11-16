"""
Command-line entry point:
    `python -m zotero_sort <command>` (or the `scripts/zotero-sort` wrapper).

Exit codes: 0 success, 1 error or `check` warnings, 2 invalid usage (from
argparse). Results go to stdout, errors to stderr.
"""

import argparse
import sys
from pathlib import Path

from zotero_sort import __version__
from zotero_sort.commands import (
    apply,
    check,
    context,
    init,
    list_collections,
    mkcol,
)
from zotero_sort.config import load_config
from zotero_sort.errors import ZoteroSortError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zotero-sort",
        description="File Zotero Inbox items into collections via the Web API. Never deletes anything.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
    )

    commands.add_parser(
        "collections",
        help="print the collection tree with item counts",
    )
    commands.add_parser(
        "context",
        help="JSON with the Inbox, collections (notes + examples), rules and warnings",
    )
    commands.add_parser(
        "check",
        help="compare notes.md with the live collection tree",
    )

    init_parser = commands.add_parser(
        "init",
        help="write a notes.md skeleton from the live tree",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing notes file",
    )

    mkcol_parser = commands.add_parser(
        "mkcol",
        help="create a collection (the parent must exist)",
    )
    mkcol_parser.add_argument(
        "collection_path",
        metavar="PATH",
        help='e.g. "Fuels & Mechanisms/Soot"',
    )

    apply_parser = commands.add_parser(
        "apply",
        help="file items as described in a plan file",
    )
    apply_parser.add_argument(
        "plan_file",
        metavar="PLAN.json",
        type=Path,
    )
    apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="only print what would change",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config()
        match args.command:
            case "collections":
                return list_collections.run(config)
            case "context":
                return context.run(config)
            case "check":
                return check.run(config)
            case "init":
                return init.run(config, overwrite=args.force)
            case "mkcol":
                return mkcol.run(config, args.collection_path)
            case "apply":
                return apply.run(config, args.plan_file, dry_run=args.dry_run)
    except ZoteroSortError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130

    raise AssertionError(f"unhandled command {args.command!r}")
