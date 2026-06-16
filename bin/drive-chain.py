#!/usr/bin/env python3
"""
drive-chain.py — DEPRECATED shim (Phase 42.5).

All functionality has moved to bin/skill-chain.py (Phase 42.2). Every flag
that drive-chain.py accepted is now a native flag on skill-chain.py, so no
`-- <forwarded-args>` separator is needed any more.

Migration:
  drive-chain.py --chain C --loop N --max-budget-usd X [opts] [-- <extra>]
  ->
  skill-chain.py --chain C --loop N --max-budget-usd X [opts] [<extra>]

This shim strips the `--` separator (if present) and forwards everything else
directly to skill-chain.py, then exits with the same return code. It emits
a one-line deprecation notice to stderr on every invocation.
"""

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SKILL_CHAIN = _REPO_ROOT / "bin" / "skill-chain.py"


def _strip_separator(argv: list[str]) -> list[str]:
    """Remove a bare `--` from the arg list (the old forwarded-args separator)."""
    try:
        idx = argv.index("--")
        return argv[:idx] + argv[idx + 1:]
    except ValueError:
        return argv


if __name__ == "__main__":
    print(
        "[drive-chain] DEPRECATED: drive-chain.py is a shim. "
        "Use: skill-chain.py --chain CHAIN [opts] (all flags are now native).",
        file=sys.stderr,
    )
    mapped = _strip_separator(sys.argv[1:])
    result = subprocess.run([sys.executable, str(_SKILL_CHAIN)] + mapped)
    sys.exit(result.returncode)
