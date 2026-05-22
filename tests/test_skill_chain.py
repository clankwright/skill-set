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
