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
#   bin/install-skills.sh                          # all skills, interactive
#   bin/install-skills.sh <name> [<name> ...]      # only the named skills
#   bin/install-skills.sh -y                       # skip confirmation
#   bin/install-skills.sh --dry-run                # show what would change, copy nothing
#   bin/install-skills.sh --target DIR             # custom target (default: ~/.claude/skills)
#   bin/install-skills.sh --source DIR             # custom source (default: <repo>/skills)
#
# Examples:
#   bin/install-skills.sh sanitize-transferable    # one skill
#   bin/install-skills.sh -y supervisor manager    # two, no prompt
#   bin/install-skills.sh --dry-run dev-cycle      # preview one
#
# Output groups skills by their source-repo category (e.g. framework/, dev/,
# framework/coms/). Categories are a source-side organization; the harness
# target layout stays flat ($TARGET/<name>/).
#
# Exit: 0 on success, 1 on error or user cancel.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET="${HOME}/.claude/skills"
SOURCE="${REPO_ROOT}/skills"
DRY_RUN=0
ASSUME_YES=0
FILTERS=()

usage() { sed -n '2,25p' "$0"; }

while [ $# -gt 0 ]; do
    case "$1" in
        -y|--yes)      ASSUME_YES=1; shift ;;
        --dry-run)     DRY_RUN=1; shift ;;
        --target)      TARGET="$2"; shift 2 ;;
        --source)      SOURCE="$2"; shift 2 ;;
        -h|--help)     usage; exit 0 ;;
        --)            shift; while [ $# -gt 0 ]; do FILTERS+=("$1"); shift; done ;;
        -*)            echo "unknown flag: $1" >&2; usage; exit 1 ;;
        *)             FILTERS+=("$1"); shift ;;
    esac
done

[ -d "$SOURCE" ] || { echo "source dir does not exist: $SOURCE" >&2; exit 1; }

# Skills are grouped into category subdirs in the source repo (e.g.
# skills/dev/dev-cycle/, skills/framework/coms/setup-telegram/) but the harness
# expects a flat layout under $TARGET/<name>/. Find every SKILL.md recursively
# and install each skill dir under its basename (category is dropped on copy).
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

# Apply the name filter (if any). Every positional arg must match exactly one
# skill; unknown names are a hard error so a typo doesn't silently no-op.
if [ "${#FILTERS[@]}" -gt 0 ]; then
    filtered=()
    unmatched=()
    for want in "${FILTERS[@]}"; do
        hit=""
        for dir in "${skill_dirs[@]}"; do
            if [ "$(basename "$dir")" = "$want" ]; then
                hit="$dir"
                break
            fi
        done
        if [ -n "$hit" ]; then
            filtered+=("$hit")
        else
            unmatched+=("$want")
        fi
    done
    if [ "${#unmatched[@]}" -gt 0 ]; then
        echo "error: skill(s) not found in $SOURCE: ${unmatched[*]}" >&2
        echo "available names:" >&2
        printf "  %s\n" "${skill_dirs[@]}" | xargs -n1 basename | sort | sed 's/^/  /' >&2
        exit 1
    fi
    skill_dirs=("${filtered[@]}")
fi

# Compute each skill's source-side category (path between $SOURCE and the skill
# basename), then group the display output by category. This is cosmetic only;
# the target layout stays flat.
category_of() {
    local dir="$1"
    local rel="${dir#"$SOURCE"/}"
    rel="${rel%/}"                       # strip trailing slash
    local name
    name="$(basename "$rel")"
    local cat="${rel%/"$name"}"          # everything before the final segment
    [ "$cat" = "$rel" ] && cat="(uncategorized)"
    printf "%s" "$cat"
}

status_of() {
    local dir="$1"
    local name="$2"
    local sm="$dir/SKILL.md"
    if [ ! -f "$sm" ]; then
        printf "skipped: no SKILL.md"
        return
    fi
    if [ -f "$TARGET/$name/SKILL.md" ]; then
        if cmp -s "$sm" "$TARGET/$name/SKILL.md"; then
            printf "unchanged"
        else
            printf "UPDATE"
        fi
    else
        printf "NEW"
    fi
}

echo "Source: $SOURCE"
echo "Target: $TARGET"
if [ "${#FILTERS[@]}" -gt 0 ]; then
    echo "Filter: ${FILTERS[*]}"
fi
echo
echo "Skills to deploy:"

# Stable group-by-category, skills within category sorted.
tmp_rows=$(mktemp)
trap 'rm -f "$tmp_rows"' EXIT
for dir in "${skill_dirs[@]}"; do
    name="$(basename "$dir")"
    cat="$(category_of "$dir")"
    st="$(status_of "$dir" "$name")"
    printf '%s\t%s\t%s\n' "$cat" "$name" "$st" >> "$tmp_rows"
done

current_cat=""
while IFS=$'\t' read -r cat name st; do
    if [ "$cat" != "$current_cat" ]; then
        printf "  %s/\n" "$cat"
        current_cat="$cat"
    fi
    printf "    %-40s  (%s)\n" "$name" "$st"
done < <(sort -t$'\t' -k1,1 -k2,2 "$tmp_rows")
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
