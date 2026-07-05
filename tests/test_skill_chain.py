"""Tests for rate-limit session-resume in bin/skill-chain.py."""
import importlib.util
import sys
from pathlib import Path
import unittest.mock as mock

_CHAIN_PATH = Path(__file__).parent.parent / "bin" / "skill-chain.py"
_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

ClaudeCodeHarness = sc.ClaudeCodeHarness


def test_build_command_cold_start_has_no_resume():
    """Cold start (no resume_session_id) must not include --resume."""
    h = ClaudeCodeHarness()
    cmd = h.build_command("sst-dev-cycle")
    assert "--resume" not in cmd


def test_build_command_cold_start_has_skill_invocation_prompt():
    """Cold start uses the 'Use the Skill tool to invoke' bootstrap prompt."""
    h = ClaudeCodeHarness()
    cmd = h.build_command("sst-dev-cycle")
    prompt = cmd[-1]
    assert "Use the Skill tool" in prompt
    assert "sst-dev-cycle" in prompt


def test_build_command_resume_includes_resume_flag():
    """When resume_session_id is set, --resume <id> appears in the command."""
    h = ClaudeCodeHarness()
    cmd = h.build_command("sst-dev-cycle", resume_session_id="abc123session")
    assert "--resume" in cmd
    idx = cmd.index("--resume")
    assert cmd[idx + 1] == "abc123session"


def test_build_command_resume_uses_continuation_prompt():
    """Resumed invocation uses a short 'continue' prompt, not the bootstrap."""
    h = ClaudeCodeHarness()
    cmd = h.build_command("sst-dev-cycle", resume_session_id="abc123session")
    prompt = cmd[-1]
    assert prompt == "continue"
    assert "Use the Skill tool" not in prompt


def test_build_command_empty_resume_session_id_falls_back_to_cold():
    """Empty string or None resume_session_id falls back to cold-start behavior."""
    h = ClaudeCodeHarness()
    for bad in ("", None):
        cmd = h.build_command("sst-dev-cycle", resume_session_id=bad)
        assert "--resume" not in cmd
        assert "Use the Skill tool" in cmd[-1]


def test_smoke_second_attempt_command_has_resume():
    """Smoke: build_command called with a captured session_id produces --resume command.

    Simulates what run_skill_with_retry does: first attempt captures session_id,
    second attempt calls build_command with that id.
    """
    h = ClaudeCodeHarness()
    captured_session_id = "sess_xyz_deadbeef12345678"

    # First attempt: cold start (no session_id yet)
    cmd_first = h.build_command("sst-dev-cycle")
    assert "--resume" not in cmd_first

    # Second attempt: resumed with the captured session_id
    cmd_retry = h.build_command("sst-dev-cycle", resume_session_id=captured_session_id)
    assert "--resume" in cmd_retry
    idx = cmd_retry.index("--resume")
    assert cmd_retry[idx + 1] == captured_session_id
    assert cmd_retry[-1] == "continue"


# ---- run_skill_with_retry integration tests (session-id threading) ----------

run_skill_with_retry = sc.run_skill_with_retry


def _make_fake_run_skill(call_kwargs_list, first_record, second_record=(0, {})):
    """Return a fake run_skill that records kwargs and drives a two-call scenario."""
    def fake(_harness, _skill_name, _index, _log_dir, **kwargs):
        call_kwargs_list.append(kwargs.copy())
        if len(call_kwargs_list) == 1:
            return first_record
        return second_record
    return fake


def test_run_skill_with_retry_threads_session_id_on_rate_limit():
    """run_skill_with_retry passes the first call's session_id as resume_session_id on retry.

    Patches run_skill to simulate: first call hits rate-limit and records a
    session_id; second call succeeds. Asserts the second run_skill call receives
    resume_session_id equal to the session_id from the first call's record.
    """
    h = ClaudeCodeHarness()
    captured_session_id = "sess_integ_test_deadbeef"
    pause_records: list = []
    call_kwargs: list = []

    first = (1, {
        "session_id": captured_session_id,
        "rate_limit_signal": {"type": "max_usage", "status": "rejected"},
    })
    fake = _make_fake_run_skill(call_kwargs, first)

    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch("time.sleep"):
        rc, _ = run_skill_with_retry(
            h, "sst-dev-cycle", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=pause_records,
        )

    assert rc == 0
    assert len(call_kwargs) == 2, "run_skill should be called twice (first + one retry)"
    assert call_kwargs[0].get("resume_session_id") is None, \
        "first attempt must be a cold start with no resume_session_id"
    assert call_kwargs[1].get("resume_session_id") == captured_session_id, \
        "retry must carry the session_id captured from the first call's record"


def test_run_skill_with_retry_cold_when_no_session_id_in_record():
    """run_skill_with_retry falls back to cold start when first call records no session_id."""
    h = ClaudeCodeHarness()
    pause_records: list = []
    call_kwargs: list = []

    first = (1, {"rate_limit_signal": {"type": "max_usage", "status": "rejected"}})
    fake = _make_fake_run_skill(call_kwargs, first)

    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch("time.sleep"):
        rc, _ = run_skill_with_retry(
            h, "sst-dev-cycle", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=pause_records,
        )

    assert rc == 0
    assert len(call_kwargs) == 2
    assert call_kwargs[1].get("resume_session_id") is None, \
        "no session_id in first record means retry must fall back to cold start"


def test_run_skill_with_retry_post_pause_delay_flat():
    """A configured flat loop_delay fires as a post-pause sleep before retrying."""
    h = ClaudeCodeHarness()
    pause_records: list = []
    call_kwargs: list = []

    first = (1, {"rate_limit_signal": {"type": "max_usage", "status": "rejected"}})
    fake = _make_fake_run_skill(call_kwargs, first)

    sleep_calls: list[float] = []
    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch.object(sc.time, "sleep", side_effect=sleep_calls.append):
        rc, _ = run_skill_with_retry(
            h, "sst-dev-cycle", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=pause_records,
            loop_delay=42.0,
        )

    assert rc == 0
    assert 42.0 in sleep_calls, \
        f"expected post-pause flat delay 42.0 in sleep calls; got {sleep_calls!r}"
    assert pause_records[0].get("post_pause_delay") == 42.0


def test_run_skill_with_retry_post_pause_delay_random():
    """A configured loop_delay_random samples a post-pause sleep from [min, max]."""
    h = ClaudeCodeHarness()
    pause_records: list = []
    call_kwargs: list = []

    first = (1, {"rate_limit_signal": {"type": "max_usage", "status": "rejected"}})
    fake = _make_fake_run_skill(call_kwargs, first)

    sleep_calls: list[float] = []
    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch.object(sc.time, "sleep", side_effect=sleep_calls.append), \
         mock.patch.object(sc.random, "uniform", return_value=123.4):
        rc, _ = run_skill_with_retry(
            h, "sst-dev-cycle", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=pause_records,
            loop_delay_random=(60.0, 600.0),
        )

    assert rc == 0
    assert 123.4 in sleep_calls, \
        f"expected sampled post-pause delay 123.4 in sleep calls; got {sleep_calls!r}"
    assert pause_records[0].get("post_pause_delay") == 123.4


def test_run_skill_with_retry_no_post_pause_delay_when_unset():
    """With no loop_delay configured, no post-pause delay is recorded or slept."""
    h = ClaudeCodeHarness()
    pause_records: list = []
    call_kwargs: list = []

    first = (1, {"rate_limit_signal": {"type": "max_usage", "status": "rejected"}})
    fake = _make_fake_run_skill(call_kwargs, first)

    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch("time.sleep"):
        rc, _ = run_skill_with_retry(
            h, "sst-dev-cycle", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=pause_records,
        )

    assert rc == 0
    assert "post_pause_delay" not in pause_records[0], \
        "unset loop_delay must not record a post_pause_delay key"


# ---- [blocked-on-human] sentinel (Phase 31.8) --------------------------------

def test_blocked_on_human_sentinel_re_exists():
    """BLOCKED_ON_HUMAN_SENTINEL_RE must be defined on the module."""
    assert hasattr(sc, "BLOCKED_ON_HUMAN_SENTINEL_RE"), \
        "BLOCKED_ON_HUMAN_SENTINEL_RE not found in skill_chain module"


def test_blocked_on_human_sentinel_re_matches_canonical_form():
    """Matches the canonical [blocked-on-human] H<phase>.<n> <title> format."""
    line = "[blocked-on-human] H3.1 Set STRAPI secrets"
    assert sc.BLOCKED_ON_HUMAN_SENTINEL_RE.search(line) is not None


def test_blocked_on_human_sentinel_re_captures_reason():
    """Captures the text after [blocked-on-human] as the reason group."""
    line = "[blocked-on-human] H3.1 Set 7 STRAPI secrets"
    m = sc.BLOCKED_ON_HUMAN_SENTINEL_RE.search(line)
    assert m is not None
    assert m.group(1) == "H3.1 Set 7 STRAPI secrets"


def test_blocked_on_human_sentinel_re_no_match_on_no_work():
    """BLOCKED_ON_HUMAN_SENTINEL_RE does not match the [no-work] sentinel."""
    line = "[no-work] queue empty and spec fully checked"
    assert sc.BLOCKED_ON_HUMAN_SENTINEL_RE.search(line) is None


def test_blocked_on_human_sentinel_re_matches_bare_sentinel():
    """Matches [blocked-on-human] with no trailing reason."""
    line = "[blocked-on-human]"
    assert sc.BLOCKED_ON_HUMAN_SENTINEL_RE.search(line) is not None


def test_blocked_on_human_sentinel_re_matches_in_multiline_output():
    """Finds the sentinel inside a larger block of assistant text."""
    output = (
        "Starting pre-flight...\n"
        "Picked item: 3.1\n"
        "[blocked-on-human] H3.1 Set STRAPI secrets\n"
        "Exiting cleanly.\n"
    )
    assert sc.BLOCKED_ON_HUMAN_SENTINEL_RE.search(output) is not None


# ---- run_iteration integration test (blocked_on_human bail, Phase 31.11) -----

run_iteration = sc.run_iteration

_ROUTE_RECORD = {
    "difficulty": "medium",
    "model_floor": "sonnet",
    "effort_floor": "high",
    "item_model": "sonnet",
    "item_effort": "high",
    "effective_model": "sonnet",
    "effective_effort": "high",
}


def test_run_iteration_blocked_on_human_bail_skips_remaining_skills():
    """run_iteration aborts after the first skill fires [blocked-on-human].

    Patches run_skill_with_retry so the first call returns a record with
    blocked_on_human set; asserts that:
    - iter_manifest["blocked_on_human"] records the bailing skill + reason
    - the second skill is never called
    - iter_manifest exit_code is 0 (bail is clean, not an error)
    """
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        if skill_name == "sst-dev-cycle":
            return (0, {"blocked_on_human": "H3.1 Set STRAPI secrets"})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-dev-review"],
            None,    # iter_log_dir=None skips snapshot writes
            None,    # auto_supervisor
            1,       # iteration
            1,       # total_iterations
            "/tmp",  # cwd (everything patched, actual path irrelevant)
        )

    assert rc == 0, "blocked-on-human bail must be a clean exit (rc=0)"
    assert "blocked_on_human" in iter_manifest, \
        "iter_manifest must contain blocked_on_human key after bail"
    assert iter_manifest["blocked_on_human"]["skill"] == "sst-dev-cycle"
    assert iter_manifest["blocked_on_human"]["reason"] == "H3.1 Set STRAPI secrets"
    assert calls == ["sst-dev-cycle"], \
        "sst-dev-review must NOT be called after blocked-on-human bail"


# ---- [no-work] phase-completion sentinel variant (Phase 38.3) ----------------
#
# 38.3 adds a phase-scoped bail to sst-dev-cycle that emits
# `[no-work] phase <N> complete on <branch>; awaiting human branch setup for
# phase <N+1>`. The acceptance requires confirming bin/skill-chain.py's existing
# NO_WORK_SENTINEL_RE + no-work bail path recognize this variant as a
# loop-aborting [no-work] (no new runner code needed; these guard the contract
# against a future regex tightening). The no-work bail path had ZERO tests
# before this; these also backfill that coverage gap.

_PHASE_COMPLETE_SENTINEL = (
    "[no-work] phase 38 complete on feature/phase-38; "
    "awaiting human branch setup for phase 39"
)


def test_no_work_sentinel_re_matches_phase_completion_variant():
    """NO_WORK_SENTINEL_RE recognizes the 38.3 phase-completion sentinel."""
    assert sc.NO_WORK_SENTINEL_RE.search(_PHASE_COMPLETE_SENTINEL) is not None


def test_no_work_sentinel_re_captures_phase_completion_reason():
    """The reason group captures the full phase-completion message text."""
    m = sc.NO_WORK_SENTINEL_RE.search(_PHASE_COMPLETE_SENTINEL)
    assert m is not None
    assert m.group(1) == (
        "phase 38 complete on feature/phase-38; "
        "awaiting human branch setup for phase 39"
    )


def test_no_work_sentinel_re_matches_phase_completion_in_multiline_output():
    """Phase-completion sentinel is found when embedded in surrounding output."""
    output = (
        "Read docs/SPEC.md; phase 38 has no open items on this branch.\n"
        f"{_PHASE_COMPLETE_SENTINEL}\n"
        "Exiting without picking work.\n"
    )
    assert sc.NO_WORK_SENTINEL_RE.search(output) is not None


def test_blocked_on_human_re_does_not_match_phase_completion_variant():
    """The phase-completion bail is a [no-work] variant, NOT blocked-on-human."""
    assert sc.BLOCKED_ON_HUMAN_SENTINEL_RE.search(_PHASE_COMPLETE_SENTINEL) is None


def test_no_work_bail_fires_for_phase_completion_when_no_commit():
    """_no_work_bail_should_fire returns True for a phase-completion bail
    record when no commit shipped (sha unchanged)."""
    record = {"no_work_bail": (
        "phase 38 complete on feature/phase-38; "
        "awaiting human branch setup for phase 39"
    )}
    assert sc._no_work_bail_should_fire(record, "abc1234", "abc1234") is True


def test_no_work_bail_suppressed_for_phase_completion_when_commit_shipped():
    """A commit landing during the skill suppresses even a phase-completion
    sentinel (false-positive guard: real work shipped)."""
    record = {"no_work_bail": (
        "phase 38 complete on feature/phase-38; "
        "awaiting human branch setup for phase 39"
    )}
    assert sc._no_work_bail_should_fire(record, "abc1234", "def5678") is False


def test_run_iteration_phase_completion_no_work_bail_skips_remaining_skills():
    """run_iteration aborts after the dev skill fires the phase-completion
    [no-work] variant: records no_work_bail on the iter manifest and never
    calls the review skill. Mirrors the blocked-on-human integration test;
    the no-work bail path had no integration coverage before 38.3."""
    h = ClaudeCodeHarness()
    calls: list = []

    reason = (
        "phase 38 complete on feature/phase-38; "
        "awaiting human branch setup for phase 39"
    )

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        if skill_name == "sst-dev-cycle":
            return (0, {"no_work_bail": reason})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("hard", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("opus", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-dev-review"],
            None,    # iter_log_dir=None skips snapshot writes
            None,    # auto_supervisor
            1,       # iteration
            1,       # total_iterations
            "/tmp",  # cwd (everything patched, actual path irrelevant)
        )

    assert rc == 0, "phase-completion no-work bail must be a clean exit (rc=0)"
    assert "no_work_bail" in iter_manifest, \
        "iter_manifest must record no_work_bail after the phase-completion bail"
    assert iter_manifest["no_work_bail"]["skill"] == "sst-dev-cycle"
    assert iter_manifest["no_work_bail"]["reason"] == reason
    assert calls == ["sst-dev-cycle"], \
        "sst-dev-review must NOT be called after a phase-completion no-work bail"


# ---- markdown-decorated control-sentinel tolerance --------------------------
#
# A skill routinely wraps its sentinel line in inline-code backticks or
# bold/italic markers. A bare `^\s*\[` anchor missed the decorated form, so the
# sentinel silently never fired and the loop ran the whole iteration + halted only
# on the much-later supervisor escalation instead of aborting immediately. The
# four loop-control sentinels now skip any leading non-alphanumeric wrapper
# (`[\W_]*`) and strip a trailing wrapper from the captured reason. These guard
# that fix (the batch-pick / picked-difficulty sentinels were already covered).

# The exact lines a dev emitted in the field that the old regex missed.
_FIELD_BACKTICKED_NO_WORK = (
    "`[no-work] phase complete on the feature branch; no value-bearing pickable "
    "item (lone remaining entry parked to deferred work as confirmed dead code).`"
)
_FIELD_BACKTICKED_SKIP_TESTER = "`[skip-tester] no pick, no source change.`"


def test_no_work_sentinel_re_matches_backtick_wrapped_field_line():
    """The exact backtick-wrapped [no-work] line from the field now fires."""
    m = sc.NO_WORK_SENTINEL_RE.search(_FIELD_BACKTICKED_NO_WORK)
    assert m is not None
    # reason captured without the wrapping backticks
    assert m.group(1).startswith("phase complete on the feature branch")
    assert not m.group(1).endswith("`")


def test_skip_tester_sentinel_re_matches_backtick_wrapped_field_line():
    m = sc.SKIP_TESTER_SENTINEL_RE.search(_FIELD_BACKTICKED_SKIP_TESTER)
    assert m is not None
    assert m.group(1) == "no pick, no source change."


_CONTROL_SENTINELS = {
    "no-work": sc.NO_WORK_SENTINEL_RE,
    "blocked-on-human": sc.BLOCKED_ON_HUMAN_SENTINEL_RE,
    "skip-tester": sc.SKIP_TESTER_SENTINEL_RE,
    "no-test-work": sc.NO_TEST_WORK_SENTINEL_RE,
}


def test_control_sentinels_match_decorated_forms():
    """All four loop-control sentinels fire through common markdown wrappers and
    capture a clean reason (no wrapping chars). The underscore case is why the
    leading class is `[\\W_]*` and not `\\W*` (`\\W` excludes `_`)."""
    wraps = [
        "`[{t}] reason`",    # inline code (the form missed in the field)
        "**[{t}] reason**",  # bold
        "_[{t}] reason_",    # italic via underscore
        "> [{t}] reason",    # blockquote
        "- [{t}] reason",    # list bullet
        "[{t}] reason",      # bare
    ]
    for token, rx in _CONTROL_SENTINELS.items():
        for w in wraps:
            text = w.format(t=token)
            m = rx.search(text)
            assert m is not None, f"[{token}] failed to match {text!r}"
            assert m.group(1) == "reason", \
                f"[{token}] captured {m.group(1)!r} from {text!r}"


def test_control_sentinels_no_match_mid_prose():
    """Words before the bracket (a mid-prose mention) must NOT trip the sentinel —
    only leading decoration may precede it."""
    for token in ("no-work", "skip-tester"):
        rx = _CONTROL_SENTINELS[token]
        assert rx.search(f"see the [{token}] flag here") is None
        assert rx.search(
            f"note: `[{token}]` is the sentinel and then more prose") is None


# ---- _incomplete_cycle_detected unit tests (Phase 36) -----------------------

_incomplete_cycle_detected = sc._incomplete_cycle_detected


def test_incomplete_cycle_detected_false_when_no_todo(tmp_path):
    """Returns False when docs/TODO.md does not exist."""
    assert _incomplete_cycle_detected(str(tmp_path)) is False


def test_incomplete_cycle_detected_false_on_clean_todo(tmp_path):
    """Returns False when In flight is empty and no PENDING placeholder."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "TODO.md").write_text(
        "## In flight\n\n<!--\n  empty\n-->\n\n## Just shipped\n",
        encoding="utf-8",
    )
    assert _incomplete_cycle_detected(str(tmp_path)) is False


def test_incomplete_cycle_detected_true_on_in_flight_bullet(tmp_path):
    """Returns True when ## In flight contains a '- [' entry."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "TODO.md").write_text(
        "## In flight\n\n- [skill-set-dev @ 2026-05-25T13:00:00Z] working\n\n## Just shipped\n",
        encoding="utf-8",
    )
    assert _incomplete_cycle_detected(str(tmp_path)) is True


def test_incomplete_cycle_detected_true_on_pending_placeholder(tmp_path):
    """Returns True when 'Sanitize: must-fix=PENDING' appears in TODO.md."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "TODO.md").write_text(
        "## Just shipped\n\n- some item; Sanitize: must-fix=PENDING\n",
        encoding="utf-8",
    )
    assert _incomplete_cycle_detected(str(tmp_path)) is True


def test_incomplete_cycle_detected_false_comment_text_not_bullet(tmp_path):
    """HTML comment prose inside ## In flight section is not an active entry."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "TODO.md").write_text(
        "## In flight\n\n<!--\n  - [example] comment line\n-->\n\n## Just shipped\n",
        encoding="utf-8",
    )
    assert _incomplete_cycle_detected(str(tmp_path)) is False


# ---- run_iteration integration test (contract_violation, Phase 36) ----------


def test_run_iteration_contract_violation_passes_to_review():
    """Phase 36: dev exits [ok] with no commit in a dev+review chain → violation
    recorded but sst-dev-review IS called (recovery handoff, not abort).

    Patches:
    - run_skill_with_retry: all skills return rc=0 with no sentinel
    - _git_sha: always returns the same sha (no commit from the mock)
    - _incomplete_cycle_detected: returns True (simulates dirty TODO.md)
    Asserts:
    - iter_manifest["contract_violation"]["kind"] == "incomplete-cycle"
    - sst-dev-review IS invoked (runner passes control for recovery)
    - exit code is 0
    """
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=True):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-dev-review"],
            None,
            None,
            1,
            1,
            "/tmp",
        )

    assert rc == 0, "contract-violation with a follower skill must be a clean exit (rc=0)"
    assert "contract_violation" in iter_manifest, \
        "iter_manifest must record contract_violation"
    assert iter_manifest["contract_violation"]["kind"] == "incomplete-cycle"
    assert iter_manifest["contract_violation"]["skill"] == "sst-dev-cycle"
    assert calls == ["sst-dev-cycle", "sst-dev-review"], \
        "sst-dev-review must be called for recovery when it follows the dev skill"


def test_run_iteration_contract_violation_aborts_without_next_skill():
    """Phase 36: dev exits [ok] with no commit in a solo-dev chain → abort.

    When the dev skill runs alone (no follower), the old abort behavior is
    preserved: contract_violation is recorded and the chain breaks.

    Patches:
    - run_skill_with_retry: dev returns rc=0 with no sentinel
    - _git_sha: always returns the same sha (no commit)
    - _incomplete_cycle_detected: returns True (simulates dirty TODO.md)
    Asserts:
    - iter_manifest["contract_violation"]["kind"] == "incomplete-cycle"
    - no further skill is called
    - exit code is 0 (violation is a clean abort, not an error)
    """
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=True):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle"],
            None,
            None,
            1,
            1,
            "/tmp",
        )

    assert rc == 0, "contract-violation bail must be a clean exit (rc=0)"
    assert "contract_violation" in iter_manifest, \
        "iter_manifest must contain contract_violation after detection"
    assert iter_manifest["contract_violation"]["kind"] == "incomplete-cycle"
    assert iter_manifest["contract_violation"]["skill"] == "sst-dev-cycle"
    assert calls == ["sst-dev-cycle"], \
        "no further skill must be called after contract_violation with no follower"


def test_run_iteration_contract_violation_aborts_when_next_is_auto_supervisor():
    """Phase 38.12: dev exits [ok] with no commit in a dev+auto-supervisor chain → abort.

    When the only follower skill is the auto-appended supervisor, the pass-through
    guard must NOT fire — the auto-supervisor should not receive orphaned dev work.
    The abort path is taken as if no follower existed.

    Patches:
    - run_skill_with_retry: dev returns rc=0 with no sentinel
    - _git_sha: always returns the same sha (no commit)
    - _incomplete_cycle_detected: returns True (simulates dirty TODO.md)
    Asserts:
    - iter_manifest["contract_violation"]["kind"] == "incomplete-cycle"
    - sst-supervisor is NOT called (abort path taken, not recovery handoff)
    - exit code is 0
    """
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=True):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-supervisor"],
            None,
            "sst-supervisor",
            1,
            1,
            "/tmp",
        )

    assert rc == 0, "contract-violation bail must be a clean exit (rc=0)"
    assert "contract_violation" in iter_manifest, \
        "iter_manifest must contain contract_violation after detection"
    assert iter_manifest["contract_violation"]["kind"] == "incomplete-cycle"
    assert iter_manifest["contract_violation"]["skill"] == "sst-dev-cycle"
    assert calls == ["sst-dev-cycle"], \
        "sst-supervisor must NOT be called when it is the auto-supervisor follower"


def test_run_iteration_no_contract_violation_when_commit_shipped():
    """Phase 36: no violation when sha changes (real commit shipped).

    Even if _incomplete_cycle_detected would return True, a commit means
    the dev finished properly — the incomplete-cycle check is sha-gated.
    """
    h = ClaudeCodeHarness()
    # _git_sha is called 4 times for a 1-skill iter: iter_manifest init,
    # sha_before_skill, sha_after_skill, iter_manifest git_sha_after.
    sha_sequence = iter(["abc1234", "abc1234", "def5678", "def5678"])

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", side_effect=lambda _: next(sha_sequence)), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=True):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle"],
            None,
            None,
            1,
            1,
            "/tmp",
        )

    assert rc == 0
    assert "contract_violation" not in iter_manifest, \
        "contract_violation must NOT fire when a commit shipped"


def _make_supervisor(skills_dir: Path, name: str) -> None:
    d = skills_dir / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text("---\nname: " + name + "\n---\n", encoding="utf-8")


def test_find_local_supervisor_prefers_proprietary(tmp_path, monkeypatch):
    """A project-local *-supervisor wins over the transferable fallback."""
    proj = tmp_path / "proj"
    _make_supervisor(proj / ".claude" / "skills", "cm-supervisor")
    home = tmp_path / "home"
    _make_supervisor(home / ".claude" / "skills", "sst-supervisor")
    monkeypatch.setenv("HOME", str(home))
    assert sc.find_local_supervisor(str(proj)) == "cm-supervisor"


def test_find_local_supervisor_falls_back_to_transferable(tmp_path, monkeypatch):
    """No proprietary supervisor in cwd → fall back to transferable sst-supervisor in ~/.claude/skills."""
    proj = tmp_path / "proj"
    # A non-supervisor skill present, but no *-supervisor.
    (proj / ".claude" / "skills" / "skill-set-manager").mkdir(parents=True)
    (proj / ".claude" / "skills" / "skill-set-manager" / "SKILL.md").write_text("x", encoding="utf-8")
    home = tmp_path / "home"
    _make_supervisor(home / ".claude" / "skills", "sst-supervisor")
    monkeypatch.setenv("HOME", str(home))
    assert sc.find_local_supervisor(str(proj)) == "sst-supervisor"


def test_find_local_supervisor_none_when_neither_present(tmp_path, monkeypatch):
    """No proprietary supervisor and no transferable fallback → None."""
    proj = tmp_path / "proj"
    (proj / ".claude" / "skills").mkdir(parents=True)
    home = tmp_path / "home"
    (home / ".claude" / "skills").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    assert sc.find_local_supervisor(str(proj)) is None


def test_find_local_supervisor_multiple_proprietary_returns_none(tmp_path, monkeypatch):
    """Ambiguous (>1) proprietary supervisors → None, no fallback (user must pick)."""
    proj = tmp_path / "proj"
    _make_supervisor(proj / ".claude" / "skills", "cm-supervisor")
    _make_supervisor(proj / ".claude" / "skills", "other-supervisor")
    home = tmp_path / "home"
    _make_supervisor(home / ".claude" / "skills", "sst-supervisor")
    monkeypatch.setenv("HOME", str(home))
    assert sc.find_local_supervisor(str(proj)) is None


# ---- Per-agent turn wind-down (graceful --max-turns) ------------------------

def _max_turns_value(cmd):
    """Extract the integer following --max-turns in a built command."""
    idx = cmd.index("--max-turns")
    return int(cmd[idx + 1])


def test_build_command_default_hard_turn_cap_is_250():
    """Every agent gets the hard --max-turns backstop (default 250)."""
    h = ClaudeCodeHarness()
    for skill in ("sst-dev-cycle", "sst-tester", "sst-supervisor"):
        assert _max_turns_value(h.build_command(skill)) == sc.DEFAULT_MAX_TURNS == 250


def test_build_command_tester_cold_start_appends_wind_down():
    """A *-tester cold start advertises the soft budget below the hard cap."""
    h = ClaudeCodeHarness()
    prompt = h.build_command("sst-tester")[-1]
    hard = sc.DEFAULT_MAX_TURNS
    soft = hard - sc.WIND_DOWN_TURN_HEADROOM
    assert "Turn budget" in prompt
    assert str(hard) in prompt
    assert str(soft) in prompt
    # Still invokes the skill — the directive is appended, not a replacement.
    assert "Use the Skill tool" in prompt
    assert "sst-tester" in prompt


def test_build_command_proprietary_tester_also_winds_down():
    """Proprietary *-tester wrappers (e.g. ssp-cm-tester) get the directive too."""
    h = ClaudeCodeHarness()
    prompt = h.build_command("ssp-cm-tester")[-1]
    assert "Turn budget" in prompt


def test_build_command_non_tester_has_no_wind_down():
    """Non-tester skills do not carry the soft wind-down directive."""
    h = ClaudeCodeHarness()
    for skill in ("sst-dev-cycle", "sst-dev-review", "sst-supervisor", "ssp-cm-dev"):
        prompt = h.build_command(skill)[-1]
        assert "Turn budget" not in prompt


def test_build_command_tester_resume_keeps_bare_continue():
    """A resumed tester (post rate-limit pause) keeps the bare 'continue' prompt."""
    h = ClaudeCodeHarness()
    prompt = h.build_command("sst-tester", resume_session_id="sess_abc123")[-1]
    assert prompt == "continue"
    assert "Turn budget" not in prompt


def test_build_command_custom_max_turns_tracks_soft_budget():
    """Overriding harness.max_turns moves both the hard cap and the advertised soft budget."""
    h = ClaudeCodeHarness()
    h.max_turns = 300
    cmd = h.build_command("sst-tester")
    assert _max_turns_value(cmd) == 300
    prompt = cmd[-1]
    assert "300" in prompt           # hard
    assert "250" in prompt           # soft = 300 - 50


def test_build_command_tiny_max_turns_soft_budget_floored():
    """A pathologically small cap floors the soft budget at >= 1 (no negative)."""
    h = ClaudeCodeHarness()
    h.max_turns = 10
    prompt = h.build_command("sst-tester")[-1]
    assert "Turn budget" in prompt   # still injected; just degenerate headroom


# ---- "never both" runner enforcement (Phase 49) ------------------------------
#
# A dev skill that WRITES a tester-guidance.md has, by writing it, committed the
# cycle to a tester RUN. Emitting [skip-tester] in the same run is a
# self-contradiction ("never both"). Prose-level "pick exactly one" did not
# converge across repeated iters, so bin/skill-chain.py enforces it at the
# runner level: handle_event flags the guidance write on the skill record, and
# run_iteration VOIDS the skip (runs the tester anyway) when the flag is set.
# Keyed on the skill's own tool-use this run, not a stale on-disk file.

def _guidance_write_event(file_path):
    """An assistant event whose single tool_use writes to file_path."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "name": "Write",
                 "input": {"file_path": file_path, "content": "guidance"}},
            ]
        },
    }


def _guidance_read_event(file_path):
    """An assistant event whose single tool_use reads file_path."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "name": "Read",
                 "input": {"file_path": file_path}},
            ]
        },
    }


def _guidance_edit_event(file_path):
    """An assistant event whose single tool_use edits file_path."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "name": "Edit",
                 "input": {"file_path": file_path,
                           "old_string": "x", "new_string": "y"}},
            ]
        },
    }


def test_handle_event_detects_tester_guidance_write():
    """A Write whose file_path ends in tester-guidance.md sets the record flag."""
    rec: dict = {}
    sink = sc._Sink(None)
    sc.handle_event(sink, _guidance_write_event("/run/iter_01/tester-guidance.md"), rec)
    assert rec.get("wrote_tester_guidance") is True


def test_handle_event_ignores_other_file_writes():
    """A Write to an unrelated file does NOT set the guidance flag."""
    rec: dict = {}
    sink = sc._Sink(None)
    sc.handle_event(sink, _guidance_write_event("/run/iter_01/some-other-file.md"), rec)
    assert "wrote_tester_guidance" not in rec


def test_handle_event_read_does_not_trip_guidance_flag():
    """A Read of tester-guidance.md must NOT set wrote_tester_guidance.

    A dev that merely reads a stale guidance file from a prior cycle would
    otherwise trip the Phase 49 never-both gate and get a legitimate
    [skip-tester] incorrectly voided.
    """
    rec: dict = {}
    sink = sc._Sink(None)
    sc.handle_event(sink, _guidance_read_event("/run/iter_01/tester-guidance.md"), rec)
    assert "wrote_tester_guidance" not in rec, (
        "Read tool must NOT set wrote_tester_guidance; only Write/Edit should"
    )


def test_handle_event_edit_sets_guidance_flag():
    """An Edit whose file_path ends in tester-guidance.md sets the record flag."""
    rec: dict = {}
    sink = sc._Sink(None)
    sc.handle_event(sink, _guidance_edit_event("/run/iter_01/tester-guidance.md"), rec)
    assert rec.get("wrote_tester_guidance") is True


def test_run_iteration_skip_tester_voided_when_guidance_written():
    """Dev that wrote guidance AND emitted [skip-tester] -> tester runs anyway.

    The skip is self-contradictory ('never both'); run_iteration must void it,
    keep the tester in the run list (so it IS called), and record the void in
    the iter manifest rather than the normal tester_skipped entry.
    """
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        if skill_name == "sst-dev-cycle":
            return (0, {"skip_tester": "refactor-only: no UI surface change",
                        "wrote_tester_guidance": True})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-tester", "sst-dev-review"],
            None, None, 1, 1, "/tmp",
        )

    assert rc == 0
    assert "sst-tester" in calls, \
        "tester MUST run when the dev wrote guidance + emitted skip (never-both)"
    assert "tester_skip_voided" in iter_manifest, \
        "the voided skip must be recorded in the iter manifest"
    assert iter_manifest["tester_skip_voided"]["emitted_by"] == "sst-dev-cycle"
    assert "tester_skipped" not in iter_manifest, \
        "a voided skip must NOT also record a normal tester_skipped entry"


def test_run_iteration_skip_tester_honored_when_no_guidance():
    """Dev that emitted [skip-tester] WITHOUT writing guidance -> tester skipped.

    Preserves the existing Phase 41.10 behavior: a legitimate backend-only skip
    pops the tester from the run list (it is never called).
    """
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        if skill_name == "sst-dev-cycle":
            return (0, {"skip_tester": "backend-only: pytest + SQL"})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-tester", "sst-dev-review"],
            None, None, 1, 1, "/tmp",
        )

    assert rc == 0
    assert "sst-tester" not in calls, \
        "tester must be skipped on a legitimate guidance-free [skip-tester]"
    assert iter_manifest.get("tester_skipped", {}).get("skill") == "sst-tester"
    assert "tester_skip_voided" not in iter_manifest


def test_run_iteration_skip_does_not_leak_into_caller_skills_list():
    """A one-iteration [skip-tester] pop must NOT mutate the caller's list.

    skills_to_run is built ONCE in main() and passed by reference on every
    iteration. Before the per-call copy, a legitimate tests-only [skip-tester]
    in an early iter popped the tester from that shared list, so it was
    PERMANENTLY gone for every later iter (which then shipped UI work with no
    in-loop verification, and a real regression reached the deployed app). This
    guards the fix: the caller's list stays intact and a later no-skip iter
    still runs the tester.
    """
    h = ClaudeCodeHarness()
    shared = ["sst-dev-cycle", "sst-tester", "sst-dev-review"]

    def fake_skip(_harness, skill_name, _idx, _log_dir, **kwargs):
        if skill_name == "sst-dev-cycle":
            return (0, {"skip_tester": "tests-only: web/server/tests (no UI surface)"})
        return (0, {})

    calls2: list = []

    def fake_no_skip(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls2.append(skill_name)
        return (0, {})

    with mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"):
        # iter 1: legitimate skip pops the tester from run_iteration's LOCAL copy
        with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_skip):
            rc1, m1 = run_iteration(h, shared, None, None, 1, 2, "/tmp")
        # iter 2: caller passes the SAME list object again; dev does NOT skip
        with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_no_skip):
            rc2, m2 = run_iteration(h, shared, None, None, 2, 2, "/tmp")

    assert rc1 == 0 and rc2 == 0
    assert shared == ["sst-dev-cycle", "sst-tester", "sst-dev-review"], \
        "run_iteration must not mutate the caller's shared skills_to_run list"
    assert m1.get("tester_skipped", {}).get("skill") == "sst-tester"
    assert "sst-tester" in calls2, \
        "a later no-skip iter must still run the tester (no cross-iter skip leak)"


# ---- [batch-pick] emission gate (Phase 50) ----------------------------------
#
# sst-dev-cycle §1 mandates a `[batch-pick] N items @ <difficulty>; ...` block
# at pick time (even for single-item picks). The dev had stopped emitting it for
# many consecutive iters, silently degrading downstream batch-coherence review
# (sst-dev-review §2.10) and stuck-item detection (sst-supervisor §3.6) to
# bracket-parsing fallbacks. The runner flags its ABSENCE on a dev iter that
# shipped a commit as a NON-FATAL contract violation (recorded in the iter
# MANIFEST + printed) so the gap is deterministic, not jsonl-grep-only. Keyed on
# a committed dev iter so testers/reviews/supervisors (which do not commit) are
# excluded; a `-tester` name guard covers a solo tester sweep at i==0.

_BATCH_PICK_LINE = ("[batch-pick] 1 items @ easy; window-target ~150k; "
                    "rationale: only actionable item this cycle")


def _sha_commit_seq():
    """A _git_sha side_effect where sha_before != sha_after (a commit shipped),
    robust to extra calls: s0 for the first 2 calls (iter-init, sha_before),
    s1 thereafter (sha_after + iter-final)."""
    state = {"n": 0}
    def f(_cwd):
        state["n"] += 1
        return "s0" if state["n"] <= 2 else "s1"
    return f


def test_batch_pick_sentinel_re_matches_canonical_block():
    assert sc.BATCH_PICK_SENTINEL_RE.search(_BATCH_PICK_LINE)


def test_batch_pick_sentinel_re_matches_multi_item_block():
    assert sc.BATCH_PICK_SENTINEL_RE.search(
        "[batch-pick] 3 items @ medium; window-target ~250k; rationale: same-file cluster")


def test_batch_pick_sentinel_re_no_match_when_absent():
    assert sc.BATCH_PICK_SENTINEL_RE.search("just some prose with no sentinel") is None


def test_batch_pick_sentinel_re_matches_bold_wrapped():
    """**[batch-pick]** (bold markdown) must not trip the false-flag gate."""
    assert sc.BATCH_PICK_SENTINEL_RE.search(
        "**[batch-pick]** 1 items @ easy; window-target ~100k; rationale: only item")


def test_batch_pick_sentinel_re_matches_backtick_wrapped():
    """`[batch-pick]` (backtick markdown) must be detected."""
    assert sc.BATCH_PICK_SENTINEL_RE.search(
        "`[batch-pick]` 1 items @ medium; window-target ~200k; rationale: only item")


def test_picked_difficulty_re_matches_bold_wrapped():
    """**[picked-difficulty: medium]** must set picked_difficulty and not trigger batch_pick_missing."""
    assert sc.PICKED_DIFFICULTY_SENTINEL_RE.search("**[picked-difficulty: medium]**")


def test_picked_difficulty_re_matches_backtick_wrapped():
    """`[picked-difficulty: easy]` must be detected."""
    assert sc.PICKED_DIFFICULTY_SENTINEL_RE.search("`[picked-difficulty: easy]`")


def test_handle_event_detects_bold_wrapped_batch_pick_and_difficulty():
    """A dev that emits **[batch-pick]** + **[picked-difficulty: medium]** (bold markdown)
    must set emitted_batch_pick=True and picked_difficulty='medium' with no batch_pick_missing."""
    rec: dict = {}
    bold_batch = "**[batch-pick]** 1 items @ medium; window-target ~200k; rationale: only item"
    bold_diff  = "**[picked-difficulty: medium]**"
    sc.handle_event(sc._Sink(None), {
        "type": "assistant",
        "message": {"content": [
            {"type": "text", "text": bold_batch + "\n" + bold_diff}]},
    }, rec)
    assert rec.get("emitted_batch_pick") is True, "bold-wrapped [batch-pick] must set emitted_batch_pick"
    assert rec.get("picked_difficulty") == "medium", "bold-wrapped [picked-difficulty:] must set picked_difficulty"


def test_handle_event_detects_batch_pick_block():
    rec: dict = {}
    sc.handle_event(sc._Sink(None), {
        "type": "assistant",
        "message": {"content": [
            {"type": "text", "text": "picking now\n" + _BATCH_PICK_LINE + "\n[picked-difficulty: easy]"}]},
    }, rec)
    assert rec.get("emitted_batch_pick") is True


def test_handle_event_no_batch_pick_flag_when_absent():
    rec: dict = {}
    sc.handle_event(sc._Sink(None), {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "implementing without the block"}]},
    }, rec)
    assert "emitted_batch_pick" not in rec


def test_run_iteration_flags_missing_batch_pick_when_dev_commits():
    """A dev that shipped a commit but emitted no [batch-pick] block -> the iter
    manifest records a non-fatal batch_pick_missing violation; rc stays 0."""
    h = ClaudeCodeHarness()

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        return (0, {})  # committed (sha seq), no emitted_batch_pick, no picked_difficulty

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty", return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route", return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", side_effect=_sha_commit_seq()), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=False):
        rc, iter_manifest = run_iteration(h, ["sst-dev-cycle"], None, None, 1, 1, "/tmp")

    assert rc == 0, "a missing [batch-pick] is non-fatal -- the cycle's shipped work stands"
    assert "batch_pick_missing" in iter_manifest
    assert iter_manifest["batch_pick_missing"]["skill"] == "sst-dev-cycle"
    assert iter_manifest["batch_pick_missing"]["picked_difficulty_emitted"] is False


def test_run_iteration_no_batch_pick_flag_when_dev_emits_block():
    """A dev that emitted the [batch-pick] block -> no violation recorded."""
    h = ClaudeCodeHarness()

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        return (0, {"emitted_batch_pick": True, "picked_difficulty": "easy"})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty", return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route", return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", side_effect=_sha_commit_seq()), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=False):
        rc, iter_manifest = run_iteration(h, ["sst-dev-cycle"], None, None, 1, 1, "/tmp")

    assert "batch_pick_missing" not in iter_manifest


def test_run_iteration_no_batch_pick_flag_when_dev_makes_no_commit():
    """No commit (sha unchanged) -> the gate does not fire (it is commit-gated,
    so non-committing skills and incomplete cycles are excluded)."""
    h = ClaudeCodeHarness()

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty", return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route", return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=False):
        rc, iter_manifest = run_iteration(h, ["sst-dev-cycle"], None, None, 1, 1, "/tmp")

    assert "batch_pick_missing" not in iter_manifest


def test_run_iteration_no_batch_pick_flag_on_solo_tester():
    """A solo tester at i==0 must never trip the gate, even if sha advanced --
    the -tester name guard excludes it (testers do not emit [batch-pick])."""
    h = ClaudeCodeHarness()

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty", return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route", return_value=("sonnet", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", side_effect=_sha_commit_seq()), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=False):
        rc, iter_manifest = run_iteration(h, ["sst-tester"], None, None, 1, 1, "/tmp")

    assert "batch_pick_missing" not in iter_manifest


# ---- verdict-outcome classification (false-positive escalate-halt fix) -------
#
# _verdict_outcome drives the between-iteration halt: the runner halts iff it
# returns "escalate". It previously captured the `## Outcome` value with
# [A-Za-z_-]+, which silently failed on a digit-leading outcome ("1 edit" /
# "2 edits") and fell through to a whole-body \bescalate\b scan -- which
# false-positives on verdict prose that merely DISCUSSES escalation (e.g. a §7
# carve-out stating a MANIFEST flag does NOT escalate), halting a fine loop.

def _verdict_file(tmp_path, body):
    p = tmp_path / "supervisor_verdict.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_verdict_outcome_digit_leading_outcome_not_escalate(tmp_path):
    """Regression: a "1 edit" outcome whose body merely discusses escalation
    must NOT be classified as an escalate verdict (no false halt)."""
    body = ("# Supervisor verdict\n\n## Outcome\n\n1 edit\n\n"
            "Per the carve-out this MANIFEST flag does NOT escalate; the next "
            "supervisor should escalate only on concrete downstream harm.\n")
    assert sc._verdict_outcome(_verdict_file(tmp_path, body)) != "escalate"


def test_verdict_outcome_escalate_header_detected(tmp_path):
    body = "## Outcome\n\nescalate (0 edits)\n\ndetail about the blocker\n"
    assert sc._verdict_outcome(_verdict_file(tmp_path, body)) == "escalate"


def test_verdict_outcome_clean_header_not_escalate(tmp_path):
    body = "## Outcome\n\nclean -- deep walk ran, zero findings\n"
    out = sc._verdict_outcome(_verdict_file(tmp_path, body))
    assert out != "escalate" and out.startswith("clean")


def test_verdict_outcome_not_escalated_phrase_not_escalate(tmp_path):
    """An outcome line that ends with "Not escalated." must not classify as
    escalate (the word 'escalate' appears only mid-line, negated)."""
    body = "## Outcome\n\n2 findings -- 3 skill edits. Not escalated.\n"
    assert sc._verdict_outcome(_verdict_file(tmp_path, body)) != "escalate"


def test_verdict_outcome_inline_outcome_form_escalate(tmp_path):
    body = "**Outcome**: escalate -- recurring blocker\n\ndetail\n"
    assert sc._verdict_outcome(_verdict_file(tmp_path, body)) == "escalate"


def test_verdict_outcome_body_scan_fallback_when_no_header(tmp_path):
    """No structured Outcome line -> the last-resort whole-body scan still
    catches a genuine escalate verdict."""
    body = "# verdict\n\nThe supervisor decided to escalate this run.\n"
    assert sc._verdict_outcome(_verdict_file(tmp_path, body)) == "escalate"


def test_verdict_outcome_missing_file_is_unknown(tmp_path):
    assert sc._verdict_outcome(tmp_path / "nope.md") == "unknown"


# ---- sst-supervisor §7 outcome-line convention guard -------------------------
#
# The runner halts the loop iff _verdict_outcome returns "escalate".  It uses
# an anchored re.match so ONLY an outcome line that BEGINS with "escalate" is
# classified as an escalation.  A supervisor that writes "2 findings,
# escalating" (trailing suffix) or "triggered escalation" (non-leading word)
# silently under-halts the loop.  sst-supervisor §7 now documents the
# leading-word requirement; these tests guard against regressions.

def test_verdict_outcome_trailing_escalating_not_escalate(tmp_path):
    """Convention guard: an outcome line ending with 'escalating' must NOT
    classify as escalate.  Only a line that BEGINS with 'escalate' halts the
    loop; mid-line or trailing uses are not recognized by the anchored match."""
    body = "## Outcome\n\n2 findings, escalating\n\ndetail\n"
    assert sc._verdict_outcome(_verdict_file(tmp_path, body)) != "escalate"


def test_verdict_outcome_non_leading_escalate_word_not_escalate(tmp_path):
    """Convention guard: an outcome line like 'triggered escalation' (where
    'escalat*' is not the first word) must NOT classify as escalate."""
    body = "## Outcome\n\ntriggered escalation\n\ndetail\n"
    assert sc._verdict_outcome(_verdict_file(tmp_path, body)) != "escalate"


# ---- Phase 55: skill-failure graceful-resolution handoff -----------------------
#
# A mid-chain skill that exits non-zero (turn-limit exhaustion or a crash) must
# NO LONGER hard-abort the whole run. run_iteration flags the failure on the iter
# manifest, skips the remaining INTERMEDIATE skills, and hands off to the auto-
# supervisor for graceful resolution; rc stays 0 so main()'s loop continues
# (bounded by the SKILL_FAILURE_BACKSTOP consecutive-failure cap). Quota-
# exhaustion aborts (rate_limit/overload) remain HARD stops.


def test_classify_skill_failure_turn_limit():
    """error_max_turns result subtype classifies as turn_limit_exhausted."""
    assert sc._classify_skill_failure(
        {"result_subtype": "error_max_turns", "num_turns": 251}
    ) == "turn_limit_exhausted"


def test_classify_skill_failure_generic():
    """Any other non-zero exit classifies as a generic error."""
    assert sc._classify_skill_failure({"result_subtype": "error_during_execution"}) == "error"
    assert sc._classify_skill_failure({}) == "error"


def test_run_iteration_skill_failure_hands_off_to_supervisor():
    """A dev turn-limit failure flags + skips intermediates + runs the supervisor.

    dev (i=0) returns rc=1 with result_subtype=error_max_turns; the intermediate
    tester + review are skipped; the auto-supervisor IS invoked for graceful
    resolution; rc stays 0 (run NOT aborted); skill_failure is recorded.
    """
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        if skill_name == "sst-dev-cycle":
            return (1, {"result_subtype": "error_max_turns", "num_turns": 251})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("opus", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-tester", "sst-dev-review", "sst-supervisor"],
            None,
            "sst-supervisor",
            1,
            1,
            "/tmp",
        )

    assert rc == 0, "a flagged skill failure must NOT abort the chain (rc=0)"
    assert "skill_failure" in iter_manifest, "skill_failure must be recorded"
    assert iter_manifest["skill_failure"]["skill"] == "sst-dev-cycle"
    assert iter_manifest["skill_failure"]["failure_kind"] == "turn_limit_exhausted"
    assert iter_manifest["skill_failure"]["exit_code"] == 1
    assert calls == ["sst-dev-cycle", "sst-supervisor"], \
        "intermediate tester+review skipped; supervisor handles resolution"


def test_run_iteration_skill_failure_no_supervisor_flags_without_abort():
    """A dev failure with no auto-supervisor flags + ends the iter, rc still 0.

    Without a supervisor to hand off to, run_iteration still flags the failure
    and does NOT propagate a non-zero rc (the loop continues; the backstop in
    main() bounds repeats). The following review skill is NOT run against the
    failed skill's half-done state.
    """
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        if skill_name == "sst-dev-cycle":
            return (1, {"result_subtype": "error_max_turns", "num_turns": 251})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("opus", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-dev-review"],
            None,
            None,   # no auto_supervisor
            1,
            1,
            "/tmp",
        )

    assert rc == 0, "flagged failure with no supervisor still keeps rc=0"
    assert iter_manifest["skill_failure"]["skill"] == "sst-dev-cycle"
    assert calls == ["sst-dev-cycle"], \
        "review must NOT run against the failed skill's half-done state"


def test_run_iteration_rate_limit_abort_still_hard_aborts():
    """Quota-exhaustion (rate_limit_aborted) remains a HARD abort, not a flag.

    A non-zero exit carrying rate_limit_aborted must take the old hard-abort
    path: rc != 0, NO skill_failure flag, no supervisor handoff.
    """
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        if skill_name == "sst-dev-cycle":
            return (1, {"rate_limit_aborted": "max_pauses_reached"})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("opus", "high", _ROUTE_RECORD)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-tester", "sst-supervisor"],
            None,
            "sst-supervisor",
            1,
            1,
            "/tmp",
        )

    assert rc == 1, "rate-limit exhaustion must hard-abort (rc != 0)"
    assert "skill_failure" not in iter_manifest, \
        "quota-exhaustion abort must NOT be flagged as a recoverable skill_failure"
    assert calls == ["sst-dev-cycle"], "no handoff after a quota-exhaustion abort"


# ---- Phase 56: model-unavailable graceful fallback --------------------------

_next_lower_tier = sc._next_lower_tier
MODEL_UNAVAILABLE_TEXT_RE = sc.MODEL_UNAVAILABLE_TEXT_RE


def test_next_lower_tier_steps_down_one_rung():
    assert _next_lower_tier("fable", sc.MODEL_TIERS) == "opus"
    assert _next_lower_tier("opus", sc.MODEL_TIERS) == "sonnet"
    assert _next_lower_tier("sonnet", sc.MODEL_TIERS) == "haiku"


def test_next_lower_tier_none_at_bottom_or_unknown():
    assert _next_lower_tier("haiku", sc.MODEL_TIERS) is None
    assert _next_lower_tier("bogus", sc.MODEL_TIERS) is None


def test_model_unavailable_regex_matches_real_error_phrasings():
    positives = [
        'API Error: 404 {"type":"not_found_error","message":"model: claude-fable-5 not found"}',
        "invalid model: claude-fable-5",
        "the requested model is not available for this account",
        "unknown model claude-fable-5",
        "your organization does not have access to model claude-fable-5",
        "model claude-fable-5 does not exist",
    ]
    for line in positives:
        assert MODEL_UNAVAILABLE_TEXT_RE.search(line), f"should match: {line!r}"


def test_model_unavailable_regex_ignores_transient_and_normal_lines():
    negatives = [
        "API Error: 529 overloaded",
        "API Error: 503 Service Unavailable",   # 'unavailable' but no 'model' token
        "rate limit reached; resets at 2026-07-04T00:00:00Z",
        "Model usage: 12000 input tokens",      # 'model' but no unavailability phrase
        "[TEST] model rendered fine",
    ]
    for line in negatives:
        assert not MODEL_UNAVAILABLE_TEXT_RE.search(line), f"should NOT match: {line!r}"


def _fake_run_skill_by_model(call_kwargs_list, outcomes, default=(0, {})):
    """Fake run_skill that returns a canned (rc, record) keyed on the model kwarg."""
    def fake(_harness, _skill_name, _index, _log_dir, **kwargs):
        call_kwargs_list.append(kwargs.copy())
        return outcomes.get(kwargs.get("model"), default)
    return fake


def test_model_fallback_steps_down_to_available_tier():
    """fable unavailable -> retry on opus (fresh session), succeed, record the fallback."""
    h = ClaudeCodeHarness()
    call_kwargs: list = []
    outcomes = {
        "fable": (1, {"model_unavailable_signal": {"source": "text_fallback"},
                      "session_id": "sess_fable"}),
        "opus":  (0, {}),
    }
    fake = _fake_run_skill_by_model(call_kwargs, outcomes)

    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch("time.sleep"):
        rc, record = run_skill_with_retry(
            h, "ssp-cm-supervisor", 0, None,
            on_rate_limit="pause", max_pause_seconds=3600, max_pauses=3,
            pause_records=[], model="fable", effort="xhigh",
        )

    assert rc == 0
    assert len(call_kwargs) == 2
    assert call_kwargs[0]["model"] == "fable"
    assert call_kwargs[1]["model"] == "opus", "must step DOWN one tier on unavailability"
    assert call_kwargs[1]["resume_session_id"] is None, "model swap must start a fresh session"
    assert record.get("model_fallbacks"), "the successful record must carry the fallback trail"
    assert record["model_fallbacks"][0]["from"] == "fable"
    assert record["model_fallbacks"][0]["to"] == "opus"
    assert record.get("effective_model_after_fallback") == "opus"


def test_model_fallback_cascades_multiple_tiers():
    """fable + opus both unavailable -> lands on sonnet."""
    h = ClaudeCodeHarness()
    call_kwargs: list = []
    outcomes = {
        "fable":  (1, {"model_unavailable_signal": {"source": "result_frame"}}),
        "opus":   (1, {"model_unavailable_signal": {"source": "result_frame"}}),
        "sonnet": (0, {}),
    }
    fake = _fake_run_skill_by_model(call_kwargs, outcomes)

    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch("time.sleep"):
        rc, record = run_skill_with_retry(
            h, "ssp-cm-manager", 0, None,
            on_rate_limit="pause", max_pause_seconds=3600, max_pauses=3,
            pause_records=[], model="fable",
        )

    assert rc == 0
    assert [k["model"] for k in call_kwargs] == ["fable", "opus", "sonnet"]
    assert [f["to"] for f in record["model_fallbacks"]] == ["opus", "sonnet"]


def test_model_fallback_aborts_at_lowest_tier():
    """Unavailable at the lowest tier -> give up, flag model_fallback_aborted."""
    h = ClaudeCodeHarness()
    call_kwargs: list = []
    outcomes = {"haiku": (1, {"model_unavailable_signal": {"source": "text_fallback"}})}
    fake = _fake_run_skill_by_model(call_kwargs, outcomes)

    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch("time.sleep"):
        rc, record = run_skill_with_retry(
            h, "sst-translator", 0, None,
            on_rate_limit="pause", max_pause_seconds=3600, max_pauses=3,
            pause_records=[], model="haiku",
        )

    assert rc == 1
    assert len(call_kwargs) == 1, "no lower tier to try, so exactly one attempt"
    assert record.get("model_fallback_aborted") == "no_lower_tier"


def test_model_fallback_not_triggered_when_overload_signal_present():
    """A transient overload alongside a model signal retries the SAME model, no downgrade."""
    h = ClaudeCodeHarness()
    call_kwargs: list = []
    outcomes = {
        # First fable attempt: overload wins (transient) -> retry fable, then succeed.
        "fable": (1, {"overload_signal": {"status": 529, "source": "result_frame"},
                      "model_unavailable_signal": {"source": "text_fallback"},
                      "session_id": "sess_x"}),
    }
    # After the overload retry, return success for fable on the 2nd call.
    calls = {"n": 0}

    def fake(_h, _s, _i, _l, **kwargs):
        call_kwargs.append(kwargs.copy())
        calls["n"] += 1
        if calls["n"] == 1:
            return outcomes["fable"]
        return (0, {})

    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch("time.sleep"):
        rc, record = run_skill_with_retry(
            h, "ssp-cm-supervisor", 0, None,
            on_rate_limit="pause", max_pause_seconds=3600, max_pauses=3,
            pause_records=[], overload_retry_records=[], model="fable",
        )

    assert rc == 0
    assert [k["model"] for k in call_kwargs] == ["fable", "fable"], \
        "overload retries the same model; it must NOT downgrade the tier"
    assert not record.get("model_fallbacks")


# ---- Phase 57: Fable-off-by-default ceiling + rate-limit model downgrade -----

_apply_model_ceiling = sc._apply_model_ceiling
MODEL_SWITCHABLE_RATE_LIMIT_RE = sc.MODEL_SWITCHABLE_RATE_LIMIT_RE


def _reset_tier_globals(ceiling):
    sc._RUNTIME_MODEL_CEILING = ceiling
    sc._RATE_LIMITED_TIERS.clear()


def test_model_ceiling_disables_fable_by_default():
    _reset_tier_globals("opus")   # the module default
    assert _apply_model_ceiling("fable") == "opus"
    assert _apply_model_ceiling("opus") == "opus"
    assert _apply_model_ceiling("sonnet") == "sonnet"


def test_model_ceiling_none_allows_fable():
    _reset_tier_globals(None)
    assert _apply_model_ceiling("fable") == "fable"


def test_rate_limited_tier_is_capped_below():
    _reset_tier_globals(None)
    sc._RATE_LIMITED_TIERS.add("fable")
    assert _apply_model_ceiling("fable") == "opus"      # capped below the RL'd tier
    sc._RATE_LIMITED_TIERS.add("opus")
    assert _apply_model_ceiling("fable") == "sonnet"
    _reset_tier_globals("opus")


def test_switchable_rate_limit_regex():
    for t in ["seven_day_overage_included", "seven_day", "weekly_limit",
              "monthly spend limit", "You've hit your monthly spend limit"]:
        assert MODEL_SWITCHABLE_RATE_LIMIT_RE.search(t), t
    for t in ["five_hour", "5h rolling window", "opus_five_hour"]:
        assert not MODEL_SWITCHABLE_RATE_LIMIT_RE.search(t), t


def test_switchable_rate_limit_downgrades_instead_of_sleeping():
    """A seven_day_overage rejection drops one tier and retries -- no sleep."""
    _reset_tier_globals(None)
    h = ClaudeCodeHarness()
    call_kwargs: list = []
    outcomes = {
        "fable": (1, {"rate_limit_signal": {"type": "seven_day_overage_included",
                                            "status": "rejected"}}),
        "opus":  (0, {}),
    }
    fake = _fake_run_skill_by_model(call_kwargs, outcomes)
    sleep_calls: list = []
    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch.object(sc.time, "sleep", side_effect=sleep_calls.append):
        rc, record = run_skill_with_retry(
            h, "ssp-cm-dev", 0, None,
            on_rate_limit="pause", max_pause_seconds=28800, max_pauses=3,
            pause_records=[], model="fable",
        )
    assert rc == 0
    assert [k["model"] for k in call_kwargs] == ["fable", "opus"]
    assert not sleep_calls, "switchable rate limit must NOT sleep; it downgrades"
    assert record["model_fallbacks"][0]["to"] == "opus"
    assert record["model_fallbacks"][0]["reason"].startswith("rate_limit:")
    assert "fable" in sc._RATE_LIMITED_TIERS, "exhausted tier is stuck for the run"
    _reset_tier_globals("opus")


def test_five_hour_rate_limit_still_sleeps_no_downgrade():
    """A shared five_hour limit is NOT model-switchable: sleep + retry same model."""
    _reset_tier_globals(None)
    h = ClaudeCodeHarness()
    call_kwargs: list = []
    calls = {"n": 0}

    def fake(_h, _s, _i, _l, **kwargs):
        call_kwargs.append(kwargs.copy())
        calls["n"] += 1
        if calls["n"] == 1:
            return (1, {"rate_limit_signal": {"type": "five_hour", "status": "exceeded"}})
        return (0, {})

    sleep_calls: list = []
    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch.object(sc.time, "sleep", side_effect=sleep_calls.append):
        rc, record = run_skill_with_retry(
            h, "ssp-cm-dev", 0, None,
            on_rate_limit="pause", max_pause_seconds=28800, max_pauses=3,
            pause_records=[], model="fable",
        )
    assert rc == 0
    assert [k["model"] for k in call_kwargs] == ["fable", "fable"], \
        "five_hour must retry the SAME model, not downgrade"
    assert sleep_calls, "five_hour must sleep until reset"
    assert not record.get("model_fallbacks")
    assert "fable" not in sc._RATE_LIMITED_TIERS
    _reset_tier_globals("opus")
