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
