#!/usr/bin/env python3
"""clean-skill-runs.py: idempotent housekeeping for a project's run-log + skills tree.

Removes three classes of cruft that accumulate as a side effect of pre-Phase-11
chain runs and the supervisor's old `--backup` invocation pattern:

1. Empty `<run-dir>/proposals/` (and `<run-dir>/iter_NN/proposals/`) directories.
   The pre-Phase-11 contract created `proposals/` up front; Phase 11 routes drafts
   to `<run-dir>/drafts/` instead, so the empty dirs are pure leftover.

2. `*SKILL.md.bak` files anywhere under `<project>/.claude/skills/`. Leftover
   from the supervisor's prior `--backup` edit pattern (Phase 14 dropped the
   `--backup` default). Git history covers rollback; the tracked-but-
   uncommitted `.bak` files just surface as dirty status every cycle.

3. Orphaned `<run-dir>/drafts/` directories whose contents are older than N days
   (default 14). These accumulate when a supervisor exits between sanitize and
   apply (Phase 14 (a)/(b)); the iter-boundary drafts sweep should consume the
   recent ones, leaving only legitimately stale orphans for housekeeping.
   Drafts younger than the threshold are never touched.

Defaults to dry-run: prints what it WOULD remove and exits 0. Pass `--apply` to
actually delete. Pass `--yes` to auto-confirm prompts on draft directories
(empty proposals/ and `.bak` files never prompt; they have no recovery value).

Usage
-----
    bin/clean-skill-runs.py [<project-root>]                  # dry-run from <root> (default cwd)
    bin/clean-skill-runs.py --apply                           # actually delete (prompts on drafts/)
    bin/clean-skill-runs.py --apply --yes                     # auto-confirm drafts/ deletions
    bin/clean-skill-runs.py --apply --days 30                 # bump drafts/ stale threshold
    bin/clean-skill-runs.py --apply ~/Dev/sdrai               # housekeep a specific project

Exit codes
----------
    0   ran cleanly (dry-run or apply)
    1   usage / input error
    2   project root is outside the user's home (refused) or doesn't look like a
        framework consumer (no .skill-runs/ AND no .claude/skills/)
"""

import argparse
import shutil
import sys
import time
from pathlib import Path


HOME = Path.home().resolve()


def is_approved_root(root: Path) -> tuple[bool, str]:
    """The script only operates inside the user's home, on a directory that has
    at least one of the framework's housekeeping surfaces (`.skill-runs/` or
    `.claude/skills/`). Symlinks resolved before checks."""
    try:
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError) as e:
        return False, f"cannot resolve project root: {e}"
    if not resolved.is_dir():
        return False, f"project root is not a directory: {resolved}"
    try:
        resolved.relative_to(HOME)
    except ValueError:
        return False, f"project root is outside the user's home: {resolved}"
    has_runs = (resolved / ".skill-runs").is_dir()
    has_skills = (resolved / ".claude" / "skills").is_dir()
    if not has_runs and not has_skills:
        return False, (
            f"project root {resolved} has neither .skill-runs/ nor .claude/skills/; "
            f"refusing to operate (does not look like a framework consumer)"
        )
    return True, ""


def find_run_dirs(project_root: Path) -> list[Path]:
    """Return every chain-run directory under `<project_root>/.skill-runs/`,
    INCLUDING per-iteration subdirs (`iter_NN/`). Both layouts host their own
    `proposals/` and `drafts/` siblings."""
    runs_root = project_root / ".skill-runs"
    if not runs_root.is_dir():
        return []
    out: list[Path] = []
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        out.append(run_dir)
        for child in sorted(run_dir.iterdir()):
            if child.is_dir() and child.name.startswith("iter_"):
                out.append(child)
    return out


def find_empty_proposals(run_dirs: list[Path]) -> list[Path]:
    """Return every `<run>/proposals/` (or iter-level) directory that exists and is empty."""
    out: list[Path] = []
    for d in run_dirs:
        proposals = d / "proposals"
        if proposals.is_dir() and not any(proposals.iterdir()):
            out.append(proposals)
    return out


def find_bak_files(project_root: Path) -> list[Path]:
    """Return every `*SKILL.md.bak` under `<project>/.claude/skills/`. Match is
    on filename suffix; that is the exact shape the supervisor's prior
    `--backup` edit pattern used to produce."""
    skills_root = project_root / ".claude" / "skills"
    if not skills_root.is_dir():
        return []
    return sorted(skills_root.rglob("*SKILL.md.bak"))


def latest_file_mtime(path: Path) -> float:
    """Most-recent mtime among files under `path` (recursively). Returns 0.0
    if no files found. The directory's OWN mtime is intentionally ignored:
    it tracks add/remove operations on direct children, which can make a dir
    appear young even when every file inside it is months old (e.g. the file
    was created today but `touch -d <old>`'d to a past timestamp). We want to
    age the drafts/ by content, not by directory bookkeeping."""
    newest = 0.0
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        try:
            mt = child.stat().st_mtime
        except OSError:
            continue
        if mt > newest:
            newest = mt
    return newest


def find_stale_drafts(run_dirs: list[Path], threshold_days: int) -> list[tuple[Path, float, int]]:
    """Return `(drafts_dir, latest_mtime_epoch, file_count)` for every drafts/
    directory older than the threshold. Empty drafts/ dirs always qualify
    (treated as zero-age cruft) so they get reported regardless of `threshold_days`."""
    cutoff = time.time() - threshold_days * 86400
    out: list[tuple[Path, float, int]] = []
    for d in run_dirs:
        drafts = d / "drafts"
        if not drafts.is_dir():
            continue
        file_count = sum(1 for f in drafts.rglob("*") if f.is_file())
        if file_count == 0:
            out.append((drafts, drafts.stat().st_mtime, 0))
            continue
        newest = latest_file_mtime(drafts)
        if newest <= cutoff:
            out.append((drafts, newest, file_count))
    return out


def confirm(prompt: str, auto_yes: bool) -> bool:
    if auto_yes:
        return True
    try:
        ans = input(prompt).strip().lower()
    except EOFError:
        return False
    return ans == "y" or ans == "yes"


def fmt_age(epoch: float) -> str:
    age_days = (time.time() - epoch) / 86400
    return f"{age_days:.1f}d ago"


def fmt_path(p: Path) -> str:
    """Render under HOME with a `~` prefix when applicable; reduces noise."""
    try:
        rel = p.resolve().relative_to(HOME)
        return f"~/{rel}"
    except ValueError:
        return str(p)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="clean-skill-runs.py",
        description=(
            "Housekeeping for a project's .skill-runs/ + .claude/skills/ trees. "
            "Removes empty proposals/ dirs, *SKILL.md.bak cruft, and stale drafts/ "
            "directories. Defaults to dry-run; pass --apply to actually delete."
        ),
    )
    p.add_argument(
        "project_root",
        nargs="?",
        default=".",
        type=Path,
        help="Project root to housekeep (default: current directory). "
             "Must contain .skill-runs/ or .claude/skills/ and live under your home.",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform deletions. Without this flag the script runs read-only.",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Auto-confirm prompts (drafts/ removals). Empty proposals/ and *.bak "
             "files never prompt; they have no recovery value.",
    )
    p.add_argument(
        "--days",
        type=int,
        default=14,
        help="Drafts/ staleness threshold in days (default 14). "
             "Drafts younger than this are not touched.",
    )
    args = p.parse_args(argv)

    if args.days < 0:
        print(f"--days must be non-negative (got {args.days})", file=sys.stderr)
        return 1

    project_root = args.project_root.resolve()
    approved, reason = is_approved_root(project_root)
    if not approved:
        print(f"refusing: {reason}", file=sys.stderr)
        return 2

    print(f"clean-skill-runs: scanning {fmt_path(project_root)} (dry-run={'no' if args.apply else 'yes'})")

    run_dirs = find_run_dirs(project_root)
    empty_proposals = find_empty_proposals(run_dirs)
    bak_files = find_bak_files(project_root)
    stale_drafts = find_stale_drafts(run_dirs, args.days)

    total = len(empty_proposals) + len(bak_files) + len(stale_drafts)
    if total == 0:
        print("nothing to clean.")
        return 0

    print(f"\n[empty proposals/ dirs] {len(empty_proposals)}")
    for d in empty_proposals:
        print(f"  {fmt_path(d)}")

    print(f"\n[*SKILL.md.bak files] {len(bak_files)}")
    for f in bak_files:
        print(f"  {fmt_path(f)}")

    print(f"\n[stale drafts/ dirs (>={args.days}d or empty)] {len(stale_drafts)}")
    for d, newest, count in stale_drafts:
        if count == 0:
            print(f"  {fmt_path(d)}  (empty)")
        else:
            print(f"  {fmt_path(d)}  ({count} files, newest {fmt_age(newest)})")

    if not args.apply:
        print(f"\n(dry-run) re-run with --apply to delete the {total} items above.")
        return 0

    removed = 0
    skipped = 0
    failed = 0

    for d in empty_proposals:
        try:
            d.rmdir()
            print(f"removed {fmt_path(d)}")
            removed += 1
        except OSError as e:
            print(f"failed: {fmt_path(d)}: {e}", file=sys.stderr)
            failed += 1

    for f in bak_files:
        try:
            f.unlink()
            print(f"removed {fmt_path(f)}")
            removed += 1
        except OSError as e:
            print(f"failed: {fmt_path(f)}: {e}", file=sys.stderr)
            failed += 1

    for d, newest, count in stale_drafts:
        descriptor = "empty" if count == 0 else f"{count} files, newest {fmt_age(newest)}"
        if count == 0:
            try:
                d.rmdir()
                print(f"removed {fmt_path(d)} ({descriptor})")
                removed += 1
            except OSError as e:
                print(f"failed: {fmt_path(d)}: {e}", file=sys.stderr)
                failed += 1
            continue
        prompt = f"remove {fmt_path(d)} ({descriptor})? [y/N]: "
        if not confirm(prompt, args.yes):
            print(f"skipped {fmt_path(d)}")
            skipped += 1
            continue
        try:
            shutil.rmtree(d)
            print(f"removed {fmt_path(d)} ({descriptor})")
            removed += 1
        except OSError as e:
            print(f"failed: {fmt_path(d)}: {e}", file=sys.stderr)
            failed += 1

    print(f"\nsummary: {removed} removed, {skipped} skipped, {failed} failed.")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
