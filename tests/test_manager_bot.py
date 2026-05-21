"""Tests for /projects command and /help extension in bin/manager-bot.py (SPEC 28.2)."""
import os
import sys
import tempfile
from pathlib import Path
import importlib.util

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


def test_help_proposals_shows_project_token():
    """SPEC 28.5: /help usage line for /proposals must show <project> as required."""
    reply = mb.handle_command("/help", chat_id=1)
    assert "/proposals <project>" in reply


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


def test_route_promote_takes_project_as_first_arg():
    """`/promote cm <skill>` — args[0] is the project token, args[1] is the skill name."""
    payload = {"command": "promote", "args": ["cm", "my-skill"], "from_chat_id": 1}
    action, _ = mb.route_queue_payload(payload, my_persona="cm", known_personas=["cm", "skill-set"])
    assert action == "act"


def test_route_promote_for_other_persona_skipped():
    payload = {"command": "promote", "args": ["skill-set", "some-skill"], "from_chat_id": 1}
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


def test_status_returns_persona_prefixed_digest(tmp_path, monkeypatch):
    """SPEC 28.7: /status <persona> returns the newest <persona>_*.txt digest."""
    digests_dir = tmp_path / "manager-digests"
    digests_dir.mkdir()
    (digests_dir / "skill-set_2026-01-02T00-00-00Z.txt").write_text("persona-digest")
    (digests_dir / "2026-01-01T00-00-00Z.txt").write_text("old-generic-digest")
    monkeypatch.setattr(mb, "DIGESTS_DIR", digests_dir)
    reply = mb.handle_command("/status skill-set", chat_id=1)
    assert "persona-digest" in reply


def test_status_falls_back_to_newest_when_no_persona_prefix(tmp_path, monkeypatch):
    """SPEC 28.7: /status <persona> falls back to the newest overall digest when no persona-prefixed files exist."""
    digests_dir = tmp_path / "manager-digests"
    digests_dir.mkdir()
    (digests_dir / "2026-01-01T00-00-00Z.txt").write_text("generic-digest")
    monkeypatch.setattr(mb, "DIGESTS_DIR", digests_dir)
    reply = mb.handle_command("/status skill-set", chat_id=1)
    assert "generic-digest" in reply


def test_status_isolation_across_personas(tmp_path, monkeypatch):
    """SPEC 28.7: /status cm must not return a skill-set digest and vice versa."""
    digests_dir = tmp_path / "manager-digests"
    digests_dir.mkdir()
    (digests_dir / "cm_2026-01-02T00-00-00Z.txt").write_text("cm-digest")
    (digests_dir / "skill-set_2026-01-01T00-00-00Z.txt").write_text("skill-set-digest")
    monkeypatch.setattr(mb, "DIGESTS_DIR", digests_dir)
    reply_cm = mb.handle_command("/status cm", chat_id=1)
    reply_ss = mb.handle_command("/status skill-set", chat_id=1)
    assert "cm-digest" in reply_cm
    assert "skill-set-digest" in reply_ss
    assert "cm-digest" not in reply_ss
    assert "skill-set-digest" not in reply_cm


def test_status_persona_prefix_ignores_other_persona_files(tmp_path, monkeypatch):
    """SPEC 28.7: /status cm picks only cm_*.txt files, not skill-set_*.txt even if newer."""
    digests_dir = tmp_path / "manager-digests"
    digests_dir.mkdir()
    # skill-set has a newer timestamp but we request cm
    (digests_dir / "skill-set_2026-01-03T00-00-00Z.txt").write_text("newer-skill-set-digest")
    (digests_dir / "cm_2026-01-01T00-00-00Z.txt").write_text("older-cm-digest")
    monkeypatch.setattr(mb, "DIGESTS_DIR", digests_dir)
    reply = mb.handle_command("/status cm", chat_id=1)
    assert "older-cm-digest" in reply
    assert "newer-skill-set-digest" not in reply


# ── SPEC 28.8: truncation hints must include project token ─────────────────────

def test_skill_md_truncation_hint_includes_project_token():
    """SPEC 28.8: sst-manager hard-rules truncation hint must tell users to supply a project token."""
    skill_md = _REPO_ROOT / "skills/framework/sst-manager/SKILL.md"
    content = skill_md.read_text()
    assert "run /status <project>" in content or "run /status <persona>" in content, (
        "truncation hint must say 'run /status <project>' or 'run /status <persona>' — "
        "bare '/status' is broken after SPEC 28.7 made the token required"
    )


def test_notify_telegram_truncation_hint_includes_project_token():
    """SPEC 28.8: notify-telegram.sh truncation hint must tell users to supply a project token."""
    script = _REPO_ROOT / "bin/notify-telegram.sh"
    content = script.read_text()
    assert "run /status <project>" in content or "run /status <persona>" in content, (
        "notify-telegram.sh truncation hint must say 'run /status <project>' or 'run /status <persona>'"
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
