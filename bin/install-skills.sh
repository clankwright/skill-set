#!/usr/bin/env bash
# install-skills.sh — one-way deploy of transferable skills from this repo into
# the harness's user-skills directory.
#
# The master repo (./skills/) is the canonical source. The target dir is a
# deployed copy. Run this whenever you bump a transferable. Does NOT delete
# skills at the target that aren't in the source — that prevents accidentally
# wiping a project-local or hand-managed skill.
#
# Usage:
#   bin/install-skills.sh                # interactive, copies into ~/.claude/skills/
#   bin/install-skills.sh -y             # skip confirmation
#   bin/install-skills.sh --dry-run      # show what would change, copy nothing
#   bin/install-skills.sh --target DIR   # custom target (default: ~/.claude/skills)
#   bin/install-skills.sh --source DIR   # custom source (default: <repo>/skills)
#
# Exit: 0 on success, 1 on error or user cancel.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET="${HOME}/.claude/skills"
SOURCE="${REPO_ROOT}/skills"
DRY_RUN=0
ASSUME_YES=0

usage() { sed -n '2,18p' "$0"; }

while [ $# -gt 0 ]; do
    case "$1" in
        -y|--yes)      ASSUME_YES=1; shift ;;
        --dry-run)     DRY_RUN=1; shift ;;
        --target)      TARGET="$2"; shift 2 ;;
        --source)      SOURCE="$2"; shift 2 ;;
        -h|--help)     usage; exit 0 ;;
        *)             echo "unknown arg: $1" >&2; usage; exit 1 ;;
    esac
done

[ -d "$SOURCE" ] || { echo "source dir does not exist: $SOURCE" >&2; exit 1; }

# Skills are grouped into category subdirs in the source repo (e.g.
# skills/dev/dev-cycle/, skills/content/editorial-pass/) but the harness
# expects a flat layout under $TARGET/<name>/. Find every SKILL.md recursively
# and install each skill dir under its basename (category is dropped).
skill_dirs=()
while IFS= read -r -d '' sm; do
    skill_dirs+=("$(dirname "$sm")/")
done < <(find "$SOURCE" -type f -name SKILL.md -print0 | sort -z)

if [ "${#skill_dirs[@]}" -eq 0 ]; then
    echo "no skills found in $SOURCE" >&2
    exit 1
fi

# Detect name collisions across categories (same skill folder name used twice).
dup=$(printf "%s\n" "${skill_dirs[@]}" | xargs -n1 basename | sort | uniq -d)
if [ -n "$dup" ]; then
    echo "error: duplicate skill names across categories: $dup" >&2
    echo "(the harness target layout is flat; names must be unique)" >&2
    exit 1
fi

echo "Source: $SOURCE"
echo "Target: $TARGET"
echo
echo "Skills to deploy:"
for dir in "${skill_dirs[@]}"; do
    name="$(basename "$dir")"
    sm="$dir/SKILL.md"
    if [ ! -f "$sm" ]; then
        printf "  %-40s  (skipped: no SKILL.md)\n" "$name"
        continue
    fi
    if [ -f "$TARGET/$name/SKILL.md" ]; then
        if cmp -s "$sm" "$TARGET/$name/SKILL.md"; then
            printf "  %-40s  (unchanged)\n" "$name"
        else
            printf "  %-40s  (UPDATE)\n" "$name"
        fi
    else
        printf "  %-40s  (NEW)\n" "$name"
    fi
done
echo

if [ "$DRY_RUN" -eq 1 ]; then
    echo "(--dry-run; no changes made)"
    exit 0
fi

if [ "$ASSUME_YES" -ne 1 ]; then
    printf "Proceed with copy? [y/N] "
    read -r reply
    case "$reply" in
        y|Y|yes|YES) ;;
        *) echo "aborted."; exit 1 ;;
    esac
fi

mkdir -p "$TARGET"

for dir in "${skill_dirs[@]}"; do
    name="$(basename "$dir")"
    [ -f "$dir/SKILL.md" ] || continue
    mkdir -p "$TARGET/$name"
    # Copy the whole skill dir (SKILL.md + any optional assets/, scripts/, references/).
    # -a preserves perms+timestamps; we don't pass --delete so target-only files survive.
    cp -a "$dir/." "$TARGET/$name/"
done

echo "Done."
