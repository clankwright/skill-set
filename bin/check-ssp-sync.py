#!/usr/bin/env python3
"""check-ssp-sync.py — report proprietary skill wrappers that have drifted
behind the base transferable they wrap.

A proprietary wrapper declares two frontmatter keys that couple it to a base
transferable:

    transferable: sst-X       # the base skill this wrapper extends
    base-version: A.B.C       # the base sst-X version last reconciled against

`base-version` is the version of the base `sst-X` whose contract the wrapper's
project-specific prose was last reviewed against. This tool compares each
wrapper's `base-version` to the base repo's CURRENT `sst-X` version and reports
any wrapper whose base has moved ahead — the wrapper's "inherits + adds + on
conflict project wins" prose may now reference superseded base behavior and
should be reviewed (and its `base-version` bumped once reconciled).

This is the semantic complement to `install-skills.sh`'s runtime-copy drift
check. Those two checks close two different gaps:

  * install-skills.sh keeps the runtime `~/.claude/skills/sst-*` COPIES equal to
    the base SOURCE (a file-content gap).
  * check-ssp-sync.py keeps each `ssp-*` WRAPPER reconciled against the base
    CONTRACT it wraps (a semantic-version gap).

A clean upgrade flow runs both: bump the base sst-X, run install-skills.sh to
refresh the runtime copy, then run check-ssp-sync.py to surface every wrapper
that now needs a reconcile pass.

Wrappers are usually project-local: the runtime `~/.claude/skills/sst-*` copies
are transferables, while each `ssp-*` wrapper lives in its project's
`.claude/skills/`. So by default this scans BOTH `~/.claude/skills` and the
current directory's `./.claude/skills`; pass `--skills-dir` (repeatable) to
scan explicit roots instead.

Usage:
  bin/check-ssp-sync.py                       # scan ~/.claude/skills + ./.claude/skills
  bin/check-ssp-sync.py --json                # machine-readable report
  bin/check-ssp-sync.py --quiet               # exit code only, no stdout
  bin/check-ssp-sync.py --base DIR            # base repo (default: this repo)
  bin/check-ssp-sync.py --skills-dir DIR      # explicit skills root (repeatable)

Exit codes:
  0  every wrapper is reconciled against the current base version
  1  at least one wrapper is stale, unpinned, ahead, or points at an unknown base
  2  configuration error (base dir or skills dir missing / unreadable)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SKILLS_DIR = Path.home() / ".claude" / "skills"

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Top-level `key: value` line (no leading whitespace, so block-scalar
# continuations and nested/prose lines are skipped).
_KEY_RE = re.compile(r"^([A-Za-z][\w-]*):\s?(.*)$")
_VERSION_RE = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)")


def extract_frontmatter(text: str) -> dict | None:
    """Extract top-level scalar keys from a SKILL.md frontmatter block.

    Deliberately line-based rather than a full YAML parse: real wrapper
    frontmatter often has a single-line `description:` containing `: `
    sequences that a strict YAML loader rejects ("mapping values are not
    allowed here"), yet the keys this tool needs (name, version, transferable,
    base-version) are always simple scalars. Matches how the other framework
    tools read these files. Returns None only when no frontmatter block exists.
    """
    m = FRONTMATTER_RE.search(text)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        km = _KEY_RE.match(line)  # ^[A-Za-z] => indented continuations skipped
        if km:
            key, val = km.group(1), km.group(2).strip()
            fm.setdefault(key, val)  # first occurrence wins
    return fm


def parse_version(value: object) -> tuple[int, int, int] | None:
    """Parse a SemVer-ish 'A.B.C' string into a comparable tuple, else None."""
    if value is None:
        return None
    m = _VERSION_RE.match(str(value))
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def build_base_version_map(base_dir: Path) -> dict[str, str]:
    """Map every base-repo skill name to its declared version."""
    versions: dict[str, str] = {}
    skills_root = base_dir / "skills"
    if not skills_root.is_dir():
        return versions
    for sm in skills_root.rglob("SKILL.md"):
        fm = extract_frontmatter(sm.read_text(encoding="utf-8"))
        if not fm:
            continue
        name = fm.get("name")
        version = fm.get("version")
        if name and version is not None:
            versions[str(name)] = str(version)
    return versions


def scan_wrappers(skills_dir: Path, base_versions: dict[str, str]) -> list[dict]:
    """Return one status record per installed proprietary wrapper.

    A wrapper is any installed SKILL.md whose frontmatter carries a
    `transferable:` key (transferables themselves lack that key).
    """
    records: list[dict] = []
    for child in sorted(skills_dir.iterdir()):
        sm = child / "SKILL.md"
        if not sm.is_file():
            continue
        fm = extract_frontmatter(sm.read_text(encoding="utf-8"))
        if not fm:
            continue
        transferable = fm.get("transferable")
        if not transferable:
            continue  # not a wrapper

        name = str(fm.get("name") or child.name)
        transferable = str(transferable)
        pinned = fm.get("base-version")
        pinned_str = None if pinned is None else str(pinned)
        base_cur = base_versions.get(transferable)

        status = _classify(pinned_str, base_cur)
        records.append(
            {
                "name": name,
                "transferable": transferable,
                "base_version": pinned_str,
                "base_current": base_cur,
                "status": status,
                "path": str(sm),
            }
        )
    return records


def _classify(pinned: str | None, base_cur: str | None) -> str:
    """One of: ok | stale | ahead | unpinned | unknown-base | unparseable."""
    if base_cur is None:
        return "unknown-base"
    if pinned is None:
        return "unpinned"
    pv, bv = parse_version(pinned), parse_version(base_cur)
    if pv is None or bv is None:
        return "unparseable"
    if bv > pv:
        return "stale"
    if pv > bv:
        return "ahead"
    return "ok"


# Statuses that mean "a human/manager should reconcile this wrapper".
_DRIFT_STATUSES = frozenset({"stale", "ahead", "unpinned", "unknown-base", "unparseable"})

_STATUS_NOTE = {
    "ok": "reconciled",
    "stale": "base moved ahead — review wrapper, then bump base-version",
    "ahead": "base-version is newer than the base repo (base behind?)",
    "unpinned": "no base-version pin — add one after a reconcile pass",
    "unknown-base": "transferable not found in the base repo",
    "unparseable": "base-version or base version is not SemVer A.B.C",
}


def format_report(records: list[dict]) -> str:
    """Human-readable report grouped drift-first."""
    if not records:
        return "check-ssp-sync: no proprietary wrappers found (nothing to check)."
    drift = [r for r in records if r["status"] in _DRIFT_STATUSES]
    ok = [r for r in records if r["status"] not in _DRIFT_STATUSES]
    lines: list[str] = []
    if drift:
        lines.append(f"DRIFT: {len(drift)} wrapper(s) need a reconcile pass")
        for r in drift:
            lines.append(
                f"  {r['name']}: {r['status']} "
                f"(wraps {r['transferable']}; pinned={r['base_version']} "
                f"base={r['base_current']}) — {_STATUS_NOTE[r['status']]}"
            )
    else:
        lines.append("OK: all wrappers reconciled against current base versions")
    if ok:
        lines.append(f"in sync ({len(ok)}): " + ", ".join(
            f"{r['name']}@{r['base_version']}" for r in ok))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report ssp-* wrappers drifted behind their base sst-* transferable.")
    parser.add_argument(
        "--base", default=str(REPO_ROOT),
        help="Base skill-set repo (default: this script's repo root).")
    parser.add_argument(
        "--skills-dir", action="append", default=None,
        help="Skills root to scan for wrappers (repeatable). "
             "Default: ~/.claude/skills and ./.claude/skills.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--quiet", action="store_true", help="No stdout; exit code only.")
    args = parser.parse_args(argv)

    base_dir = Path(args.base).expanduser()
    if not (base_dir / "skills").is_dir():
        print(f"check-ssp-sync: base skills tree not found under {base_dir}", file=sys.stderr)
        return 2

    # Resolve the skills roots. Explicit --skills-dir values must each exist
    # (a typo'd path is a config error, not "no wrappers"); the default pair is
    # filtered to whichever exist, and at least one must.
    if args.skills_dir:
        roots: list[Path] = []
        for d in args.skills_dir:
            p = Path(d).expanduser()
            if not p.is_dir():
                print(f"check-ssp-sync: skills dir not found: {p}", file=sys.stderr)
                return 2
            roots.append(p)
    else:
        candidates = [DEFAULT_SKILLS_DIR, Path.cwd() / ".claude" / "skills"]
        roots = [p for p in candidates if p.is_dir()]
        if not roots:
            print("check-ssp-sync: no skills dir found "
                  f"(looked in {', '.join(str(c) for c in candidates)})", file=sys.stderr)
            return 2

    base_versions = build_base_version_map(base_dir)
    records: list[dict] = []
    seen: set[str] = set()
    for root in roots:
        for rec in scan_wrappers(root, base_versions):
            if rec["name"] in seen:
                continue  # a wrapper installed in two roots: report once
            seen.add(rec["name"])
            records.append(rec)
    has_drift = any(r["status"] in _DRIFT_STATUSES for r in records)

    if not args.quiet:
        if args.json:
            print(json.dumps({"drift": has_drift, "wrappers": records}, indent=2))
        else:
            print(format_report(records))

    return 1 if has_drift else 0


if __name__ == "__main__":
    sys.exit(main())
