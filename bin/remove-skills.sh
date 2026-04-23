#!/usr/bin/env bash
# remove-skills.sh — inverse of install-skills.sh. Removes transferable skills
# from the harness's user-skills directory.
#
# Only removes skill names that this repo's ./skills/ also defines — so a
# project-local or hand-written skill under $TARGET with a name this repo
# doesn't ship will never be touched. That's the same safety rail install-
# skills.sh uses in the other direction.
#
# Usage:
#   bin/remove-skills.sh                          # all (from source list), interactive
#   bin/remove-skills.sh <name> [<name> ...]      # only the named skills
#   bin/remove-skills.sh -y                       # skip confirmation
#   bin/remove-skills.sh --dry-run                # show what would be removed, delete nothing
#   bin/remove-skills.sh --target DIR             # custom target (default: ~/.claude/skills)
#   bin/remove-skills.sh --source DIR             # custom source (default: <repo>/skills)
#
# Examples:
#   bin/remove-skills.sh sanitize-transferable    # one skill
#   bin/remove-skills.sh -y supervisor manager    # two, no prompt
#   bin/remove-skills.sh --dry-run                # preview full uninstall
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
[ -d "$TARGET" ] || { echo "target dir does not exist: $TARGET (nothing to remove)"; exit 0; }

# Find every skill this repo defines (any nesting depth under $SOURCE).
skill_dirs=()
while IFS= read -r -d '' sm; do
    skill_dirs+=("$(dirname "$sm")/")
done < <(find "$SOURCE" -type f -name SKILL.md -print0 | sort -z)

if [ "${#skill_dirs[@]}" -eq 0 ]; then
    echo "no skills found in $SOURCE" >&2
    exit 1
fi

dup=$(printf "%s\n" "${skill_dirs[@]}" | xargs -n1 basename | sort | uniq -d)
if [ -n "$dup" ]; then
    echo "error: duplicate skill names across categories in source: $dup" >&2
    exit 1
fi

# Apply the name filter (if any). Every positional arg must match exactly one
# source-defined skill; unknown names are a hard error.
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

category_of() {
    local dir="$1"
    local rel="${dir#"$SOURCE"/}"
    rel="${rel%/}"
    local name
    name="$(basename "$rel")"
    local cat="${rel%/"$name"}"
    [ "$cat" = "$rel" ] && cat="(uncategorized)"
    printf "%s" "$cat"
}

status_of() {
    local name="$1"
    if [ -d "$TARGET/$name" ]; then
        printf "REMOVE"
    else
        printf "not present"
    fi
}

echo "Source (definition): $SOURCE"
echo "Target (deploy):     $TARGET"
if [ "${#FILTERS[@]}" -gt 0 ]; then
    echo "Filter:              ${FILTERS[*]}"
fi
echo
echo "Skills to remove from target:"

tmp_rows=$(mktemp)
trap 'rm -f "$tmp_rows"' EXIT
will_remove=0
for dir in "${skill_dirs[@]}"; do
    name="$(basename "$dir")"
    cat="$(category_of "$dir")"
    st="$(status_of "$name")"
    [ "$st" = "REMOVE" ] && will_remove=$((will_remove + 1))
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

if [ "$will_remove" -eq 0 ]; then
    echo "nothing to remove."
    exit 0
fi

echo "$will_remove skill(s) will be removed. Other entries under $TARGET are untouched."
echo

if [ "$DRY_RUN" -eq 1 ]; then
    echo "(--dry-run; no changes made)"
    exit 0
fi

if [ "$ASSUME_YES" -ne 1 ]; then
    printf "Proceed with removal? [y/N] "
    read -r reply
    case "$reply" in
        y|Y|yes|YES) ;;
        *) echo "aborted."; exit 1 ;;
    esac
fi

for dir in "${skill_dirs[@]}"; do
    name="$(basename "$dir")"
    target_path="$TARGET/$name"
    # Safety rails: never rm outside $TARGET, never rm the target root itself.
    case "$target_path" in
        "$TARGET"/*) ;;
        *) echo "refusing to remove path outside target: $target_path" >&2; exit 1 ;;
    esac
    [ -d "$target_path" ] || continue
    rm -rf -- "$target_path"
done

echo "Done."
