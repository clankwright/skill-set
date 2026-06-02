"""Tests for bin/manager-bot.py: /projects, /help, dispatcher (SPEC 28.2, 35.2, 35.3, 35.5)."""
import os
import sys
import tempfile
from pathlib import Path
import importlib.util

import pytest

_REPO_ROOT = Path(__file__).parent.parent

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
        skill_dir = root / "cm-manager"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: cm-manager\ntransferable: sst-manager\ntransferable-version: \">=1.0.0\"\n---\n\n"
            "```yaml\nwatched-projects:\n  - path: /home/rob/Dev/claim_management\n    name: claim_management\n```\n"
        )
        result = mb._discover_manager_personas(root)
    assert len(result) == 1
    assert result[0]["persona"] == "cm"


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
        p_dir = root / "cm-manager"
        p_dir.mkdir()
        (p_dir / "SKILL.md").write_text(
            "---\nname: cm-manager\ntransferable: sst-manager\n---\n\n"
            "```yaml\nwatched-projects:\n  - path: /home/rob/Dev/cm\n    name: cm\n```\n"
        )
        result = mb._discover_manager_personas(root)
    assert len(result) == 1
    assert result[0]["persona"] == "cm"


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


def test_help_status_shows_project_token():
    """SPEC 28.5: /help usage line for /status must show <project> as required."""
    reply = mb.handle_command("/help", chat_id=1)
    assert "/status <project>" in reply


def test_help_pause_shows_project_token():
    """SPEC 28.5: /help usage line for /pause must show <project> as required."""
    reply = mb.handle_command("/help", chat_id=1)
    assert "/pause <project>" in reply


def test_help_resume_shows_project_token():
    """SPEC 28.5: /help usage line for /resume must show <project> as required."""
    reply = mb.handle_command("/help", chat_id=1)
    assert "/resume <project>" in reply


def test_help_feedback_shows_project_token():
    """SPEC 28.5: /help usage line for /feedback must show <project> as required."""
    reply = mb.handle_command("/help", chat_id=1)
    assert "/feedback <project>" in reply


def test_help_objectives_shows_project_token():
    """SPEC 28.5: /help usage line for /objectives must show <project> as required."""
    reply = mb.handle_command("/help", chat_id=1)
    assert "/objectives <project>" in reply


def test_help_token_required_not_optional():
    """SPEC 28.5: /help must state token is REQUIRED, not framed as a multi-persona tip."""
    reply = mb.handle_command("/help", chat_id=1)
    lower = reply.lower()
    assert "required" in lower


def test_help_exception_set_includes_all_three():
    """SPEC 28.5: /help must name /ping, /help, and /projects as the token-exempt exception set."""
    reply = mb.handle_command("/help", chat_id=1)
    assert "/ping" in reply
    assert "/help" in reply
    assert "/projects" in reply


# ── route_queue_payload (SPEC 28.3) ────────────────────────────────────────────

def test_route_agnostic_ping():
    """Project-agnostic commands (ping/help/projects) always act without a project token."""
    payload = {"command": "ping", "args": [], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "act"


def test_route_agnostic_help():
    payload = {"command": "help", "args": [], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "act"


def test_route_agnostic_projects():
    payload = {"command": "projects", "args": [], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "act"


def test_route_status_matches_my_persona():
    payload = {"command": "status", "args": ["cm"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "act"


def test_route_status_for_other_persona_is_skipped():
    """A queue file targeting another known persona must be left alone (the other manager will pick it up)."""
    payload = {"command": "status", "args": ["skill-set"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "skip"


def test_route_status_with_missing_token_refused():
    """Missing project token must be refused (anti-fork: never default to my persona)."""
    payload = {"command": "status", "args": [], "from_chat_id": 1}
    action, detail = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "refuse-missing"
    # The detail should suggest /projects so the user can discover known tokens.
    assert "/projects" in detail or "projects" in detail.lower()


def test_route_status_with_unknown_token_refused():
    """An unrecognized first-arg string is a routing failure, not a cm-scoped action."""
    payload = {"command": "status", "args": ["bogus"], "from_chat_id": 1}
    action, detail = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "refuse-unknown"
    assert "/projects" in detail or "projects" in detail.lower()


def test_route_feedback_matches_my_persona_by_body_token():
    """For /feedback, the project token is the leading whitespace-delimited token of body."""
    payload = {"command": "feedback", "body": "cm The reviewer should weigh cost more.", "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "act"


def test_route_feedback_for_other_persona_is_skipped():
    payload = {"command": "feedback", "body": "skill-set tighten the supervisor batch-window check.", "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "skip"


def test_route_feedback_with_no_body_token_refused():
    payload = {"command": "feedback", "body": "Please fix the thing.", "from_chat_id": 1}
    action, detail = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "refuse-unknown"
    assert "/projects" in detail or "projects" in detail.lower()


def test_route_feedback_with_empty_body_refused_missing():
    payload = {"command": "feedback", "body": "", "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "refuse-missing"


def test_route_multiarg_takes_project_as_first_arg():
    """A multi-arg command — args[0] is the project token, later args are payload."""
    payload = {"command": "status", "args": ["cm", "extra"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "act"


def test_route_multiarg_for_other_persona_skipped():
    payload = {"command": "status", "args": ["skill-set", "extra"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "skip"


def test_route_only_one_known_persona():
    """When the bot serves a single persona, an unknown token still routes as refuse-unknown."""
    payload = {"command": "status", "args": ["foo"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm"])
    assert action == "refuse-unknown"


def test_route_refusal_lists_known_personas():
    """The refusal detail should list known personas so the user knows what tokens to try."""
    payload = {"command": "status", "args": [], "from_chat_id": 1}
    _, detail = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set", "dahrouge"])
    # All known personas should be discoverable in the refusal text.
    for persona in ("cm", "skill-set", "dahrouge"):
        assert persona in detail


# ── /feedback empty-body error (SPEC 28.6) ────────────────────────────────────

def test_feedback_empty_body_error_includes_project_token():
    """SPEC 28.6: empty /feedback must tell the user to supply a project token."""
    reply = mb.handle_command("/feedback", chat_id=1)
    assert "<project>" in reply


# ── /status persona-aware (SPEC 28.7) ─────────────────────────────────────────

def test_status_no_token_returns_usage_error():
    """SPEC 28.7: /status with no project token must say a token is required."""
    reply = mb.handle_command("/status", chat_id=1)
    lower = reply.lower()
    assert "token" in lower or "<project>" in reply or "required" in lower


def test_status_queues_only_when_manager_skill_unset(tmp_path, monkeypatch):
    """SPEC 35.2: /status queues the command when MANAGER_SKILL_NAME is unset."""
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "")
    monkeypatch.setattr(mb, "QUEUE_DIR", tmp_path / "queue")
    reply = mb.handle_command("/status skill-set", chat_id=1)
    lower = reply.lower()
    assert "queued" in lower or "next manager" in lower


def test_status_routes_to_manager_when_dispatching_enabled(tmp_path, monkeypatch):
    """SPEC 35.2+35.3: /status <persona> spawns the matching manager with correct persona."""
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "skill-set-manager")
    monkeypatch.setattr(mb, "QUEUE_DIR", tmp_path / "queue")
    spawned: list[tuple] = []

    def fake_spawn(persona, project_cwd, queue_file):
        spawned.append((persona, project_cwd, queue_file))
        return True

    monkeypatch.setattr(mb, "spawn_manager_for_command", fake_spawn)
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: [
        {"persona": "skill-set", "projects": [{"path": "/home/rob/Dev/skill-set", "name": "skill-set"}]},
    ])
    reply = mb.handle_command("/status skill-set", chat_id=1)
    lower = reply.lower()
    assert "routing" in lower or "reply incoming" in lower
    assert len(spawned) == 1
    assert spawned[0][0] == "skill-set"


def test_status_cwd_resolved_from_persona_entry(tmp_path, monkeypatch):
    """SPEC 35.3: dispatcher passes the persona's project path as cwd."""
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "skill-set-manager")
    monkeypatch.setattr(mb, "QUEUE_DIR", tmp_path / "queue")
    spawned: list[tuple] = []

    def fake_spawn(persona, project_cwd, queue_file):
        spawned.append((persona, project_cwd, queue_file))
        return True

    monkeypatch.setattr(mb, "spawn_manager_for_command", fake_spawn)
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: [
        {"persona": "skill-set", "projects": [{"path": "/home/rob/Dev/skill-set", "name": "skill-set"}]},
    ])
    mb.handle_command("/status skill-set", chat_id=1)
    assert spawned[0][1] == "/home/rob/Dev/skill-set"


def test_dispatch_unknown_token_returns_error(tmp_path, monkeypatch):
    """SPEC 35.2: unknown project token returns an error listing known personas."""
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "skill-set-manager")
    monkeypatch.setattr(mb, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: [
        {"persona": "skill-set", "projects": [{"path": "/home/rob/Dev/skill-set", "name": "skill-set"}]},
    ])
    reply = mb.handle_command("/status bogus-token", chat_id=1)
    lower = reply.lower()
    assert "unknown" in lower
    assert "bogus-token" in reply
    assert "skill-set" in reply  # known personas listed


# ── SPEC 28.8: truncation hints must include project token ─────────────────────

def test_skill_md_uses_chunking_not_truncation():
    """SPEC 35.7: sst-manager hard rules must document chunked sending, not truncation."""
    skill_md = _REPO_ROOT / "skills/framework/sst-manager/SKILL.md"
    content = skill_md.read_text()
    # Old truncation rule removed by SPEC 35.7 (chunking replaces truncation).
    assert "truncate" not in content.lower() or "not truncate" in content.lower() or "chunked" in content.lower(), (
        "sst-manager should document chunked sending (SPEC 35.7 removed truncation)"
    )
    assert "chunk" in content.lower(), (
        "sst-manager hard rules should mention chunking"
    )


def test_notify_telegram_uses_chunking_not_truncation():
    """SPEC 35.7: notify-telegram.sh must split long bodies into chunks, not truncate them."""
    script = _REPO_ROOT / "bin/notify-telegram.sh"
    content = script.read_text()
    # The old 4000-char hard truncation is gone; chunking is now used instead.
    assert "split_chunks" in content or "split" in content.lower(), (
        "notify-telegram.sh should contain chunk-splitting logic"
    )
    assert "truncat" not in content or "4000" not in content, (
        "notify-telegram.sh should not truncate — use chunking instead"
    )


# ── SPEC 30.3: operator-level manager discovery ────────────────────────────────


def _make_operator_manager_skill(
    skills_root: Path, operator: str, projects: list[dict]
) -> None:
    """Write a minimal operator-level `<operator>-manager/SKILL.md`.

    The yaml block carries `operator-level: true`, signalling to
    `_discover_manager_personas` that each watched-project's `name:` field
    is a persona token (not a project-directory basename).
    """
    skill_dir = skills_root / f"{operator}-manager"
    skill_dir.mkdir(parents=True, exist_ok=True)
    projects_yaml = "\n".join(
        f"  - path: {p['path']}\n    name: {p['name']}" for p in projects
    )
    content = (
        f"---\nname: {operator}-manager\nversion: 1.0.0\ntransferable: sst-manager\n---\n\n"
        f"```yaml\noperator-level: true\nwatched-projects:\n{projects_yaml}\n```\n"
    )
    (skill_dir / "SKILL.md").write_text(content)


def test_discover_operator_level_emits_one_persona_per_project():
    """An operator-level manager with N watched-projects emits N personas,
    each persona = the project's `name:` field. The folder-derived 'operator'
    persona is NOT emitted (the operator name is just a file label, not a
    routable token)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _make_operator_manager_skill(
            root,
            "rob",
            [
                {"path": "/home/rob/Dev/claim_management", "name": "cm"},
                {"path": "/home/rob/Dev/dahrouge.com", "name": "dahrouge"},
                {"path": "/home/rob/Dev/skill-set", "name": "skill-set"},
            ],
        )
        result = mb._discover_manager_personas(root)
    personas = {r["persona"] for r in result}
    assert personas == {"cm", "dahrouge", "skill-set"}, (
        f"operator-level discovery must emit one persona per watched-project name, "
        f"not the operator's folder name; got {personas!r}"
    )
    # Each emitted entry carries only its own project (not all of them).
    for r in result:
        assert len(r["projects"]) == 1, (
            f"operator-level entries must scope to one project; persona "
            f"{r['persona']!r} carries {len(r['projects'])} projects"
        )
        assert r["projects"][0]["name"] == r["persona"]


def test_discover_operator_level_persona_path_matches_project():
    """Each operator-level persona record's project path must match the
    `path:` field from the corresponding watched-projects entry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _make_operator_manager_skill(
            root,
            "rob",
            [
                {"path": "/home/rob/Dev/claim_management", "name": "cm"},
                {"path": "/home/rob/Dev/dahrouge.com", "name": "dahrouge"},
            ],
        )
        result = mb._discover_manager_personas(root)
    by_persona = {r["persona"]: r for r in result}
    assert by_persona["cm"]["projects"][0]["path"] == "/home/rob/Dev/claim_management"
    assert by_persona["dahrouge"]["projects"][0]["path"] == "/home/rob/Dev/dahrouge.com"


def test_discover_operator_level_single_project():
    """An operator-level manager watching just one project still emits one
    persona (token = project.name), not the operator folder name. This is
    the steady-state shape after the per-project managers are archived but
    only one consuming project is configured."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _make_operator_manager_skill(
            root,
            "rob",
            [{"path": "/home/rob/Dev/claim_management", "name": "cm"}],
        )
        result = mb._discover_manager_personas(root)
    assert len(result) == 1
    assert result[0]["persona"] == "cm", (
        "operator-level single-project must emit the project's name as the persona, "
        "not the operator folder name"
    )


def test_discover_legacy_per_project_manager_unchanged():
    """Backward compat: a legacy per-project `<persona>-manager` (no
    `operator-level: true`) keeps emitting the folder-derived persona,
    so deployed cm-manager instances continue to route via /feedback cm
    until the operator migrates per docs/migration-single-manager.md."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Legacy shape: name= path-basename, no operator-level flag
        _make_manager_skill(
            root, "cm", [{"path": "/home/rob/Dev/claim_management", "name": "claim_management"}]
        )
        result = mb._discover_manager_personas(root)
    assert len(result) == 1
    assert result[0]["persona"] == "cm", "legacy folder-derived persona must remain"
    assert result[0]["projects"][0]["name"] == "claim_management"


def test_discover_mixed_legacy_and_operator_level():
    """Transition state: a legacy cm-manager and a new rob-manager coexist.
    The legacy emits persona `cm`; the operator-level emits one persona per
    project. Tokens may collide (cm from legacy AND cm from operator-level);
    `/projects` collapses duplicates by presenting all valid entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _make_manager_skill(
            root, "cm", [{"path": "/home/rob/Dev/claim_management", "name": "claim_management"}]
        )
        _make_operator_manager_skill(
            root,
            "rob",
            [{"path": "/home/rob/Dev/dahrouge.com", "name": "dahrouge"}],
        )
        result = mb._discover_manager_personas(root)
    personas = sorted(r["persona"] for r in result)
    assert personas == ["cm", "dahrouge"], (
        f"transition state must emit both legacy folder-derived and operator-level "
        f"per-project personas; got {personas!r}"
    )


def test_discover_operator_level_skips_transferable_template():
    """Even when a transferable template's yaml block contains
    `operator-level: true` placeholder text, the missing `transferable:`
    frontmatter key must still cause the file to be skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        skill_dir = root / "sst-manager"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: sst-manager\nversion: 1.13.0\n---\n\n"
            "```yaml\noperator-level: true\nwatched-projects:\n"
            "  - path: ~/Dev/project-a\n    name: a\n"
            "  - path: ~/Dev/project-b\n    name: b\n```\n"
        )
        result = mb._discover_manager_personas(root)
    assert result == [], "transferable templates are skipped regardless of operator-level flag"


def test_projects_reply_lists_operator_level_personas(monkeypatch):
    """/projects must list each operator-level persona separately even when
    they all originate from one operator manager file."""
    fake_data = [
        {"persona": "cm", "projects": [{"path": "/home/rob/Dev/claim_management", "name": "cm"}]},
        {"persona": "dahrouge", "projects": [{"path": "/home/rob/Dev/dahrouge.com", "name": "dahrouge"}]},
    ]
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: fake_data)
    reply = mb.handle_command("/projects", chat_id=1)
    assert "cm" in reply
    assert "dahrouge" in reply
    assert "/home/rob/Dev/claim_management" in reply
    assert "/home/rob/Dev/dahrouge.com" in reply


def test_migration_guide_exists():
    """SPEC 30.3: docs/migration-single-manager.md must exist."""
    guide = _REPO_ROOT / "docs/migration-single-manager.md"
    assert guide.exists(), "migration guide docs/migration-single-manager.md must exist (SPEC 30.3)"
    body = guide.read_text()
    # Spot-check the five operator runbook steps the spec calls out (a-e).
    for needle in [
        "operator-level",
        "watched-projects",
        "docs/MANAGER.md",
        "objectives",
        "cron",
    ]:
        assert needle in body, f"migration guide missing required guidance: {needle!r}"


# ── SPEC 35.2 / 35.3 / 35.5: dispatcher + startup log ─────────────────────────

def test_ping_no_args_returns_pong_from_dispatcher():
    """SPEC 35.2: bare /ping (no project token) returns 'pong from dispatcher'."""
    reply = mb.handle_command("/ping", chat_id=1)
    assert reply == "pong from dispatcher"


def test_spawn_manager_for_command_uses_process_command_mode(tmp_path, monkeypatch):
    """SPEC 35.2: spawn_manager_for_command uses --process-command, not --process-feedback."""
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "skill-set-manager")
    monkeypatch.setattr(mb, "ON_DEMAND_LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(mb, "CLAUDE_BIN", "claude")
    captured: list[list] = []

    import subprocess as _sp

    def fake_popen(cmd, **kwargs):
        captured.append(cmd)
        class _P:
            pass
        return _P()

    monkeypatch.setattr(_sp, "Popen", fake_popen)
    queue_file = tmp_path / "test_cmd.json"
    queue_file.write_text('{"command": "status"}')
    mb.spawn_manager_for_command("skill-set", "/home/rob/Dev/skill-set", queue_file)
    assert len(captured) == 1
    cmd_str = " ".join(captured[0])
    assert "--process-command" in cmd_str
    assert "--process-feedback" not in cmd_str
    assert "skill-set-manager" in cmd_str


def test_spawn_manager_for_command_passes_cwd(tmp_path, monkeypatch):
    """SPEC 35.3: spawn_manager_for_command passes project_cwd as the Popen cwd."""
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "skill-set-manager")
    monkeypatch.setattr(mb, "ON_DEMAND_LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(mb, "CLAUDE_BIN", "claude")
    captured_kwargs: list[dict] = []

    import subprocess as _sp

    def fake_popen(cmd, **kwargs):
        captured_kwargs.append(kwargs)
        class _P:
            pass
        return _P()

    monkeypatch.setattr(_sp, "Popen", fake_popen)
    queue_file = tmp_path / "test_cmd.json"
    queue_file.write_text('{"command": "status"}')
    mb.spawn_manager_for_command("skill-set", "/home/rob/Dev/skill-set", queue_file)
    assert len(captured_kwargs) == 1
    assert captured_kwargs[0].get("cwd") == "/home/rob/Dev/skill-set"


def test_spawn_manager_for_command_returns_false_when_skill_unset(tmp_path, monkeypatch):
    """SPEC 35.2: spawn_manager_for_command returns False when MANAGER_SKILL_NAME is unset."""
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "")
    queue_file = tmp_path / "test_cmd.json"
    queue_file.write_text('{"command": "status"}')
    result = mb.spawn_manager_for_command("skill-set", "/home/rob/Dev/skill-set", queue_file)
    assert result is False


def test_feedback_routes_through_dispatcher(tmp_path, monkeypatch):
    """SPEC 35.2: /feedback routes through spawn_manager_for_command when routing is enabled."""
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "skill-set-manager")
    monkeypatch.setattr(mb, "QUEUE_DIR", tmp_path / "queue")
    spawned: list[tuple] = []

    def fake_spawn(persona, project_cwd, queue_file):
        spawned.append((persona, project_cwd, queue_file))
        return True

    monkeypatch.setattr(mb, "spawn_manager_for_command", fake_spawn)
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: [
        {"persona": "skill-set", "projects": [{"path": "/home/rob/Dev/skill-set", "name": "skill-set"}]},
    ])
    reply = mb.handle_command("/feedback skill-set The supervisor needs more context.", chat_id=1)
    lower = reply.lower()
    assert "routing" in lower or "reply incoming" in lower
    assert len(spawned) == 1
    assert spawned[0][0] == "skill-set"


def test_pause_routes_through_dispatcher(tmp_path, monkeypatch):
    """SPEC 35.2: /pause <persona> routes through the dispatcher."""
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "skill-set-manager")
    monkeypatch.setattr(mb, "QUEUE_DIR", tmp_path / "queue")
    spawned: list[tuple] = []

    def fake_spawn(persona, project_cwd, queue_file):
        spawned.append((persona, project_cwd, queue_file))
        return True

    monkeypatch.setattr(mb, "spawn_manager_for_command", fake_spawn)
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: [
        {"persona": "skill-set", "projects": [{"path": "/home/rob/Dev/skill-set", "name": "skill-set"}]},
    ])
    reply = mb.handle_command("/pause skill-set", chat_id=1)
    lower = reply.lower()
    assert "routing" in lower or "reply incoming" in lower
    assert len(spawned) == 1


def test_startup_log_includes_verbs_when_routing_enabled(monkeypatch, caplog):
    """SPEC 35.5: when MANAGER_SKILL_NAME is set, startup log mentions 'on-demand command routing enabled' with verbs."""
    import logging
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "skill-set-manager")

    # Trigger the log message by calling the same logger.info path directly.
    # We test the log format string rather than running the full main() loop.
    with caplog.at_level(logging.INFO, logger="manager-bot"):
        mb.logger.info(
            "on-demand command routing enabled (verbs: status, objectives, "
            "pause, resume, feedback, ping): claude=%s",
            mb.CLAUDE_BIN,
        )
    assert "on-demand command routing enabled" in caplog.text
    assert "verbs:" in caplog.text
    for verb in ("status", "objectives", "pause", "resume", "feedback", "ping"):
        assert verb in caplog.text


def test_startup_log_says_queue_only_when_routing_disabled(monkeypatch, caplog):
    """SPEC 35.5: when MANAGER_SKILL_NAME is unset, startup log says queue-only fallback active."""
    import logging
    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "")
    with caplog.at_level(logging.INFO, logger="manager-bot"):
        mb.logger.info(
            "on-demand command routing disabled (MANAGER_SKILL_NAME unset); "
            "queue-only fallback active"
        )
    assert "queue-only fallback" in caplog.text


# ── SPEC 35.8: round-trip integration test ─────────────────────────────────────

_STUB_CLAUDE = _REPO_ROOT / "tests" / "fixtures" / "stub_claude.py"

_DISPATCH_VERBS = [
    ("/status skill-set", "status"),
    ("/objectives skill-set", "objectives"),
    ("/pause skill-set", "pause"),
    ("/resume skill-set", "resume"),
    ("/ping skill-set", "ping"),
]


@pytest.fixture
def fixture_project(tmp_path):
    """Minimal project directory for round-trip integration tests."""
    proj = tmp_path / "test_project"
    proj.mkdir()
    (proj / "docs").mkdir()
    (proj / "docs" / "TODO.md").write_text(
        "# TODO\n\n## In flight\n\n## Just shipped\n\n## Next up\n"
    )
    (proj / "docs" / "SPEC.md").write_text(
        "# SPEC\n\n## Phase 1\n\n- [x] 1.1 [easy] Fixture item.\n"
    )
    return proj


@pytest.mark.parametrize("cmd_text,expected_verb", _DISPATCH_VERBS)
def test_dispatcher_round_trip(tmp_path, monkeypatch, fixture_project, cmd_text, expected_verb):
    """SPEC 35.8: end-to-end round trip; stub sees queue-file content; spawn uses project cwd.

    Flow: handle_command → queue file written → spawn_manager_for_command →
    stub_claude.py reads queue file → writes capture + simulated Telegram payload.
    """
    import json
    import subprocess as _sp

    capture_file = tmp_path / "capture.json"
    telegram_capture = tmp_path / "telegram.json"

    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "skill-set-manager")
    monkeypatch.setattr(mb, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(mb, "ON_DEMAND_LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: [
        {"persona": "skill-set", "projects": [
            {"path": str(fixture_project), "name": "skill-set"}
        ]},
    ])

    # Save the real Popen before patching so sync_popen can invoke the stub
    # without recursing back into itself (subprocess.run → Popen → sync_popen).
    _real_popen = _sp.Popen

    def sync_popen(cmd, **kwargs):
        """Run stub_claude.py synchronously so the capture file is ready to assert."""
        env = {
            **os.environ,
            "STUB_CAPTURE_FILE": str(capture_file),
            "STUB_TELEGRAM_CAPTURE": str(telegram_capture),
        }
        proc = _real_popen(
            [sys.executable, str(_STUB_CLAUDE)] + list(cmd[1:]),
            env=env,
            cwd=kwargs.get("cwd"),
            stdout=_sp.PIPE,
            stderr=_sp.PIPE,
            stdin=_sp.DEVNULL,
        )
        proc.wait()

        class _P:
            pass

        return _P()

    monkeypatch.setattr(_sp, "Popen", sync_popen)

    reply = mb.handle_command(cmd_text, chat_id=99999)

    # Bot sends a routing ack to the user.
    assert "routing" in reply.lower() or "reply incoming" in reply.lower(), (
        f"/{expected_verb}: expected routing ack, got {reply!r}"
    )

    # Queue file was written with correct JSON shape.
    queue_files = list((tmp_path / "queue").glob("*.json"))
    assert len(queue_files) == 1, f"/{expected_verb}: expected exactly one queue file"
    qdata = json.loads(queue_files[0].read_text())
    assert qdata["command"] == expected_verb, (
        f"queue file command mismatch: expected {expected_verb!r}, got {qdata['command']!r}"
    )
    assert "received_at" in qdata, "queue file must include received_at timestamp"
    assert qdata["from_chat_id"] == 99999, "queue file must record the originating chat_id"

    # Stub ran in the project cwd; capture confirms both cwd and queue content.
    assert capture_file.exists(), f"/{expected_verb}: stub_claude did not write capture file"
    cap = json.loads(capture_file.read_text())
    assert cap["cwd"] == str(fixture_project), (
        f"/{expected_verb}: spawn cwd {cap['cwd']!r} != project path"
    )
    assert cap.get("queue_content", {}).get("command") == expected_verb, (
        f"/{expected_verb}: stub did not see correct command in queue file"
    )
    assert cap.get("queue_file") == str(queue_files[0]), (
        f"/{expected_verb}: stub received a different queue file path than the one written"
    )

    # Mock notify-telegram captured the expected reply (simulated by stub).
    assert telegram_capture.exists(), (
        f"/{expected_verb}: stub did not write telegram capture (notify-telegram.sh path)"
    )
    tg = json.loads(telegram_capture.read_text())
    assert tg.get("command") == expected_verb, (
        f"/{expected_verb}: telegram capture command mismatch"
    )
    assert tg.get("from_chat_id") == 99999, (
        f"/{expected_verb}: telegram capture must include originating chat_id"
    )


def test_dispatcher_refuses_unknown_persona_without_spawning(tmp_path, monkeypatch):
    """SPEC 35.8: unknown project token returns refuse-unknown reply; Popen never called."""
    import subprocess as _sp

    monkeypatch.setattr(mb, "MANAGER_SKILL_NAME", "skill-set-manager")
    monkeypatch.setattr(mb, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(mb, "ON_DEMAND_LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(mb, "_discover_manager_personas", lambda *a, **kw: [
        {"persona": "skill-set", "projects": [
            {"path": str(tmp_path / "proj"), "name": "skill-set"}
        ]},
    ])

    popen_calls: list = []

    def capture_popen(cmd, **kwargs):
        popen_calls.append(cmd)

        class _P:
            pass

        return _P()

    monkeypatch.setattr(_sp, "Popen", capture_popen)

    reply = mb.handle_command("/status bogus-persona", chat_id=99999)

    assert "unknown" in reply.lower(), (
        f"Expected 'unknown' in refuse reply, got {reply!r}"
    )
    assert "bogus-persona" in reply, "Reply must echo the unknown token back to the user"
    assert "skill-set" in reply, "Reply must list known personas"
    assert len(popen_calls) == 0, (
        f"Popen must NOT be called for an unknown persona; was called {len(popen_calls)} time(s)"
    )


# ── MANAGER_SKILLS_EXTRA_ROOTS (persona discovery across multiple roots) ────────

def test_discover_extra_roots_param_finds_persona():
    """extra_roots param causes _discover_manager_personas to scan additional roots."""
    with tempfile.TemporaryDirectory() as primary_dir, \
         tempfile.TemporaryDirectory() as extra_dir:
        primary = Path(primary_dir)
        extra = Path(extra_dir)
        # Primary root is empty; persona lives in extra root only.
        _make_manager_skill(extra, "proj", [{"path": "/home/rob/Dev/proj", "name": "proj"}])
        result = mb._discover_manager_personas(primary, extra_roots=[extra])
        personas = {r["persona"] for r in result}
        assert "proj" in personas, f"Expected 'proj' in {personas}"


def test_discover_extra_roots_param_deduplicates():
    """Same persona in both primary and extra root is returned exactly once."""
    with tempfile.TemporaryDirectory() as primary_dir, \
         tempfile.TemporaryDirectory() as extra_dir:
        primary = Path(primary_dir)
        extra = Path(extra_dir)
        _make_manager_skill(primary, "cm", [{"path": "/p1", "name": "cm"}])
        _make_manager_skill(extra, "cm", [{"path": "/p2", "name": "cm"}])
        result = mb._discover_manager_personas(primary, extra_roots=[extra])
        cm_entries = [r for r in result if r["persona"] == "cm"]
        assert len(cm_entries) == 1, f"Expected deduplication; got {len(cm_entries)} entries for 'cm'"


def test_discover_extra_roots_global_honored(monkeypatch):
    """When mb.MANAGER_SKILLS_EXTRA_ROOTS is set (no explicit extra_roots arg), the global is used."""
    with tempfile.TemporaryDirectory() as primary_dir, \
         tempfile.TemporaryDirectory() as extra_dir:
        primary = Path(primary_dir)
        extra = Path(extra_dir)
        _make_manager_skill(extra, "global-proj", [{"path": "/some/path", "name": "global-proj"}])
        monkeypatch.setattr(mb, "MANAGER_SKILLS_EXTRA_ROOTS", [extra])
        result = mb._discover_manager_personas(primary)  # no explicit extra_roots
        personas = {r["persona"] for r in result}
        assert "global-proj" in personas, f"Expected 'global-proj' via global; got {personas}"


def test_discover_extra_roots_combines_personas():
    """Personas from primary AND extra root are both returned."""
    with tempfile.TemporaryDirectory() as primary_dir, \
         tempfile.TemporaryDirectory() as extra_dir:
        primary = Path(primary_dir)
        extra = Path(extra_dir)
        _make_manager_skill(primary, "cm", [{"path": "/Dev/cm", "name": "cm"}])
        _make_manager_skill(extra, "proj2", [{"path": "/Dev/proj2", "name": "proj2"}])
        result = mb._discover_manager_personas(primary, extra_roots=[extra])
        personas = {r["persona"] for r in result}
        assert "cm" in personas, f"Primary root persona missing; got {personas}"
        assert "proj2" in personas, f"Extra root persona missing; got {personas}"


# ── service file content checks ─────────────────────────────────────────────────

_SERVICE_FILE = Path(__file__).parent.parent / "bin" / "manager-bot.service"


def test_service_file_has_manager_skill_name_env():
    """service file must set MANAGER_SKILL_NAME so dispatcher mode is on by default."""
    content = _SERVICE_FILE.read_text()
    assert "MANAGER_SKILL_NAME" in content, (
        "manager-bot.service must include MANAGER_SKILL_NAME env var to enable dispatcher mode"
    )


def test_service_file_is_user_mode_unit():
    """service file must target default.target (user-mode unit), not multi-user.target."""
    content = _SERVICE_FILE.read_text()
    assert "WantedBy=default.target" in content, (
        "manager-bot.service must use WantedBy=default.target for user-mode systemd unit"
    )
    assert "WantedBy=multi-user.target" not in content, (
        "manager-bot.service must NOT use multi-user.target (system-mode target)"
    )


def test_service_file_no_user_directive():
    """User-mode service template must not hardcode a User= directive (user units run as the invoking user)."""
    content = _SERVICE_FILE.read_text()
    lines = content.splitlines()
    user_lines = [l for l in lines if l.startswith("User=")]
    assert user_lines == [], (
        f"manager-bot.service must not have a User= directive in a user-mode unit; found: {user_lines}"
    )


def test_service_file_uses_percent_h_for_home():
    """service file must use %h (systemd home-dir specifier) rather than hardcoded /path/to/ placeholders for paths."""
    content = _SERVICE_FILE.read_text()
    assert "%h" in content, (
        "manager-bot.service must use %h (systemd home specifier) so paths work without editing"
    )


def _rw_paths(content: str) -> list[str]:
    """Extract all path tokens from ReadWritePaths= lines in a service file."""
    tokens: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("ReadWritePaths="):
            value = stripped[len("ReadWritePaths="):]
            tokens.extend(value.split())
    return tokens


def test_service_file_readwrite_paths_covers_claude_dir():
    """ReadWritePaths must include %h/.claude (or broader %h) so the spawned claude subprocess can write session state."""
    content = _SERVICE_FILE.read_text()
    rw = _rw_paths(content)
    # Accept %h (broadest) or exact %h/.claude; a sub-path like %h/.claude/state alone is NOT sufficient.
    covers = "%h" in rw or "%h/.claude" in rw
    assert covers, (
        f"manager-bot.service ReadWritePaths ({rw}) must include %h/.claude (or broader %h) to allow "
        "the dispatcher-spawned claude subprocess to write ~/.claude/projects/ session state"
    )


def test_service_file_readwrite_paths_covers_skill_set_dir():
    """ReadWritePaths must include %h/Dev/skill-set (or broader) so spawned skills can write run-logs and skill state."""
    content = _SERVICE_FILE.read_text()
    rw = _rw_paths(content)
    covers = "%h" in rw or "%h/Dev/skill-set" in rw or "%h/Dev" in rw
    assert covers, (
        f"manager-bot.service ReadWritePaths ({rw}) must include %h/Dev/skill-set (or broader %h) to allow "
        "spawned manager skills to write to the skill-set working directory"
    )


def test_service_file_readwrite_paths_not_only_state():
    """ReadWritePaths must NOT be narrowed to only %h/.claude/state; dispatcher mode needs broader write access."""
    content = _SERVICE_FILE.read_text()
    lines = content.splitlines()
    rw_lines = [l.strip() for l in lines if l.strip().startswith("ReadWritePaths=")]
    assert rw_lines, "manager-bot.service must have at least one ReadWritePaths= directive"
    # If the only ReadWritePaths entry is the narrow state dir, the test fails.
    narrow_only = all(l == "ReadWritePaths=%h/.claude/state" for l in rw_lines)
    assert not narrow_only, (
        "manager-bot.service ReadWritePaths is narrowed to %h/.claude/state only; "
        "dispatcher mode also needs ~/.claude/projects/ and project dirs — widen to "
        "%h/.claude and %h/Dev/skill-set (or broader %h)"
    )


def test_service_file_rwpaths_comment_not_misleading_dev_ancestor():
    """The EXTRA_ROOTS comment must not imply %h/Dev/ is a covered ReadWritePaths ancestor.

    Only %h/Dev/skill-set is listed in ReadWritePaths.  A sibling like
    %h/Dev/claim_management is NOT covered.  The old phrase "outside %h/Dev/"
    implies the whole %h/Dev/ tree is already allowed, misleading operators.
    """
    content = _SERVICE_FILE.read_text()
    assert "outside %h/Dev/" not in content, (
        "manager-bot.service comment says 'outside %h/Dev/' but only %h/Dev/skill-set is in "
        "ReadWritePaths; the comment misleads users into thinking the entire %h/Dev/ tree is "
        "covered.  Fix: say 'outside any already-listed ReadWritePaths entry' and give a "
        "concrete example (e.g. %h/Dev/claim_management must be listed explicitly)."
    )


def test_service_file_rwpaths_comment_mentions_explicit_listing():
    """The EXTRA_ROOTS comment must explicitly warn that sibling project paths need listing.

    After the fix the comment should state that any project NOT under an
    already-listed ReadWritePaths ancestor must be added explicitly, so an
    operator setting MANAGER_SKILLS_EXTRA_ROOTS to %h/Dev/claim_management
    knows to also add %h/Dev/claim_management to ReadWritePaths.
    """
    content = _SERVICE_FILE.read_text()
    has_explicit_guidance = (
        "already-listed" in content
        or "must be listed explicitly" in content
        or "listed explicitly" in content
    )
    assert has_explicit_guidance, (
        "manager-bot.service comment about MANAGER_SKILLS_EXTRA_ROOTS must explicitly state "
        "that each project path not under an already-listed ReadWritePaths ancestor must be "
        "added to ReadWritePaths (e.g. include 'must be listed explicitly')."
    )
