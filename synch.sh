SKILL_TARGET="$HOME/.claude/skills/zotero-sort"
GITHUB_DIR="$HOME/Documents/GitHub"

# the repo itself is the stow package, linked file-by-file into ~/.claude/skills/zotero-sort
mkdir -p "$SKILL_TARGET"
stow --restow --no-folding --target="$SKILL_TARGET" --dir="$GITHUB_DIR" zotero-sort
