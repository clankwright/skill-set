#!/usr/bin/env python3
"""
skill-batch.py — DEPRECATED shim (Phase 42.4).

All functionality has moved to bin/skill-chain.py --batch mode.

Migration:
  skill-batch.py --skill SKILL --inputs GLOB --output-template TMPL [opts]
  ->
  skill-chain.py SKILL --batch GLOB --output-template TMPL [opts]

Flag mapping (all native on skill-chain.py now):
  --skill SKILL             -> first positional argument
  --inputs GLOB             -> --batch GLOB
  All other flags keep the same name.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SKILL_CHAIN = _REPO_ROOT / "bin" / "skill-chain.py"


def _map_args(argv: list[str]) -> list[str]:
    """Translate skill-batch.py flags to skill-chain.py --batch equivalents."""
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--skill", default=None)
    p.add_argument("--inputs", default=None)
    p.add_argument("--output-template", default=None)
    p.add_argument("--inputs-cwd", default=None)
    p.add_argument("--output-cwd", default=None)
    p.add_argument("--skip-if-exists", action="store_true")
    p.add_argument("--include", default=None)
    p.add_argument("--exclude", default=None)
    p.add_argument("--limit", default=None)
    p.add_argument("--start-at", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--log-dir", default=None)
    p.add_argument("--no-log", action="store_true")
    p.add_argument("--harness", default=None)
    p.add_argument("--on-failure", default=None)
    p.add_argument("--on-rate-limit", default=None)
    p.add_argument("--max-rate-limit-pause-seconds", default=None)
    p.add_argument("--max-pauses-per-session", default=None)
    args, extra = p.parse_known_args(argv)

    out: list[str] = []
    if args.skill:
        out.append(args.skill)          # positional skill name
    if args.inputs:
        out += ["--batch", args.inputs]  # --inputs -> --batch
    if args.output_template:
        out += ["--output-template", args.output_template]
    if args.inputs_cwd:
        out += ["--inputs-cwd", args.inputs_cwd]
    if args.output_cwd:
        out += ["--output-cwd", args.output_cwd]
    if args.skip_if_exists:
        out.append("--skip-if-exists")
    if args.include:
        out += ["--include", args.include]
    if args.exclude:
        out += ["--exclude", args.exclude]
    if args.limit:
        out += ["--limit", args.limit]
    if args.start_at:
        out += ["--start-at", args.start_at]
    if args.dry_run:
        out.append("--dry-run")
    if args.log_dir:
        out += ["--log-dir", args.log_dir]
    if args.no_log:
        out.append("--no-log")
    if args.harness:
        out += ["--harness", args.harness]
    if args.on_failure:
        out += ["--on-failure", args.on_failure]
    if args.on_rate_limit:
        out += ["--on-rate-limit", args.on_rate_limit]
    if args.max_rate_limit_pause_seconds:
        out += ["--max-rate-limit-pause-seconds", args.max_rate_limit_pause_seconds]
    if args.max_pauses_per_session:
        out += ["--max-pauses-per-session", args.max_pauses_per_session]
    out += extra
    return out


if __name__ == "__main__":
    print(
        "[skill-batch] DEPRECATED: skill-batch.py is a shim. "
        "Use: skill-chain.py SKILL --batch GLOB --output-template TMPL",
        file=sys.stderr,
    )
    mapped = _map_args(sys.argv[1:])
    result = subprocess.run([sys.executable, str(_SKILL_CHAIN)] + mapped)
    sys.exit(result.returncode)
