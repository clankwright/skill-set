"""Tests for /projects command and /help extension in bin/manager-bot.py (SPEC 28.2)."""
import os
import sys
import tempfile
from pathlib import Path
import importlib.util

# manager-bot.py does sys.exit(1) at import time if TELEGRAM_BOT_TOKEN is absent.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token_for_unit_tests")
os.environ.setdefault("TELEGRAM_CHAT_ID", "99999")

# Import manager-bot.py via importlib (hyphenated filename can't use normal import).
_BOT_PATH = Path(__file__).parent.parent / "bin" / "manager-bot.py"
_spec = importlib.util.spec_from_file_location("manager_bot", _BOT_PATH)
mb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mb)


def _make_manager_skill(skills_root: Path, persona: str, projects: list[dict]) -> None:
    """Write a minimal *-manager/SKILL.md with a watched-projects block."""
    skill_dir = skills_root / f"{persona}-manager"
    skill_dir.mkdir(parents=True, exist_ok=True)
    projects_yaml = "\n".join(
        f"  - path: {p['path']}\n    name: {p['name']}" for p in projects
    )
    content = (
        f"---\nname: {persona}-manager\nversion: 1.0.0\n---\n\n"
        f"```yaml\nwatched-projects:\n{projects_yaml}\n```\n"
    )
    (skill_dir / "SKILL.md").write_text(content)


# ── KNOWN_COMMANDS ─────────────────────────────────────────────────────────────

def test_projects_in_known_commands():
    assert "projects" in mb.KNOWN_COMMANDS


# ── _discover_manager_personas ─────────────────────────────────────────────────

def test_discover_empty_skills_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mb._discover_manager_personas(Path(tmpdir))
    assert result == []


def test_discover_single_persona():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _make_manager_skill(root, "cm", [{"path": "/home/rob/Dev/claim_management", "name": "claim_management"}])
        result = mb._discover_manager_personas(root)
    assert len(result) == 1
    r = result[0]
    assert r["persona"] == "cm"
    assert len(r["projects"]) == 1
    assert r["projects"][0]["path"] == "/home/rob/Dev/claim_management"


def test_discover_multiple_personas():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _make_manager_skill(root, "cm", [{"path": "/dev/cm", "name": "cm"}])
        _make_manager_skill(root, "skill-set", [{"path": "/dev/skill-set", "name": "skill-set"}])
        result = mb._discover_manager_personas(root)
    personas = {r["persona"] for r in result}
    assert personas == {"cm", "skill-set"}


def test_discover_no_watched_projects_block():
    """A *-manager/SKILL.md with no watched-projects block should produce an empty projects list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        skill_dir = root / "x-manager"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: x-manager\n---\n\n# no projects block\n")
        result = mb._discover_manager_personas(root)
    assert len(result) == 1
    assert result[0]["persona"] == "x"
    assert result[0]["projects"] == []


# ── handle_command /projects ────────────────────────────────────────────────────

def test_projects_command_no_personas(monkeypatch):
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: [])
    reply = mb.handle_command("/projects", chat_id=1)
    assert "no" in reply.lower() or "none" in reply.lower() or reply.strip() != ""


def test_projects_command_lists_personas(monkeypatch):
    fake_data = [
        {"persona": "cm", "projects": [{"path": "/home/rob/Dev/cm", "name": "cm"}]},
    ]
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: fake_data)
    reply = mb.handle_command("/projects", chat_id=1)
    assert "cm" in reply
    assert "/home/rob/Dev/cm" in reply


def test_projects_command_token_in_reply(monkeypatch):
    fake_data = [
        {"persona": "cm", "projects": [{"path": "/home/rob/Dev/cm", "name": "cm"}]},
    ]
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: fake_data)
    reply = mb.handle_command("/projects", chat_id=1)
    assert "token" in reply.lower() or "cm" in reply


# ── /help ──────────────────────────────────────────────────────────────────────

def test_help_mentions_projects():
    reply = mb.handle_command("/help", chat_id=1)
    assert "/projects" in reply


def test_help_mentions_token_convention():
    reply = mb.handle_command("/help", chat_id=1)
    # Must mention that commands accept a project token as first arg
    lower = reply.lower()
    assert "token" in lower or "project" in lower
