---
name: zotero-sort
description: Sort new papers from the Zotero "Inbox" collection into the user's existing collections and tags via the Zotero Web API, always after the user approves a proposed placement table. Use when the user says /zotero-sort, asks to sort/file/organize their Zotero inbox or newly imported papers, asks to add or rename a Zotero collection in their structure, or asks to set up zotero-sort.
---

# zotero-sort

Files items from the user's Zotero `Inbox` collection into their collections and adds tags.

**Hard rules**
- Never apply anything before the user explicitly approves the table in step 3.
- Never delete items or collections. The helper has no delete operation; don't try another way.
- Never ask the user to paste their API key into the chat.

**Helper**: `~/.claude/skills/zotero-sort/scripts/zotero-sort <command>` (call it `zs` below).
It picks the right Python (>= 3.11) by itself. Commands: `collections`, `context`, `check`,
`init`, `mkcol`, `apply` (`zs --help`, `zs COMMAND --help`). Errors are one `error: ...` line on stderr, exit code 1.

## How classification works (hybrid)

Two sources, both delivered by `zs context`:

1. **Examples**: for every collection, the titles of its most recently added items. They come
   from the live library, so they are always current. They show what the user *actually* files there.
2. **Notes**: the user's `notes.md` (path in `notesFile`): general rules, the allowed tags and
   short notes per collection about boundaries and exceptions.

When they disagree, **the notes win** (they state intent; examples may contain old misfilings).
A collection with no notes is classified from its examples alone. A collection with no examples
and no notes: only use it if the name is unambiguous, and say so in the table.

## Procedure

1. **Read the state**: `zs context > <scratchpad>/context.json`, then read it.
   - `inbox.count == 0` → tell the user to import into the Inbox collection in Zotero and sync, then stop.
   - Non-empty `warnings` (notes out of date) → mention them briefly at the top of your reply
     and offer to fix the notes after sorting (step 6). Don't block on them.

2. **Classify each Inbox item** from its title, abstract and venue:
   - 1-3 collections, the most specific leaf (`hasSubcollections: false`) that fits;
   - follow `generalRules`; tags only from `tags`, and only when clearly true.

3. **Propose and stop.** Show one table:

   | # | First author, year | Title (short) | → Collections | Tags |

   Then, only if any:
   - **Possible duplicates** (`possibleDuplicates`): show the existing item and its collections;
     suggest merging in Zotero desktop (*Duplicate Items* → *Merge*); leave it in the Inbox unless told otherwise.
   - **No metadata** (`standaloneAttachment`): ask the user to run *Retrieve Metadata* or
     *Create Parent Item* in Zotero, sync, and re-run; leave it in the Inbox.
   - **New collection proposals**: full path, why, which items would go there.
   - **Low-confidence placements**: say which and why in one line.

   Ask for approval or changes, then wait.

4. **Apply** (only after approval, including the user's edits):
   - create approved new collections: `zs mkcol "Parent/Child"`;
   - write `<scratchpad>/plan.json`: `[{"key": "...", "collections": ["Exact/Path"], "tags": ["#review"]}]`;
   - `zs apply <plan> --dry-run`, check it matches the approved table, then `zs apply <plan>`.
     This adds the collections and tags and removes the item from the Inbox.

5. **Report**: items filed, items left in the Inbox and why, and remind the user to sync Zotero desktop.

6. **Keep the notes current.** The notes file belongs to the user and lives outside the repo.
   Edit it only with their OK, and keep its format (see below):
   - new collection created → add a `## <path>` section with one or two lines of criteria;
   - the user corrected a placement in a way that reveals a rule → propose adding that rule;
   - `check` warnings (renamed/deleted collection) → propose renaming or removing the section.
   Afterwards run `zs check`; it should print `ok`.

## notes.md format

```markdown
# General rules
free text, applies to every decision

# Tags
the allowed tag vocabulary

# Collections
## Parent/Child          ← exact full path of a collection, one section per leaf collection
free text: what goes here, boundaries, exceptions
```

Only these three `#` sections are read; `<!-- comments -->` are ignored. Parents with
subcollections need no section.

## First-time setup (when `zs` reports a missing key or notes file)

1. API key: the user creates one at https://www.zotero.org/settings/keys/new with *Allow library
   access* + *Allow write access* and saves it, alone, in `~/.zotero_api_key` (e.g. `nano ~/.zotero_api_key`).
2. Python >= 3.11: if `python3` is older, the user writes the interpreter command
   (e.g. `conda run -n myenv python`) into `~/.config/zotero-sort/python`.
3. A top-level collection named `Inbox` (or set `inbox` in `~/.config/zotero-sort/config.toml`).
4. `zs init` writes a notes skeleton from the live tree. Offer to draft each section from the
   collection's examples (`zs context`) and let the user review the file before relying on it.

## Troubleshooting

- `HTTP 403`: key revoked or without write access (`check` warns about the latter).
- `HTTP 412` / write failed with 412: an item changed in between (e.g. a sync). Re-run the dry run, then apply.
- An item isn't in the Inbox online: Zotero desktop hasn't synced yet.
- `ERROR conda.cli.main_run ... failed` printed together with `check` warnings: that's just conda
  reporting the non-zero exit code of `check`, not a separate error.
