#!/usr/bin/env bash
set -euo pipefail

SKILL_TARGET="$HOME/.claude/skills/zotero-sort"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# the repo itself is the stow package, linked file-by-file into ~/.claude/skills/zotero-sort
mkdir -p "$SKILL_TARGET"
stow --restow --no-folding --target="$SKILL_TARGET" --dir="$(dirname "$REPO_DIR")" "$(basename "$REPO_DIR")"
