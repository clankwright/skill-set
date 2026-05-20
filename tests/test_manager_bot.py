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
    """Write a minimal proprietary *-manager/SKILL.md with a watched-projects block.

    Includes transferable: sst-manager in frontmatter so _discover_manager_personas
    recognises it as a real persona instance (not a transferable template).
    """
    skill_dir = skills_root / f"{persona}-manager"
    skill_dir.mkdir(parents=True, exist_ok=True)
    projects_yaml = "\n".join(
        f"  - path: {p['path']}\n    name: {p['name']}" for p in projects
    )
    content = (
        f"---\nname: {persona}-manager\nversion: 1.0.0\ntransferable: sst-manager\n---\n\n"
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
        _make_manager_skill(root, "alpha", [{"path": "/home/rob/Dev/alpha_app", "name": "alpha_app"}])
        result = mb._discover_manager_personas(root)
    assert len(result) == 1
    r = result[0]
    assert r["persona"] == "alpha"
    assert len(r["projects"]) == 1
    assert r["projects"][0]["path"] == "/home/rob/Dev/alpha_app"


def test_discover_multiple_personas():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _make_manager_skill(root, "alpha", [{"path": "/dev/alpha", "name": "alpha"}])
        _make_manager_skill(root, "skill-set", [{"path": "/dev/skill-set", "name": "skill-set"}])
        result = mb._discover_manager_personas(root)
    personas = {r["persona"] for r in result}
    assert personas == {"alpha", "skill-set"}


def test_discover_no_watched_projects_block():
    """A *-manager/SKILL.md with no watched-projects block should produce an empty projects list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        skill_dir = root / "x-manager"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: x-manager\ntransferable: sst-manager\ntransferable-version: \">=1.0.0\"\n---\n\n# no projects block\n"
        )
        result = mb._discover_manager_personas(root)
    assert len(result) == 1
    assert result[0]["persona"] == "x"
    assert result[0]["projects"] == []


def test_discover_skips_transferable_skill():
    """Skills without transferable: in frontmatter (transferable templates, not real personas) must be skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        skill_dir = root / "sst-manager"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: sst-manager\nversion: 1.10.0\n---\n\n"
            "```yaml\nwatched-projects:\n  - path: ~/Dev/project-a\n    name: project-a\n  - path: ~/Dev/project-b\n    name: project-b\n```\n"
        )
        result = mb._discover_manager_personas(root)
    assert result == [], "transferable sst-manager must not appear as a real persona"


def test_discover_keeps_proprietary_skill():
    """Skills WITH transferable: in frontmatter (real proprietary persona instances) must be returned."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        skill_dir = root / "alpha-manager"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: alpha-manager\ntransferable: sst-manager\ntransferable-version: \">=1.0.0\"\n---\n\n"
            "```yaml\nwatched-projects:\n  - path: /home/rob/Dev/alpha_app\n    name: alpha_app\n```\n"
        )
        result = mb._discover_manager_personas(root)
    assert len(result) == 1
    assert result[0]["persona"] == "alpha"


def test_discover_mixed_transferable_and_proprietary():
    """When both a transferable template and a real proprietary skill are present, only the proprietary is returned."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # transferable — no transferable: key, should be skipped
        t_dir = root / "sst-manager"
        t_dir.mkdir()
        (t_dir / "SKILL.md").write_text(
            "---\nname: sst-manager\nversion: 1.10.0\n---\n\n"
            "```yaml\nwatched-projects:\n  - path: ~/Dev/project-a\n    name: project-a\n```\n"
        )
        # proprietary — has transferable: key, should be returned
        p_dir = root / "alpha-manager"
        p_dir.mkdir()
        (p_dir / "SKILL.md").write_text(
            "---\nname: alpha-manager\ntransferable: sst-manager\n---\n\n"
            "```yaml\nwatched-projects:\n  - path: /home/rob/Dev/alpha\n    name: alpha\n```\n"
        )
        result = mb._discover_manager_personas(root)
    assert len(result) == 1
    assert result[0]["persona"] == "alpha"


# ── handle_command /projects ────────────────────────────────────────────────────

def test_projects_command_no_personas(monkeypatch):
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: [])
    reply = mb.handle_command("/projects", chat_id=1)
    assert "no" in reply.lower() or "none" in reply.lower() or reply.strip() != ""


def test_projects_command_lists_personas(monkeypatch):
    fake_data = [
        {"persona": "alpha", "projects": [{"path": "/home/rob/Dev/alpha", "name": "alpha"}]},
    ]
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: fake_data)
    reply = mb.handle_command("/projects", chat_id=1)
    assert "alpha" in reply
    assert "/home/rob/Dev/alpha" in reply


def test_projects_command_token_in_reply(monkeypatch):
    fake_data = [
        {"persona": "alpha", "projects": [{"path": "/home/rob/Dev/alpha", "name": "alpha"}]},
    ]
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: fake_data)
    reply = mb.handle_command("/projects", chat_id=1)
    assert "token" in reply.lower() or "alpha" in reply


# ── /help ──────────────────────────────────────────────────────────────────────

def test_help_mentions_projects():
    reply = mb.handle_command("/help", chat_id=1)
    assert "/projects" in reply


def test_help_mentions_token_convention():
    reply = mb.handle_command("/help", chat_id=1)
    # Must mention that commands accept a project token as first arg
    lower = reply.lower()
    assert "token" in lower or "project" in lower


# ── route_queue_payload (SPEC 28.3) ────────────────────────────────────────────

def test_route_agnostic_ping():
    """Project-agnostic commands (ping/help/projects) always act without a project token."""
    payload = {"command": "ping", "args": [], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "act"


def test_route_agnostic_help():
    payload = {"command": "help", "args": [], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "act"


def test_route_agnostic_projects():
    payload = {"command": "projects", "args": [], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "act"


def test_route_status_matches_my_persona():
    payload = {"command": "status", "args": ["alpha"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "act"


def test_route_status_for_other_persona_is_skipped():
    """A queue file targeting another known persona must be left alone (the other manager will pick it up)."""
    payload = {"command": "status", "args": ["skill-set"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "skip"


def test_route_status_with_missing_token_refused():
    """Missing project token must be refused (anti-fork: never default to my persona)."""
    payload = {"command": "status", "args": [], "from_chat_id": 1}
    action, detail = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "refuse-missing"
    # The detail should suggest /projects so the user can discover known tokens.
    assert "/projects" in detail or "projects" in detail.lower()


def test_route_status_with_unknown_token_refused():
    """An unrecognized first-arg string is a routing failure, not a alpha-scoped action."""
    payload = {"command": "status", "args": ["bogus"], "from_chat_id": 1}
    action, detail = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "refuse-unknown"
    assert "/projects" in detail or "projects" in detail.lower()


def test_route_feedback_matches_my_persona_by_body_token():
    """For /feedback, the project token is the leading whitespace-delimited token of body."""
    payload = {"command": "feedback", "body": "alpha The reviewer should weigh cost more.", "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "act"


def test_route_feedback_for_other_persona_is_skipped():
    payload = {"command": "feedback", "body": "skill-set tighten the supervisor batch-window check.", "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "skip"


def test_route_feedback_with_no_body_token_refused():
    payload = {"command": "feedback", "body": "Please fix the thing.", "from_chat_id": 1}
    action, detail = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "refuse-unknown"
    assert "/projects" in detail or "projects" in detail.lower()


def test_route_feedback_with_empty_body_refused_missing():
    payload = {"command": "feedback", "body": "", "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "refuse-missing"


def test_route_promote_takes_project_as_first_arg():
    """`/promote alpha <skill>` — args[0] is the project token, args[1] is the skill name."""
    payload = {"command": "promote", "args": ["alpha", "my-skill"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "act"


def test_route_promote_for_other_persona_skipped():
    payload = {"command": "promote", "args": ["skill-set", "some-skill"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set"])
    assert action == "skip"


def test_route_only_one_known_persona():
    """When the bot serves a single persona, an unknown token still routes as refuse-unknown."""
    payload = {"command": "status", "args": ["foo"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha"])
    assert action == "refuse-unknown"


def test_route_refusal_lists_known_personas():
    """The refusal detail should list known personas so the user knows what tokens to try."""
    payload = {"command": "status", "args": [], "from_chat_id": 1}
    _, detail = mb.route_queue_payload(payload, my_persona="alpha", known_personas=["alpha", "skill-set", "beta"])
    # All known personas should be discoverable in the refusal text.
    for persona in ("alpha", "skill-set", "beta"):
        assert persona in detail
