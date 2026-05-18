#!/usr/bin/env python3
"""
Run a single skill once per input file in a glob pattern.

Sister tool to `skill-chain.py`:
- skill-chain runs a SEQUENCE of skills (once or via `loop:`).
- skill-batch runs ONE skill N times with a different per-iteration input.

Both share the same per-skill subprocess execution + rate-limit pause/resume:
this script imports `run_skill_with_retry` and the harness from skill-chain.py
rather than duplicating that logic. So a long batch run survives the rolling
5h Anthropic quota window the same way a long chain run does.

Usage:
    skill-batch.py --skill <skill> --inputs <glob> --output-template <tmpl> [opts]

Required:
    --skill            Skill name to invoke (must be installed under ~/.claude/skills/<name>/).
    --inputs           Glob pattern matching input files (relative to --inputs-cwd, default cwd).
    --output-template  Per-input output path. Supports {stem}, {name}, {parent}, {ext}.
                       e.g. "reviewed/from_pdf_manual/{stem}.csv".

Common options:
    --inputs-cwd <dir>     Resolve --inputs relative to this dir (default: cwd).
    --output-cwd <dir>     Resolve --output-template relative to this dir (default: --inputs-cwd).
    --skip-if-exists       Skip iterations whose output already exists.
    --include <regex>      Only process inputs whose stem matches.
    --exclude <regex>      Skip inputs whose stem matches.
    --limit <N>            Stop after N successful runs (post-skip filter).
    --start-at <stem>      Skip inputs alphabetically before this stem.
    --dry-run              Print the planned invocations and exit 0.
    --log-dir <dir>        Where per-iteration logs land (default ./.skill-batch-runs/<UTC>_<skill>/).
    --no-log               Disable log capture entirely.
    --harness <name>       Agent harness (default: $AGENT_HARNESS, else 'claude-code').
    --on-failure <mode>    fail | continue (default: fail). Continue keeps going past errors.

Rate-limit options (forwarded to skill-chain's retry loop):
    --on-rate-limit <mode>           fail | pause | pause-with-cap (default: pause).
    --max-rate-limit-pause-seconds   Cap on a single pause-with-cap pause (default: 28800).
    --max-pauses-per-session         Abort after N pauses on the same input (default: 3).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Reuse the chain runner's harness, retry loop, and helpers — no duplicated
# subprocess/stream-parsing/rate-limit code. skill-chain.py owns those.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module
_chain = import_module("skill-chain")  # type: ignore[no-redef]

DEFAULT_ON_RATE_LIMIT = _chain.DEFAULT_ON_RATE_LIMIT
DEFAULT_MAX_RATE_LIMIT_PAUSE_SECONDS = _chain.DEFAULT_MAX_RATE_LIMIT_PAUSE_SECONDS
DEFAULT_MAX_PAUSES_PER_SESSION = _chain.DEFAULT_MAX_PAUSES_PER_SESSION


def render_output_template(template: str, input_path: Path, base: Path) -> Path:
    rel = input_path
    if input_path.is_absolute():
        try:
            rel = input_path.relative_to(base)
        except ValueError:
            rel = input_path
    out = template.format(
        stem=input_path.stem,
        name=input_path.name,
        parent=str(rel.parent),
        ext=input_path.suffix.lstrip("."),
    )
    p = Path(out)
    return p if p.is_absolute() else (base / p)


def expand_inputs(glob: str, base: Path,
                  include: str | None, exclude: str | None,
                  start_at: str | None) -> list[Path]:
    matches = sorted(base.glob(glob))
    inc = re.compile(include) if include else None
    exc = re.compile(exclude) if exclude else None
    out: list[Path] = []
    for p in matches:
        if not p.is_file():
            continue
        if start_at and p.stem < start_at:
            continue
        if inc and not inc.search(p.stem):
            continue
        if exc and exc.search(p.stem):
            continue
        out.append(p)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="skill-batch.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--skill", required=True)
    ap.add_argument("--inputs", required=True, help="Glob pattern relative to --inputs-cwd.")
    ap.add_argument("--output-template", required=True)
    ap.add_argument("--inputs-cwd", type=Path, default=None)
    ap.add_argument("--output-cwd", type=Path, default=None)
    ap.add_argument("--skip-if-exists", action="store_true")
    ap.add_argument("--include", default=None)
    ap.add_argument("--exclude", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--start-at", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--log-dir", type=Path, default=None)
    ap.add_argument("--no-log", action="store_true")
    ap.add_argument("--harness", default=None)
    ap.add_argument("--on-failure", choices=["fail", "continue"], default="fail")
    ap.add_argument("--on-rate-limit", choices=["fail", "pause", "pause-with-cap"],
                    default=None)
    ap.add_argument("--max-rate-limit-pause-seconds", type=int, default=None)
    ap.add_argument("--max-pauses-per-session", type=int, default=None)
    args = ap.parse_args(argv)

    cwd = os.getcwd()
    in_base = (args.inputs_cwd or Path(cwd)).resolve()
    out_base = (args.output_cwd or args.inputs_cwd or Path(cwd)).resolve()
    inputs = expand_inputs(args.inputs, in_base, args.include, args.exclude, args.start_at)
    if not inputs:
        print(f"[skill-batch] no inputs matched {args.inputs!r} under {in_base}",
              file=sys.stderr)
        return 2

    on_rate_limit = args.on_rate_limit or DEFAULT_ON_RATE_LIMIT
    max_pause_seconds = args.max_rate_limit_pause_seconds or DEFAULT_MAX_RATE_LIMIT_PAUSE_SECONDS
    max_pauses = args.max_pauses_per_session or DEFAULT_MAX_PAUSES_PER_SESSION

    if args.no_log:
        log_dir: Path | None = None
    elif args.log_dir is not None:
        log_dir = args.log_dir
    else:
        log_dir = Path(cwd) / ".skill-batch-runs" / f"{_chain._utc_dirname()}_{args.skill}"

    harness = _chain.get_harness(args.harness)
    eff_model, eff_effort, _route = _chain._resolve_skill_route(args.skill, "medium", cwd)

    print(f"[skill-batch] skill={args.skill} matched={len(inputs)} "
          f"on_rate_limit={on_rate_limit} log_dir={log_dir}")

    manifest: dict = {
        "mode": "batch",
        "skill": args.skill,
        "started_at": _chain._utc_iso(),
        "matched_inputs": len(inputs),
        "items": [],
        "rate_limit_pauses": [],
    }

    completed = skipped = failed = 0
    overall_rc = 0
    for i, inp in enumerate(inputs, 1):
        out_path = render_output_template(args.output_template, inp, out_base)
        if args.skip_if_exists and out_path.exists():
            print(f"[{i}/{len(inputs)}] [skip] {inp.stem} (output exists)")
            skipped += 1
            manifest["items"].append({
                "index": i, "input": str(inp), "output": str(out_path),
                "status": "skipped", "reason": "output_exists",
            })
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        extra_prompt = (
            f"Apply the skill to this single input/output pair, then exit:\n"
            f"  input:  {inp}\n"
            f"  output: {out_path}"
        )
        print(f"[{i}/{len(inputs)}] [run ] {inp.stem} -> {out_path}")

        if args.dry_run:
            cmd = harness.build_command(args.skill, model=eff_model, effort=eff_effort,
                                         extra_prompt=extra_prompt)
            print("  DRY-RUN:", " ".join(repr(c) for c in cmd))
            completed += 1
            manifest["items"].append({
                "index": i, "input": str(inp), "output": str(out_path),
                "status": "dry_run",
            })
            continue

        rc, record = _chain.run_skill_with_retry(
            harness, args.skill, i, log_dir,
            on_rate_limit=on_rate_limit,
            max_pause_seconds=max_pause_seconds,
            max_pauses=max_pauses,
            pause_records=manifest["rate_limit_pauses"],
            model=eff_model, effort=eff_effort,
            extra_prompt=extra_prompt,
            log_stem_override=f"{i:03d}_{inp.stem}",
        )
        record["input"] = str(inp)
        record["output"] = str(out_path)
        record["status"] = "ok" if rc == 0 else "fail"
        manifest["items"].append(record)

        if rc == 0:
            completed += 1
        else:
            failed += 1
            print(f"[{i}/{len(inputs)}] [fail] {inp.stem} (rc={rc})", file=sys.stderr)
            if args.on_failure == "fail":
                overall_rc = rc
                break
            overall_rc = rc

        if args.limit and completed >= args.limit:
            print(f"[skill-batch] hit --limit {args.limit}, stopping")
            break

    manifest["finished_at"] = _chain._utc_iso()
    manifest["completed"] = completed
    manifest["skipped"] = skipped
    manifest["failed"] = failed
    print(f"[skill-batch] done. completed={completed} skipped={skipped} failed={failed}")

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    return overall_rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
