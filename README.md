# zotero-sort

A [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills) that files new papers from
your Zotero `Inbox` collection into your own collection structure, through the Zotero Web API.

Claude proposes a placement table (paper → collections → tags), **waits for your approval**, and only
then applies it. Nothing is ever deleted.

```
Zotero desktop ── import PDFs into "Inbox", sync ──▶ zotero.org
                                                        │  Web API
/zotero-sort in Claude Code ── scripts/zotero-sort ─────┘
   1. read: Inbox items + every collection (notes + example titles)
   2. classify, show the table, wait for your OK
   3. apply: add collections + tags, remove from Inbox
Zotero desktop ◀── sync ── zotero.org
```

## How classification works

The skill is generic: it knows nothing about your field until it reads your library. It combines
two sources:

| Source | Where it lives | Maintained by | Role |
|---|---|---|---|
| **Collection tree** | your Zotero library | you, in Zotero | the names, always live |
| **Examples** | your Zotero library | nobody: they update themselves | the N most recently added titles of each collection show Claude what you *actually* file there |
| **Notes** | `~/.config/zotero-sort/notes.md` | you (Claude proposes edits) | intent the examples can't show: boundaries, tie-breakers, exceptions, tag vocabulary |

If notes and examples disagree, the notes win. Collections without notes are classified from
examples alone, so the notes can be as short as you like. They are worth writing for
ambiguous boundaries (e.g. "DA theory vs DA applications") and for collections that should only
be used on request (projects).

`check` keeps the notes honest. It compares them with the live tree and reports collections that
have no notes, notes for collections that were renamed or deleted, and empty sections. Claude
shows these warnings at the start of every run.

Your data (key, config, notes) stays **outside the repo**, so the repo has no personal data
and can be shared.

## Repository layout

```
zotero-sort/                       ← stow package (the repo root)
├── SKILL.md                       instructions Claude follows
├── scripts/zotero-sort            wrapper: picks the Python interpreter, runs `python -m zotero_sort`
├── src/zotero_sort/               the helper (standard library only, Python >= 3.11)
│   ├── cli.py                     argparse entry point, exit codes, errors to stderr
│   ├── config.py                  config.toml loading and validation
│   ├── errors.py                  exception hierarchy
│   ├── api.py                     Zotero Web API client
│   ├── tree.py                    collection tree, key <-> "Parent/Child" path
│   ├── items.py                   item summaries, duplicate detection
│   ├── notes.py                   notes.md parsing and skeleton
│   ├── drift.py                   notes vs live tree check
│   ├── plan.py                    plan validation, item update payloads
│   └── commands/                  one module per command (+ _shared.py)
├── examples/                      config.example.toml, notes.example.md
├── tests/                         ┐
├── pyproject.toml                 │
├── README.md                      │ not linked into ~/.claude (see .stow-local-ignore)
├── synch.sh                       │
└── .stow-local-ignore             ┘
```

The domain modules (`tree`, `items`, `notes`, `drift`, `plan`) are pure: no network, no printing.
Only `api.py` talks to Zotero, and only `commands/` and `cli.py` print.

Per-user files:

```
~/.zotero_api_key                     API key (library + write access)
~/.config/zotero-sort/config.toml     optional settings
~/.config/zotero-sort/notes.md        your rules, tags and per-collection notes
~/.config/zotero-sort/python          optional: interpreter command
```

## Setup

1. **Install the skill** with [stow](https://www.gnu.org/software/stow/):
   ```sh
   git clone <this repo> ~/Documents/GitHub/zotero-sort
   cd ~/Documents/GitHub/zotero-sort && ./synch.sh     # links into ~/.claude/skills/zotero-sort/
   ```
   Files are linked one by one (`--no-folding`): after adding a **new** file, run `./synch.sh` again.
   Edits to existing files take effect immediately.

2. **API key**: create one at <https://www.zotero.org/settings/keys/new> with *Allow library access*
   and *Allow write access*, and save it, alone, in `~/.zotero_api_key`. The user ID is read from the key.

3. **Python >= 3.11** (only the standard library is used). If `python3` is older, point the wrapper
   to another interpreter in either of two ways:
   ```sh
   echo "conda run -n myenv python" > ~/.config/zotero-sort/python
   # or: export ZOTERO_SORT_PYTHON="conda run -n myenv python"
   ```

4. **Inbox**: create a top-level collection called `Inbox` in Zotero (or configure another name).

5. **Notes**:
   ```sh
   ~/.claude/skills/zotero-sort/scripts/zotero-sort init     # skeleton with one section per collection
   ```
   Fill in what matters, or ask Claude to draft the sections from your existing papers and review them.
   See `examples/notes.example.md`.

## Configuration

`~/.config/zotero-sort/config.toml`. Every key is optional:

| Key | Default | Meaning |
|---|---|---|
| `api_key_file` | `~/.zotero_api_key` | file containing the API key |
| `library` | `"user"` | `"user"` or `"group:<groupID>"` for a group library |
| `inbox` | `"Inbox"` | top-level collection that receives new imports |
| `examples_per_collection` | `8` | recent titles shown to Claude per collection |
| `notes_file` | `~/.config/zotero-sort/notes.md` | location of the notes |

`ZOTERO_SORT_CONFIG_DIR` moves the whole config directory (handy for testing).

## notes.md format

```markdown
# General rules
Free text that applies to every decision (research area, how many collections per item, ...).

# Tags
The allowed tag vocabulary. Leave empty for no tags.

# Collections
## Parent/Child
What belongs here, boundaries, exceptions. One section per collection that receives items,
headed by its exact full path. Parents that only contain subcollections need no section.
```

Only these three `#` sections are read, and `<!-- comments -->` are ignored.

## Usage

1. In Zotero, import new PDFs into `Inbox` (drag and drop, or *File → Add Files from Folder…*).
   Zotero retrieves the metadata. Then sync.
2. In Claude Code: `/zotero-sort`.
3. Review the table: duplicates, PDFs without metadata and proposed new collections are listed separately.
   Approve or change it.
4. Claude runs a dry run, applies it, and reports. Sync Zotero to see the result.

## Helper commands

`scripts/zotero-sort <command>`:

| Command | What it does |
|---|---|
| `collections` | prints the collection tree with item counts |
| `context` | JSON for Claude: Inbox items (with abstract and possible duplicates), each collection with notes and examples, rules, tags, warnings |
| `check` | compares notes with the live tree; exits with 1 if there are warnings |
| `init [--force]` | writes a notes skeleton from the live tree (won't overwrite without `--force`) |
| `mkcol "Parent/Child"` | creates a collection |
| `apply PLAN.json [--dry-run]` | files items: adds collections and tags, removes them from Inbox |

Plan format: `[{"key": "ABCD1234", "collections": ["Parent/Child"], "tags": ["#review"]}]`.
`apply` validates the whole plan (shape, duplicate keys, unknown collection paths, unknown items) before
writing anything.

Exit codes: `0` success, `1` error or `check` warnings, `2` invalid usage. Results go to stdout,
errors to stderr as a single `error: ...` line. `zotero-sort --help` and `zotero-sort COMMAND --help`
describe every option.

## How the API is used

`api.py` follows the [Web API v3](https://www.zotero.org/support/dev/web_api/v3/basics) guidance:

- **Authentication:** the key is sent in the `Zotero-API-Key` header, never in the URL. `GET /keys/current`
  resolves the user ID and the key's permissions, so no user ID is configured anywhere.
- **Versioning:** every request sends `Zotero-API-Version: 3` and a `User-Agent`.
- **Pagination:** `limit=100` (the maximum) with `start`, until `Total-Results` is reached.
- **Rate limiting:** `Retry-After` on 429/503 and the `Backoff` header are honoured. Other transient errors
  (500/502/504, network) are retried with exponential backoff, up to 5 attempts, with a 30 s timeout per request.
- **Safe retries:** a GET is always safe to repeat. A POST is repeated only when the server says it didn't
  process it (429/503), or when it carries a `Zotero-Write-Token`, which makes collection creation idempotent.
  Item updates are never blindly repeated.
- **Writes:** at most 50 objects per request (the API limit). Item updates are partial and carry the item's
  `version`, so Zotero rejects a stale write with 412 instead of overwriting a concurrent change. Per-object
  failures in a 200 response are raised as errors, not ignored.

## Development

```sh
conda run -n eoshock python -m pytest     # or any Python >= 3.11 with pytest
conda run -n eoshock ruff format src tests
conda run -n eoshock ruff check src tests
```

Formatting and lint rules (120 columns, isort, pyupgrade, bugbear, simplify) are in `pyproject.toml`.
The tests cover the pure modules and the client's retry and write policy, using a scripted fake
`urlopen`, so they never touch the network or your library.

## Safety

- No delete operations exist in the code. The only removal is an item's membership in the Inbox.
- Nothing is written before you approve the table, and every apply is preceded by a dry run.
- The API key is read from a file and never printed. Revoke it at any time on zotero.org.

## Limitations

- Works on the online library: Zotero desktop must be synced before and after.
- Duplicate detection is by DOI and normalized title only. Zotero's own *Duplicate Items* is more thorough.
- Examples are only as good as your existing filing. Messy collections teach messy placements,
  which is why notes override them.
