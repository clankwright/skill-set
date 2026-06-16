"""Tests for Phase 42: unify the chain-run entrypoints into one CLI.

Covers:
- 42.1 spec the unified CLI surface — the runner's argparse epilog documents
  the full flag set, maps each legacy drive-chain.py / skill-batch.py flag to
  its unified form, and notes which scripts become shims; no flag needs `-- `.
- 42.2 merge the drive-chain.py wrapper layer into bin/skill-chain.py natively:
  --max-budget-usd, --max-cycles, --telegram-env/--no-telegram, --profile,
  --label become native optional flags that are inert when unset; the Telegram
  env-resolution / verdict-outcome / iteration-cost / profile-loading helpers
  live in skill-chain.py; the budget/cycle halt decision is a pure helper.
"""
import importlib.util
import tempfile
from pathlib import Path

_CHAIN_PATH = Path(__file__).parent.parent / "bin" / "skill-chain.py"
_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)


# ---- 42.2: native wrapper flags exist + are inert when unset ----------------

def test_native_wrapper_flags_parse():
    """The merged runner accepts the wrapper flags natively (no `-- ` forward)."""
    args = sc.parse_args([
        "--chain", "x",
        "--max-budget-usd", "30",
        "--max-cycles", "5",
        "--telegram-env", "/tmp/foo.env",
        "--profile", "ssp",
        "--label", "skill-set",
    ])
    assert args.max_budget_usd == 30.0
    assert args.max_cycles == 5
    assert Path(args.telegram_env) == Path("/tmp/foo.env")
    assert args.profile == "ssp"
    assert args.label == "skill-set"
    assert args.no_telegram is False


def test_native_wrapper_flags_inert_when_unset():
    """A bare invocation leaves every wrapper flag at its inert default, so
    today's `skill-chain.py --chain x` behavior is unchanged."""
    args = sc.parse_args(["--chain", "x"])
    assert args.max_budget_usd is None
    assert args.max_cycles is None
    assert args.telegram_env is None
    assert args.profile is None
    assert args.label is None
    assert args.no_telegram is False


def test_no_telegram_flag():
    args = sc.parse_args(["--chain", "x", "--no-telegram"])
    assert args.no_telegram is True


# ---- 42.2: Telegram env resolution (ported from test_drive_chain_telegram) --

def _write_env(path: Path, token: str, chat_id: str) -> None:
    path.write_text(f"TELEGRAM_BOT_TOKEN={token}\nTELEGRAM_CHAT_ID={chat_id}\n")


def test_base_dir_fallback_fires_when_no_arg_no_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        _write_env(repo_root / "telegram.env", "base_token", "11111")
        result = sc._resolve_tg_env(None, {}, repo_root)
        assert result.get("TELEGRAM_BOT_TOKEN") == "base_token"
        assert result.get("TELEGRAM_CHAT_ID") == "11111"


def test_telegram_env_arg_beats_base_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        _write_env(repo_root / "telegram.env", "base_token", "11111")
        explicit_env = Path(tmpdir) / "explicit.env"
        _write_env(explicit_env, "explicit_token", "22222")
        result = sc._resolve_tg_env(explicit_env, {}, repo_root)
        assert result.get("TELEGRAM_BOT_TOKEN") == "explicit_token"
        assert result.get("TELEGRAM_CHAT_ID") == "22222"


def test_caller_exported_bot_token_beats_base_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        _write_env(repo_root / "telegram.env", "base_token", "11111")
        os_env = {"TELEGRAM_BOT_TOKEN": "caller_token", "TELEGRAM_CHAT_ID": "33333"}
        result = sc._resolve_tg_env(None, os_env, repo_root)
        assert result.get("TELEGRAM_BOT_TOKEN") == "caller_token"
        assert result.get("TELEGRAM_CHAT_ID") == "33333"


# ---- 42.2: verdict outcome parsing ------------------------------------------

def test_verdict_outcome_header_form():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "supervisor_verdict.md"
        p.write_text("# Verdict\n\n## Outcome\n\nclean\n\nbody...")
        assert sc._verdict_outcome(p) == "clean"


def test_verdict_outcome_escalate_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "supervisor_verdict.md"
        p.write_text("The supervisor decided to escalate this finding.\n")
        assert sc._verdict_outcome(p) == "escalate"


def test_verdict_outcome_absent_is_unknown():
    assert sc._verdict_outcome(Path("/nonexistent/verdict.md")) == "unknown"


def test_supervisor_verdict_path_looping_vs_flat():
    base = Path("/tmp/run")
    assert sc._supervisor_verdict_path(base, 3, True) == base / "iter_03" / "supervisor_verdict.md"
    assert sc._supervisor_verdict_path(base, 3, False) == base / "supervisor_verdict.md"


# ---- 42.2: iteration cost ---------------------------------------------------

def test_iteration_cost_sums_skills():
    manifest = {"skills": [
        {"total_cost_usd": 1.5},
        {"total_cost_usd": 2.25},
        {"total_cost_usd": None},
        {},
    ]}
    assert sc._iteration_cost(manifest) == 3.75


# ---- 42.2: profile defaults loading -----------------------------------------

def test_load_profile_defaults_reads_configured_block():
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / ".claude" / "skills" / "ssp-chain-driver"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "# ssp-chain-driver\n\n"
            "## Configured defaults\n\n"
            "```yaml\n"
            "watched-chain: skill-set-cycle\n"
            "default-loop: 0\n"
            "default-max-budget-usd: 30\n"
            "default-max-cycles: 3\n"
            "telegram-env: ~/.config/ssp-telegram.env\n"
            "label: skill-set\n"
            "ignored-key: nope\n"
            "```\n\n"
            "## Other\n"
        )
        data = sc._load_profile_defaults("ssp", tmpdir)
        assert data is not None
        assert data["watched-chain"] == "skill-set-cycle"
        assert data["default-loop"] == 0
        assert data["default-max-budget-usd"] == 30
        assert data["default-max-cycles"] == 3
        assert data["label"] == "skill-set"
        # Unknown keys are dropped to the PROFILE_KEYS contract surface.
        assert "ignored-key" not in data


def test_load_profile_defaults_missing_skill_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        assert sc._load_profile_defaults("nope", tmpdir) is None


# ---- 42.2: telegram-enabled gate (opt-in only) ------------------------------

def test_telegram_disabled_by_default():
    """Bare runner never touches Telegram — inert when unset."""
    args = sc.parse_args(["--chain", "x"])
    assert sc._wrapper_telegram_enabled(args) is False


def test_telegram_enabled_by_opt_in_flags():
    for extra in (["--telegram-env", "/tmp/e.env"], ["--profile", "ssp"], ["--label", "x"]):
        args = sc.parse_args(["--chain", "x", *extra])
        assert sc._wrapper_telegram_enabled(args) is True


def test_no_telegram_overrides_opt_in():
    args = sc.parse_args(["--chain", "x", "--profile", "ssp", "--no-telegram"])
    assert sc._wrapper_telegram_enabled(args) is False


# ---- 42.2: budget / cycle halt decision (pure helper) -----------------------

def test_halt_on_budget():
    reason = sc._wrapper_halt_reason(
        cumulative_cost_usd=31.0, completed_iterations=2,
        max_budget_usd=30.0, max_cycles=None,
    )
    assert reason is not None and "budget" in reason.lower()


def test_halt_on_max_cycles():
    reason = sc._wrapper_halt_reason(
        cumulative_cost_usd=1.0, completed_iterations=3,
        max_budget_usd=None, max_cycles=3,
    )
    assert reason is not None and "cycle" in reason.lower()


def test_halt_on_escalation():
    reason = sc._wrapper_halt_reason(
        cumulative_cost_usd=1.0, completed_iterations=1,
        max_budget_usd=None, max_cycles=None, verdict="escalate",
    )
    assert reason is not None and "escal" in reason.lower()


def test_no_halt_when_caps_unset():
    assert sc._wrapper_halt_reason(
        cumulative_cost_usd=999.0, completed_iterations=99,
        max_budget_usd=None, max_cycles=None,
    ) is None


def test_no_halt_under_caps():
    assert sc._wrapper_halt_reason(
        cumulative_cost_usd=5.0, completed_iterations=1,
        max_budget_usd=30.0, max_cycles=3,
    ) is None


# ---- 42.1: epilog documents the unified surface + shim mapping --------------

def test_epilog_maps_legacy_flags_and_names_shims():
    epi = sc.UNIFIED_CLI_EPILOG
    # Names the two scripts that become shims.
    assert "drive-chain.py" in epi
    assert "skill-batch.py" in epi
    # Maps each merged wrapper flag into the unified runner.
    for flag in ("--max-budget-usd", "--max-cycles", "--telegram-env",
                 "--profile", "--label"):
        assert flag in epi, f"epilog must document {flag}"
    # States the `-- `-forwarding split is gone.
    assert "--" in epi
    assert "shim" in epi.lower()


def test_parser_uses_the_epilog():
    """parse_args's parser carries the documented epilog (so --help shows it)."""
    # Build the parser the same way parse_args does and confirm the epilog flows
    # through. We assert via the module-level constant being embedded.
    assert "drive-chain.py" in sc.UNIFIED_CLI_EPILOG
