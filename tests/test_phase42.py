"""Tests for Phase 42: unify the chain-run entrypoints into one CLI.

Covers:
- 42.1 spec the unified CLI surface — the runner's argparse epilog documents
  the full flag set and unified invocation; no flag needs `-- `.
- 42.2 merge the wrapper layer into bin/skill-chain.py natively:
  --max-budget-usd, --max-cycles, --telegram-env/--no-telegram, --profile,
  --label become native optional flags that are inert when unset; the Telegram
  env-resolution / verdict-outcome / iteration-cost / profile-loading helpers
  live in skill-chain.py; the budget/cycle halt decision is a pure helper.
- 42.4 fold batch mode into the unified runner: one-skill-over-a-glob available
  natively via --batch; the deprecated shim scripts are removed in Phase 46.
- 42.8 _apply_profile_defaults pure helper.
- 42.9 profile-sourced budget satisfies --overnight cap requirement.
- 42.10 --dry-run must not create output directory trees as a side effect.
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


# ---- 42.1: epilog documents the unified surface -----------------------------

def test_epilog_documents_wrapper_flags():
    """Epilog documents the wrapper flags merged natively in Phase 42."""
    epi = sc.UNIFIED_CLI_EPILOG
    for flag in ("--max-budget-usd", "--max-cycles", "--telegram-env",
                 "--profile", "--label"):
        assert flag in epi, f"epilog must document {flag}"


# ---- 42.8: _apply_profile_defaults pure helper + precedence -----------------

def test_apply_profile_defaults_fills_unset_fields():
    """Profile fills all 6 unset fields when the caller set none of them."""
    args = sc.parse_args(["sst-dev-cycle"])  # no --chain, no wrapper flags
    profile = {
        "watched-chain": "skill-set-cycle",
        "default-loop": "3",
        "default-max-budget-usd": "25.5",
        "default-max-cycles": "4",
        "telegram-env": "/tmp/ssp.env",
        "label": "skill-set",
    }
    sc._apply_profile_defaults(args, profile, explicit_loop=False)
    assert args.chain == "skill-set-cycle"
    assert args.loop == 3
    assert args.max_budget_usd == 25.5
    assert args.max_cycles == 4
    assert Path(args.telegram_env) == Path("/tmp/ssp.env")
    assert args.label == "skill-set"


def test_apply_profile_defaults_explicit_cli_wins_per_field():
    """An explicit CLI value for every field blocks the profile from overwriting it."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".env", delete=False) as f:
        f.write(b"TELEGRAM_BOT_TOKEN=x\n")
        explicit_env = f.name
    try:
        args = sc.parse_args([
            "--chain", "explicit-chain",
            "--loop", "7",
            "--max-budget-usd", "50.0",
            "--max-cycles", "10",
            "--telegram-env", explicit_env,
            "--label", "explicit-label",
        ])
        profile = {
            "watched-chain": "profile-chain",
            "default-loop": "3",
            "default-max-budget-usd": "25.0",
            "default-max-cycles": "5",
            "telegram-env": "/tmp/profile.env",
            "label": "profile-label",
        }
        sc._apply_profile_defaults(args, profile, explicit_loop=True)
        assert args.chain == "explicit-chain"
        assert args.loop == 7
        assert args.max_budget_usd == 50.0
        assert args.max_cycles == 10
        assert Path(args.telegram_env) == Path(explicit_env)
        assert args.label == "explicit-label"
    finally:
        os.unlink(explicit_env)


def test_apply_profile_defaults_explicit_loop_suppresses_max_cycles():
    """When explicit_loop=True, a profile default-max-cycles must NOT be applied.
    This protects overnight-run economic guardrails: an explicit --loop N is the
    operator's ceiling, not a floor for the profile to inflate."""
    args = sc.parse_args(["--chain", "x", "--loop", "5"])
    profile = {"default-max-cycles": "3"}
    sc._apply_profile_defaults(args, profile, explicit_loop=True)
    assert args.max_cycles is None


def test_apply_profile_defaults_no_explicit_loop_fills_max_cycles():
    """When explicit_loop=False, a profile default-max-cycles IS applied."""
    args = sc.parse_args(["--chain", "x"])
    profile = {"default-max-cycles": "3"}
    sc._apply_profile_defaults(args, profile, explicit_loop=False)
    assert args.max_cycles == 3


def test_apply_profile_defaults_empty_profile_is_noop():
    """An empty profile dict leaves all args unchanged."""
    args = sc.parse_args(["--chain", "x"])
    sc._apply_profile_defaults(args, {}, explicit_loop=False)
    assert args.chain == "x"
    assert args.loop is None
    assert args.max_budget_usd is None
    assert args.max_cycles is None


# ---- 42.3: --overnight preset -----------------------------------------------

def test_overnight_flag_parsed():
    """`--overnight` is accepted by parse_args."""
    args = sc.parse_args(["--chain", "x", "--overnight"])
    assert args.overnight is True


def test_preset_overnight_parsed():
    """`--preset overnight` is accepted by parse_args."""
    args = sc.parse_args(["--chain", "x", "--preset", "overnight"])
    assert args.preset == "overnight"


def test_overnight_with_budget_cap_expands():
    """`--overnight` with a budget cap sets loop=0 and loop_delay_random to 300,1800."""
    args = sc.parse_args(["--chain", "x", "--overnight", "--max-budget-usd", "30"])
    sc._apply_preset(args, explicit_loop=False)
    assert args.loop == 0
    assert args.loop_delay_random == "300,1800"


def test_overnight_with_cycle_cap_expands():
    """`--overnight` with a cycle cap sets loop=0."""
    args = sc.parse_args(["--chain", "x", "--overnight", "--max-cycles", "5"])
    sc._apply_preset(args, explicit_loop=False)
    assert args.loop == 0


def test_overnight_without_cap_exits_nonzero():
    """`--overnight` without any budget/cycle cap exits non-zero with a clear message."""
    import pytest
    args = sc.parse_args(["--chain", "x", "--overnight"])
    with pytest.raises(SystemExit) as exc_info:
        sc._apply_preset(args, explicit_loop=False)
    assert exc_info.value.code != 0


def test_overnight_with_explicit_loop_errors():
    """`--overnight` and an explicit `--loop` are mutually exclusive."""
    import pytest
    args = sc.parse_args(["--chain", "x", "--overnight", "--max-budget-usd", "30"])
    args.loop = 5  # simulate explicit --loop
    with pytest.raises(SystemExit) as exc_info:
        sc._apply_preset(args, explicit_loop=True)
    assert exc_info.value.code != 0


def test_overnight_preserves_explicit_loop_delay_random():
    """`--overnight` does not override an explicitly-set --loop-delay-random."""
    args = sc.parse_args([
        "--chain", "x", "--overnight",
        "--max-budget-usd", "30",
        "--loop-delay-random", "60,120",
    ])
    sc._apply_preset(args, explicit_loop=False)
    assert args.loop_delay_random == "60,120"


def test_preset_overnight_equivalent_to_overnight_flag():
    """`--preset overnight` behaves identically to `--overnight`."""
    args = sc.parse_args(["--chain", "x", "--preset", "overnight", "--max-budget-usd", "30"])
    sc._apply_preset(args, explicit_loop=False)
    assert args.loop == 0
    assert args.loop_delay_random == "300,1800"


# ---- 42.9: profile-sourced cap satisfies --overnight cap requirement ----------

# ---- 42.4: --batch mode in skill-chain.py -----------------------------------

def test_batch_flag_accepted_by_parse_args():
    """`--batch GLOB --output-template TMPL` is accepted as a batch trigger."""
    args = sc.parse_args(["sst-dev-cycle", "--batch", "*.md", "--output-template", "{stem}.txt"])
    assert args.batch == "*.md"
    assert args.output_template == "{stem}.txt"


def test_batch_flag_default_is_none():
    """`--batch` is None when not passed (inert, does not change chain behavior)."""
    args = sc.parse_args(["--chain", "x"])
    assert getattr(args, "batch", None) is None


def test_batch_output_template_default_is_none():
    """`--output-template` is None when not passed."""
    args = sc.parse_args(["--chain", "x"])
    assert getattr(args, "output_template", None) is None


def test_render_output_template_stem():
    """render_output_template substitutes {stem}, {name}, {parent}, {ext}."""
    from pathlib import Path
    base = Path("/data")
    p = Path("/data/reports/foo.csv")
    result = sc.render_output_template("{stem}.txt", p, base)
    assert result.name == "foo.txt"


def test_render_output_template_all_tokens():
    """All four supported tokens expand correctly."""
    base = Path("/data")
    p = Path("/data/a/b/foo.csv")
    result = sc.render_output_template("{parent}/{stem}.out", p, base)
    # parent is 'a/b' relative to base, so the output is resolved under base.
    assert result.name == "foo.out"
    assert "a" in str(result) and "b" in str(result)


def test_expand_inputs_basic(tmp_path):
    """expand_inputs finds matching files under the base dir."""
    (tmp_path / "alpha.csv").write_text("a")
    (tmp_path / "beta.csv").write_text("b")
    (tmp_path / "gamma.txt").write_text("c")
    results = sc.expand_inputs("*.csv", tmp_path, None, None, None)
    assert len(results) == 2
    stems = {r.stem for r in results}
    assert stems == {"alpha", "beta"}


def test_expand_inputs_include_filter(tmp_path):
    """expand_inputs include regex limits results."""
    for stem in ("alpha", "beta", "charlie"):
        (tmp_path / f"{stem}.csv").write_text(stem)
    results = sc.expand_inputs("*.csv", tmp_path, r"^al", None, None)
    assert len(results) == 1 and results[0].stem == "alpha"


def test_expand_inputs_exclude_filter(tmp_path):
    """expand_inputs exclude regex removes matching files."""
    for stem in ("alpha", "beta"):
        (tmp_path / f"{stem}.csv").write_text(stem)
    results = sc.expand_inputs("*.csv", tmp_path, None, r"^bet", None)
    assert len(results) == 1 and results[0].stem == "alpha"


def test_expand_inputs_start_at(tmp_path):
    """expand_inputs skips alphabetically-before stems."""
    for stem in ("a", "b", "c"):
        (tmp_path / f"{stem}.csv").write_text(stem)
    results = sc.expand_inputs("*.csv", tmp_path, None, None, "b")
    assert {r.stem for r in results} == {"b", "c"}


def test_batch_epilog_documents_batch():
    """UNIFIED_CLI_EPILOG references --batch so it appears in --help."""
    assert "--batch" in sc.UNIFIED_CLI_EPILOG


# ---- 42.7: unified flag matrix + batch mode ---------------------------------

def test_unified_flag_matrix_batch_mode_present():
    """The unified runner accepts all batch-mode flags without error."""
    args = sc.parse_args([
        "my-skill",
        "--batch", "*.csv",
        "--output-template", "out/{stem}.json",
        "--inputs-cwd", "/tmp",
        "--output-cwd", "/tmp/out",
        "--skip-if-exists",
        "--include", r"^foo",
        "--exclude", r"^bar",
        "--limit", "5",
        "--start-at", "alpha",
        "--dry-run",
        "--on-failure", "continue",
    ])
    assert args.batch == "*.csv"
    assert args.output_template == "out/{stem}.json"
    assert args.limit == 5
    assert args.on_failure == "continue"
    assert args.dry_run is True
    assert args.skip_if_exists is True


def test_overnight_profile_sourced_budget_satisfies_cap_requirement():
    """A profile-provided default-max-budget-usd satisfies --overnight's cap requirement.

    Verifies the ordering guarantee documented in main(): _apply_profile_defaults
    runs BEFORE _apply_preset, so a profile-sourced cap prevents the "requires a
    budget or cycle cap" SystemExit even when no --max-budget-usd is on the CLI.
    """
    args = sc.parse_args(["--chain", "x", "--overnight"])
    assert args.max_budget_usd is None  # no CLI cap
    sc._apply_profile_defaults(args, {"default-max-budget-usd": "25.0"}, explicit_loop=False)
    assert args.max_budget_usd == 25.0  # profile fills it in
    sc._apply_preset(args, explicit_loop=False)  # must not raise
    assert args.loop == 0


# ---- 42.10: --dry-run must not create output directories --------------------

def test_batch_dry_run_does_not_create_output_dirs(tmp_path):
    """--dry-run must not create output directory trees as a side effect.

    Regression for 42.10: mkdir ran before the dry-run early-continue,
    creating empty nested subdirs even when no skill was actually invoked.
    """
    in_dir = tmp_path / "inputs"
    in_dir.mkdir()
    out_dir = tmp_path / "outputs"  # must NOT be created during dry-run
    (in_dir / "alpha.txt").write_text("a")
    (in_dir / "beta.txt").write_text("b")

    args = sc.parse_args([
        "my-skill",
        "--batch", "*.txt",
        "--output-template", "nested/subdir/{stem}.out",
        "--inputs-cwd", str(in_dir),
        "--output-cwd", str(out_dir),
        "--dry-run",
        "--no-log",
    ])

    class _MockHarness(sc.Harness):
        name = "mock"

        def build_command(self, skill_name, *, model=None, effort=None,
                          extra_prompt="", resume_session_id=None):
            return ["echo", skill_name]

    sc.run_batch_mode(args, _MockHarness(), str(tmp_path))

    assert not out_dir.exists(), (
        f"--dry-run must not create output dirs; found: {list(out_dir.rglob('*'))}"
    )
