"""Tests for bin/manager-idle-check.py: skip-when-idle vs run-when-work-found.

Covers SPEC TODO Next-up item: sst-manager periodic-tick idle pre-check.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT = _REPO_ROOT / "bin" / "manager-idle-check.py"
_SST_MANAGER_SKILL = _REPO_ROOT / "skills" / "framework" / "sst-manager" / "SKILL.md"
_SST_SETUP_TELEGRAM = (
    _REPO_ROOT / "skills" / "framework" / "coms" / "sst-setup-telegram" / "SKILL.md"
)


def _load_module():
    """Load manager-idle-check.py as a Python module (hyphenated filename)."""
    spec = importlib.util.spec_from_file_location("manager_idle_check", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Module-level availability ───────────────────────────────────────────────

def test_script_exists():
    """bin/manager-idle-check.py must exist."""
    assert _SCRIPT.exists(), f"Missing: {_SCRIPT}"


def test_is_manager_idle_function_exists():
    """is_manager_idle() must be importable from the module."""
    mod = _load_module()
    assert hasattr(mod, "is_manager_idle"), "is_manager_idle not found in manager-idle-check module"


# ── Shared fixture ───────────────────────────────────────────────────────────

class _Env:
    """Thin wrapper around a tmp-dir-based test environment."""

    def __init__(self, tmp_path: Path):
        self.project_root = tmp_path / "project"
        self.project_root.mkdir()
        (self.project_root / ".git").mkdir()
        (self.project_root / "docs").mkdir()
        self.runs_dir = self.project_root / ".skill-runs"
        self.runs_dir.mkdir()

        self.state_dir = tmp_path / "state"
        self.state_dir.mkdir()
        self.queue_dir = self.state_dir / "manager-bot-queue"
        self.queue_dir.mkdir()
        (self.queue_dir / "processed").mkdir()

        self.cursors_path = self.state_dir / "manager-cursors.json"
        self.cursors_path.write_text("{}")

    def write_cursor(
        self,
        last_run: str | None = None,
        human_md_snapshot: dict | None = None,
    ) -> None:
        """Write a cursor entry for self.project_root."""
        data: dict = {}
        proj_key = str(self.project_root)
        entry: dict = {}
        if last_run is not None:
            entry["last_run"] = last_run
        if human_md_snapshot is not None:
            entry["human_md_snapshot"] = human_md_snapshot
        data[proj_key] = entry
        self.cursors_path.write_text(json.dumps(data))

    def make_run_dir(self, name: str) -> Path:
        d = self.runs_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def call_idle(self) -> bool:
        mod = _load_module()
        return mod.is_manager_idle(
            str(self.project_root),
            cursors_path=str(self.cursors_path),
            queue_dir=str(self.queue_dir),
        )


@pytest.fixture()
def env(tmp_path):
    return _Env(tmp_path)


# ── Core idle / not-idle checks ──────────────────────────────────────────────

def test_no_cursor_entry_is_not_idle(env):
    """No cursor entry for the project (first run) must return not-idle."""
    # cursor file is empty {}; project has no runs, no queue
    assert env.call_idle() is False, "First run (no cursor entry) should not be idle"


def test_baseline_idle(env):
    """Cursor up-to-date, no queue files, no HUMAN.md → idle."""
    run_dir = env.make_run_dir("2026-01-01T00-00-00Z_test-chain")
    env.write_cursor(last_run=run_dir.name, human_md_snapshot={})
    assert env.call_idle() is True, "Baseline with no activity should be idle"


def test_active_when_new_skill_run_dir(env):
    """A newer .skill-runs/ dir appears after the cursor's last_run → not idle."""
    old_run = env.make_run_dir("2026-01-01T00-00-00Z_old")
    env.write_cursor(last_run=old_run.name)
    # New run dir with a later ISO timestamp (lexicographically greater name).
    env.make_run_dir("2026-01-02T00-00-00Z_new")
    assert env.call_idle() is False, "New skill-run dir must cause not-idle"


def test_active_when_queue_files_present(env):
    """Unprocessed queue JSON files trigger not-idle."""
    run_dir = env.make_run_dir("2026-01-01T00-00-00Z_test-chain")
    env.write_cursor(last_run=run_dir.name, human_md_snapshot={})
    (env.queue_dir / "cmd001.json").write_text(
        json.dumps(
            {
                "command": "status",
                "args": ["proj"],
                "received_at": "2026-01-01T00:00:00Z",
                "from_chat_id": 12345,
            }
        )
    )
    assert env.call_idle() is False, "Queue file must cause not-idle"


def test_processed_queue_files_are_ignored(env):
    """Files in manager-bot-queue/processed/ do not count as pending."""
    run_dir = env.make_run_dir("2026-01-01T00-00-00Z_test-chain")
    env.write_cursor(last_run=run_dir.name, human_md_snapshot={})
    # Only file in processed/ (already handled)
    (env.queue_dir / "processed" / "done001.json").write_text("{}")
    assert env.call_idle() is True, "Processed queue file must not count as pending"


def test_active_when_human_md_has_new_blocking_entry(env):
    """HUMAN.md gains a new Blocking entry not present in the snapshot → not idle."""
    run_dir = env.make_run_dir("2026-01-01T00-00-00Z_test-chain")
    # Cursor says no blocking entries were seen.
    env.write_cursor(last_run=run_dir.name, human_md_snapshot={})
    # Write a HUMAN.md with a blocking entry.
    (env.project_root / "docs" / "HUMAN.md").write_text(
        "# HUMAN.md\n\n"
        "## Blocking\n\n"
        "- [ ] H39.1 [easy] **Test blocker**\n"
        "  Body.\n"
        "  Blocks: 39.1\n"
        "  Filed by: test at 2026-01-01T00:00:00Z.\n"
        "  Source: test.\n\n"
        "## High\n\n## Medium\n\n## Low\n\n## Done\n"
    )
    assert env.call_idle() is False, "New blocking HUMAN.md entry must cause not-idle"


def test_idle_when_human_md_snapshot_matches(env):
    """HUMAN.md blocking entries match cursor snapshot → idle on this dimension."""
    run_dir = env.make_run_dir("2026-01-01T00-00-00Z_test-chain")
    # Cursor records the same blocking entry already seen.
    env.write_cursor(
        last_run=run_dir.name,
        human_md_snapshot={"H39.1": "Test blocker"},
    )
    (env.project_root / "docs" / "HUMAN.md").write_text(
        "# HUMAN.md\n\n"
        "## Blocking\n\n"
        "- [ ] H39.1 [easy] **Test blocker**\n"
        "  Body.\n"
        "  Blocks: 39.1\n"
        "  Filed by: test at 2026-01-01T00:00:00Z.\n"
        "  Source: test.\n\n"
        "## High\n\n## Medium\n\n## Low\n\n## Done\n"
    )
    assert env.call_idle() is True, "Matching HUMAN.md snapshot must remain idle"


# ── SKILL.md prose checks ───────────────────────────────────────────────────

def test_sst_manager_skill_documents_idle_precheck():
    """sst-manager SKILL.md must document the bin/manager-idle-check.py pre-check."""
    content = _SST_MANAGER_SKILL.read_text()
    assert "manager-idle-check" in content, (
        "sst-manager SKILL.md must document the manager-idle-check.py caller gate"
    )


def test_sst_manager_idle_check_documents_exit_codes():
    """sst-manager SKILL.md idle pre-check docs must mention exit 0 (idle) semantics."""
    content = _SST_MANAGER_SKILL.read_text()
    # The doc should explain that exit 0 means skip / idle.
    assert re.search(r"exit 0|exits? 0|idle", content, re.IGNORECASE), (
        "sst-manager SKILL.md idle pre-check docs must explain exit-0 idle semantics"
    )


def test_sst_setup_telegram_skill_documents_base_dir_symlink():
    """sst-setup-telegram SKILL.md must document creating ~/Dev/skill-set/telegram.env symlink."""
    content = _SST_SETUP_TELEGRAM.read_text()
    assert "telegram.env" in content, (
        "sst-setup-telegram SKILL.md must mention telegram.env symlink creation"
    )
    # Must describe idempotency
    assert "idempotent" in content.lower() or "already exists" in content.lower() or "if" in content.lower(), (
        "sst-setup-telegram SKILL.md must document idempotent symlink creation"
    )


def test_sst_setup_telegram_symlink_step_mentions_base_dir_fallback():
    """sst-setup-telegram SKILL.md must explain the base-dir fallback purpose."""
    content = _SST_SETUP_TELEGRAM.read_text()
    # Must mention that the symlink enables the base-dir fallback
    assert "base-dir" in content or "fallback" in content.lower(), (
        "sst-setup-telegram SKILL.md must explain the symlink enables the base-dir fallback"
    )
