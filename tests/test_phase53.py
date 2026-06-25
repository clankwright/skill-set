"""Tests for Phase 53: manager/bot must never silently deadlock a command.

53.1 — `skills/framework/sst-manager/SKILL.md` must carry an "always reply,
       never defer the ask" hard rule mandating that every --process-feedback /
       --process-command run terminates with exactly ONE outbound Telegram
       message -- either the outcome/result OR a decision-request sent BEFORE
       the run ends (never deferred to "once you answer"). The queue file stays
       in place (unprocessed) when a decision-request is pending. The rule must
       mirror the sst-executor tier-2 "ask = send the approval-request now,
       then exit" pattern. sst-manager version must be bumped. The SSP sync
       checker must report ssp-manager as in sync.

53.2 — `bin/manager-bot.py` must add a deadlock-signature WARNING: when a
       spawned --process-command / --process-feedback exits 0 but the queue
       file is still in the MAIN queue dir (not moved to processed/), log a
       WARNING. Must NOT false-positive when the file was correctly drained.
"""
import importlib.util
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

_REPO = Path(__file__).parent.parent
_SST_MANAGER = _REPO / "skills/framework/sst-manager/SKILL.md"
_SSP_MANAGER = _REPO / ".claude/skills/ssp-manager/SKILL.md"

# Load manager-bot so we can test _watch_spawn_for_deadlock directly.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token_for_unit_tests")
os.environ.setdefault("TELEGRAM_CHAT_ID", "99999")
_BOT_PATH = _REPO / "bin" / "manager-bot.py"
_spec = importlib.util.spec_from_file_location("manager_bot_53", _BOT_PATH)
_mb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mb)


def _manager_text() -> str:
    assert _SST_MANAGER.exists(), f"{_SST_MANAGER} must exist"
    return _SST_MANAGER.read_text()


def _ssp_manager_text() -> str:
    assert _SSP_MANAGER.exists(), f"{_SSP_MANAGER} must exist"
    return _SSP_MANAGER.read_text()


# ---------------------------------------------------------------------------
# 53.1 -- sst-manager SKILL.md: always-reply / never-defer hard rule
# ---------------------------------------------------------------------------

def test_sst_manager_single_terminal_outbound_message_mandate():
    """sst-manager SKILL.md must mandate that every --process-feedback /
    --process-command run sends exactly one outbound Telegram message before
    ending -- no silent exits."""
    text = _manager_text()
    assert re.search(
        r"(?i)"
        r"exactly\s+one\s+outbound\s+(Telegram\s+)?message"
        r"|must\s+terminate\s+by\s+sending\s+exactly\s+one"
        r"|send\s+exactly\s+one\s+outbound"
        r"|one\s+outbound\s+Telegram\s+message",
        text,
    ), (
        "sst-manager SKILL.md must mandate that every --process-feedback / "
        "--process-command run ends by sending exactly one outbound Telegram message"
    )


def test_sst_manager_send_ask_before_ending_rule():
    """sst-manager SKILL.md must state that a decision-request MUST be sent
    BEFORE the run ends -- never deferred to 'once you answer'."""
    text = _manager_text()
    assert re.search(
        r"(?i)"
        r"sent?\s+BEFORE\s+the\s+run\s+ends?"
        r"|send.+before.+end"
        r"|BEFORE.+ending|before.+exit|never.+defer",
        text,
    ), (
        "sst-manager SKILL.md must state that a decision-request MUST be sent "
        "BEFORE the run ends, never deferred"
    )


def test_sst_manager_never_defer_language():
    """sst-manager SKILL.md must use 'never defer' / 'never deferred' or
    equivalent language for the 'park-and-wait' anti-pattern."""
    text = _manager_text()
    assert re.search(
        r"(?i)never.+defer|defer.+never|never\s+park|never\s+silent",
        text,
    ), (
        "sst-manager SKILL.md must explicitly forbid 'deferring' a decision-request "
        "to after the user answers -- the ask must be sent BEFORE ending"
    )


def test_sst_manager_queue_file_stays_for_decision_reply():
    """sst-manager SKILL.md must state that the queue file stays in place
    (unprocessed) when a decision-request is pending, so the human's reply
    can resume the command."""
    text = _manager_text()
    assert re.search(
        r"(?i)"
        r"queue\s+file\s+stays|leave.+queue.+file|queue.+file.+pending"
        r"|file\s+stays\s+in\s+place|queue\s+file.+unprocesed|queue\s+file.+unprocessed",
        text,
    ), (
        "sst-manager SKILL.md must state that the queue file stays in place "
        "(unprocessed) when a decision-request is pending, for the reply to resume it"
    )


def test_sst_manager_mirrors_executor_tier2():
    """sst-manager SKILL.md must reference sst-executor tier-2 as the model
    for 'ask = send the approval-request now, then exit'."""
    text = _manager_text()
    assert re.search(
        r"(?i)executor.+tier.?2|tier.?2.+executor|sst-executor.+tier",
        text,
    ), (
        "sst-manager SKILL.md must reference sst-executor tier-2 as the pattern "
        "for sending a decision-request immediately before exiting"
    )


def test_sst_manager_ending_run_without_reply_is_violation():
    """sst-manager SKILL.md must name a silent exit (neither acted nor asked)
    as a contract violation."""
    text = _manager_text()
    assert re.search(
        r"(?i)"
        r"contract\s+violation"
        r"|neither\s+acted\s+nor\s+asked"
        r"|ending\s+.+having\s+neither"
        r"|never\s+ended\s+without\s+(sending|a\s+message)",
        text,
    ), (
        "sst-manager SKILL.md must name a silent exit (ending without acting or asking) "
        "as a contract violation"
    )


def test_sst_manager_hard_rules_section_contains_always_reply():
    """The always-reply rule must appear in or near the Hard rules section
    of sst-manager SKILL.md (not buried in a prose paragraph)."""
    text = _manager_text()
    # Find Hard rules section and check if it contains the always-reply language
    # (Allow it to be in the on-demand feedback/command sections too, since
    # those are the actionable entry points; what matters is the rule is findable.)
    hard_rules_idx = text.find("## Hard rules")
    on_demand_idx = text.find("## On-demand feedback routing")
    assert hard_rules_idx != -1 or on_demand_idx != -1, (
        "sst-manager SKILL.md must have a Hard rules section or On-demand sections "
        "where the always-reply rule can live"
    )
    # The always-reply mandate must appear in the text at all.
    assert re.search(
        r"(?i)always\s+repl|never.+silent|every.+run.+must.+send|"
        r"must\s+terminate\s+by\s+sending",
        text,
    ), "sst-manager SKILL.md must contain an 'always reply' or 'must send' mandate"


def test_sst_manager_version_bumped_to_at_least_2_3_0():
    """sst-manager must be bumped to >= v2.3.0 to record the Phase 53 hard rule."""
    text = _manager_text()
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "sst-manager SKILL.md must carry a 'version:' field"
    major, minor, patch_ = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch_) >= (2, 3, 0), (
        f"sst-manager version is {major}.{minor}.{patch_}; "
        "must be >= 2.3.0 to record the Phase 53 always-reply hard rule"
    )


def test_validate_frontmatter_sst_manager():
    """bin/validate-frontmatter.py must exit 0 on sst-manager after Phase 53 changes."""
    result = subprocess.run(
        [sys.executable, str(_REPO / "bin" / "validate-frontmatter.py"), str(_SST_MANAGER)],
        capture_output=True, text=True, cwd=str(_REPO),
    )
    assert result.returncode == 0, (
        f"validate-frontmatter.py failed on sst-manager:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# 53.1 -- ssp-manager sync: base-version must be present and in sync
# ---------------------------------------------------------------------------

def test_ssp_manager_has_base_version():
    """ssp-manager/SKILL.md must carry a base-version: field to track
    which sst-manager contract it was last reconciled against."""
    text = _ssp_manager_text()
    m = re.search(r"^base-version:\s*(\d+\.\d+\.\d+)", text, re.MULTILINE)
    assert m, (
        "ssp-manager/SKILL.md must carry a 'base-version:' field "
        "(e.g. base-version: 2.3.0) to track reconciliation with sst-manager"
    )


def test_ssp_manager_sync_checker_reports_in_sync():
    """check-ssp-sync.py must report ssp-manager as 'in sync' after Phase 53
    sync (base-version pinned to the bumped sst-manager version)."""
    ssp_skills_dir = str(_SSP_MANAGER.parent.parent)
    result = subprocess.run(
        [sys.executable, str(_REPO / "bin" / "check-ssp-sync.py"),
         "--skills-dir", ssp_skills_dir],
        capture_output=True, text=True, cwd=str(_REPO),
    )
    stdout = result.stdout
    # Should report in sync for ssp-manager (either "ALL in sync" or the
    # specific "in sync: ssp-manager" line).
    assert re.search(r"(?i)(in sync.*ssp-manager|ALL\s+in\s+sync|ssp-manager.*in sync)", stdout) or \
           (result.returncode == 0 and "ssp-manager" not in stdout), (
        f"check-ssp-sync.py must report ssp-manager as in sync:\n{stdout}"
    )


# ---------------------------------------------------------------------------
# 53.2 -- manager-bot.py: deadlock-signature WARNING
# ---------------------------------------------------------------------------

def test_watch_spawn_for_deadlock_function_exists():
    """manager-bot.py must expose a _watch_spawn_for_deadlock function."""
    assert hasattr(_mb, "_watch_spawn_for_deadlock"), (
        "manager-bot.py must define _watch_spawn_for_deadlock(proc, queue_file, label) "
        "for the deadlock-signature warning (Phase 53.2)"
    )


def test_deadlock_warning_fires_when_exit0_and_file_remains(tmp_path, caplog):
    """_watch_spawn_for_deadlock must log a WARNING when the spawned process
    exits 0 but the queue file is still in the main queue dir (deadlock signature)."""
    queue_file = tmp_path / "2026-06-25T12-00-00Z_feedback.json"
    queue_file.write_text('{"command": "feedback", "body": "test"}')

    mock_proc = MagicMock()
    mock_proc.wait.return_value = None
    mock_proc.returncode = 0

    with caplog.at_level(logging.WARNING, logger="manager-bot"):
        _mb._watch_spawn_for_deadlock(mock_proc, queue_file, "test-manager")

    warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert any(
        re.search(r"(?i)deadlock", msg) for msg in warning_msgs
    ), (
        f"_watch_spawn_for_deadlock must log a WARNING containing 'deadlock' when "
        f"proc exits 0 and the queue file was not moved to processed/.\n"
        f"Warnings seen: {warning_msgs}"
    )


def test_deadlock_no_false_positive_when_file_drained(tmp_path, caplog):
    """_watch_spawn_for_deadlock must NOT warn when the queue file was correctly
    moved to the processed/ subdirectory (normal successful processing)."""
    queue_file = tmp_path / "2026-06-25T12-00-00Z_feedback.json"
    # Simulate the manager moving the file to processed/ before exit.
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    processed_file = processed_dir / queue_file.name
    processed_file.write_text('{"command": "feedback", "body": "test"}')
    # queue_file itself does NOT exist (was moved, not copied).

    mock_proc = MagicMock()
    mock_proc.wait.return_value = None
    mock_proc.returncode = 0

    with caplog.at_level(logging.WARNING, logger="manager-bot"):
        _mb._watch_spawn_for_deadlock(mock_proc, queue_file, "test-manager")

    warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert not any(
        re.search(r"(?i)deadlock", msg) for msg in warning_msgs
    ), (
        f"_watch_spawn_for_deadlock must NOT warn when the queue file was drained "
        f"(moved to processed/). False positive warning(s): {warning_msgs}"
    )


def test_deadlock_no_false_positive_on_nonzero_exit(tmp_path, caplog):
    """_watch_spawn_for_deadlock must NOT warn when the spawned process exits
    non-zero (ordinary failure; the loop already aborts on non-zero)."""
    queue_file = tmp_path / "2026-06-25T12-00-00Z_command.json"
    queue_file.write_text('{"command": "status", "args": ["cm"]}')

    mock_proc = MagicMock()
    mock_proc.wait.return_value = None
    mock_proc.returncode = 1  # non-zero exit

    with caplog.at_level(logging.WARNING, logger="manager-bot"):
        _mb._watch_spawn_for_deadlock(mock_proc, queue_file, "test-manager")

    warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert not any(
        re.search(r"(?i)deadlock", msg) for msg in warning_msgs
    ), (
        f"_watch_spawn_for_deadlock must NOT warn on a non-zero exit. "
        f"False positive warning(s): {warning_msgs}"
    )


def test_deadlock_no_false_positive_when_file_gone_entirely(tmp_path, caplog):
    """_watch_spawn_for_deadlock must NOT warn when the queue file is simply
    gone from the main dir (could have been moved elsewhere or deleted; the
    absence of the file in the main dir means it was processed)."""
    queue_file = tmp_path / "2026-06-25T12-00-00Z_feedback.json"
    # File does not exist at all -- was handled and deleted.

    mock_proc = MagicMock()
    mock_proc.wait.return_value = None
    mock_proc.returncode = 0

    with caplog.at_level(logging.WARNING, logger="manager-bot"):
        _mb._watch_spawn_for_deadlock(mock_proc, queue_file, "test-manager")

    warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert not any(
        re.search(r"(?i)deadlock", msg) for msg in warning_msgs
    ), (
        f"_watch_spawn_for_deadlock must NOT warn when the queue file is gone "
        f"(was handled -- no deadlock). False positive: {warning_msgs}"
    )


def test_spawn_manager_starts_deadlock_watcher(tmp_path, monkeypatch):
    """spawn_manager_for_command must start the deadlock-watcher thread after
    a successful Popen so that silent exits are detected at runtime."""
    import threading

    watcher_calls = []

    def fake_watcher(proc, queue_file, label):
        watcher_calls.append((proc, queue_file, label))

    monkeypatch.setattr(_mb, "MANAGER_SKILL_NAME", "sst-manager")
    monkeypatch.setattr(_mb, "CLAUDE_BIN", "echo")
    monkeypatch.setattr(_mb, "ON_DEMAND_LOG_DIR", tmp_path)
    monkeypatch.setattr(_mb, "_watch_spawn_for_deadlock", fake_watcher)

    queue_file = tmp_path / "2026-06-25T12-00-00Z_feedback.json"
    queue_file.write_text('{"command": "feedback"}')

    threads_before = threading.active_count()
    result = _mb.spawn_manager_for_command("cm", str(tmp_path), queue_file)

    # Allow thread to start (it's daemon so no join needed; watcher is mocked instant).
    import time; time.sleep(0.05)

    assert result is True, "spawn_manager_for_command should return True on success"
    assert len(watcher_calls) == 1, (
        f"spawn_manager_for_command must start one deadlock-watcher per spawn; "
        f"watcher_calls={watcher_calls}"
    )
    assert watcher_calls[0][1] == queue_file, (
        "deadlock-watcher must receive the exact queue_file path"
    )
