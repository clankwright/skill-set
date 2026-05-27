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


def test_run_iteration_contract_violation_incomplete_cycle():
    """Phase 36: dev exits [ok] with no commit and In-flight set → contract_violation.

    Patches:
    - run_skill_with_retry: dev returns rc=0 with no sentinel; review never called
    - _git_sha: always returns the same sha (no commit)
    - _incomplete_cycle_detected: returns True (simulates dirty TODO.md)
    Asserts:
    - iter_manifest["contract_violation"]["kind"] == "incomplete-cycle"
    - sst-dev-review is NOT invoked
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
            ["sst-dev-cycle", "sst-dev-review"],
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
        "sst-dev-review must NOT be called after contract_violation bail"


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
