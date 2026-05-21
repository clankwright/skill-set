"""Tests for Phase 30.1 (MANAGER.md preamble + sst-manager walk-time read)
and Phase 30.2 (multi-project objectives.md ## Project: sections).
"""
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SST_MANAGER = _REPO_ROOT / "skills/framework/sst-manager/SKILL.md"
_TEMPLATES_MANAGER = _REPO_ROOT / "templates/MANAGER.md"
_TEMPLATES_OBJECTIVES = _REPO_ROOT / "templates/objectives.md"


# ── Phase 30.1: templates/MANAGER.md template exists ──────────────────────────

def test_manager_md_template_exists():
    """SPEC 30.1: templates/MANAGER.md skeleton must exist."""
    assert _TEMPLATES_MANAGER.exists(), "templates/MANAGER.md does not exist"


def test_manager_md_template_has_project_token_field():
    """SPEC 30.1: templates/MANAGER.md must document the project-token field."""
    content = _TEMPLATES_MANAGER.read_text()
    assert "project-token" in content or "project_token" in content, (
        "templates/MANAGER.md must document the project-token field "
        "(used for cross-check against operator-manager watched-projects[*].name)"
    )


def test_manager_md_template_has_digest_tone_section():
    """SPEC 30.1: templates/MANAGER.md must document digest-tone guidance."""
    content = _TEMPLATES_MANAGER.read_text()
    assert "digest" in content.lower() and "tone" in content.lower(), (
        "templates/MANAGER.md must include digest-tone guidance section"
    )


def test_manager_md_template_has_hard_rules_section():
    """SPEC 30.1: templates/MANAGER.md must document per-project hard rules."""
    content = _TEMPLATES_MANAGER.read_text()
    assert "hard rule" in content.lower() or "hard-rule" in content.lower(), (
        "templates/MANAGER.md must document per-project hard rules section"
    )


def test_manager_md_template_has_antifork_note():
    """SPEC 30.1: templates/MANAGER.md must note rules are advisory only (cannot override anti-fork)."""
    content = _TEMPLATES_MANAGER.read_text()
    assert "advisory" in content.lower(), (
        "templates/MANAGER.md must include an advisory note — "
        "rules here cannot override transferable anti-fork constraints"
    )


# ── Phase 30.1: sst-manager reads docs/MANAGER.md at walk time ────────────────

def test_sst_manager_inputs_table_includes_manager_md():
    """SPEC 30.1: sst-manager Inputs table must list docs/MANAGER.md as a read input."""
    content = _SST_MANAGER.read_text()
    assert "docs/MANAGER.md" in content, (
        "sst-manager/SKILL.md Inputs table must include docs/MANAGER.md as input 6"
    )


def test_sst_manager_walk_reads_manager_md():
    """SPEC 30.1: sst-manager §2 walk step must read docs/MANAGER.md alongside SPEC/TODO/FUTURE-WORK."""
    content = _SST_MANAGER.read_text()
    # The walk section (§2) should mention MANAGER.md as a read input
    walk_section_start = content.find("### 2. Walk watched projects")
    assert walk_section_start != -1, "Could not find '### 2. Walk watched projects' in sst-manager"
    # Check within the walk section prose that MANAGER.md is mentioned
    next_section = content.find("### 3.", walk_section_start)
    walk_prose = content[walk_section_start:next_section] if next_section != -1 else content[walk_section_start:]
    assert "MANAGER.md" in walk_prose, (
        "sst-manager §2 walk step must mention docs/MANAGER.md as one of the files read per project"
    )


def test_sst_manager_walk_manager_md_rules_are_advisory():
    """SPEC 30.1: sst-manager must note MANAGER.md rules are advisory steering only."""
    content = _SST_MANAGER.read_text()
    assert "advisory" in content.lower(), (
        "sst-manager must state that MANAGER.md rules are advisory steering "
        "and cannot override transferable anti-fork constraints"
    )


# ── Phase 30.2: templates/objectives.md has ## Project: section example ────────

def test_objectives_template_has_project_section_example():
    """SPEC 30.2: templates/objectives.md must include ## Project: <name> example."""
    content = _TEMPLATES_OBJECTIVES.read_text()
    assert "## Project:" in content, (
        "templates/objectives.md must include a '## Project: <name>' section example "
        "for multi-project objectives scoping"
    )


def test_objectives_template_has_backward_compat_note():
    """SPEC 30.2: templates/objectives.md must note backward-compat (no Project headers = single-project)."""
    content = _TEMPLATES_OBJECTIVES.read_text()
    lower = content.lower()
    assert "backward" in lower or "single-project" in lower or "absent" in lower, (
        "templates/objectives.md must note that absent ## Project: headers "
        "preserves single-project backward-compatible mode"
    )


def test_objectives_template_has_anti_objectives_top_level_note():
    """SPEC 30.2: templates/objectives.md must note anti-objectives stay top-level (cross-project)."""
    content = _TEMPLATES_OBJECTIVES.read_text()
    assert "top-level" in content.lower() or "cross-project" in content.lower(), (
        "templates/objectives.md must note that anti-objectives stay top-level "
        "(cross-project, not scoped to any ## Project: section)"
    )


# ── Phase 30.2: sst-manager documents ## Project: scoping in objectives ────────

def test_sst_manager_score_objectives_documents_project_sections():
    """SPEC 30.2: sst-manager §Score-against-objectives must document ## Project: header scoping."""
    content = _SST_MANAGER.read_text()
    assert "## Project:" in content, (
        "sst-manager must document ## Project: header scoping in objectives.md "
        "(used by planner gap-scoring to scope objectives per watched-project)"
    )


def test_sst_manager_planner_reads_project_scoped_objectives():
    """SPEC 30.2: sst-manager §Planner γ must note project-scoped objectives are read separately."""
    content = _SST_MANAGER.read_text()
    gamma_start = content.find("### γ. Score gaps")
    assert gamma_start != -1, "Could not find '### γ. Score gaps' in sst-manager"
    next_section = content.find("### δ.", gamma_start)
    gamma_prose = content[gamma_start:next_section] if next_section != -1 else content[gamma_start:]
    assert "Project:" in gamma_prose or "project-scoped" in gamma_prose.lower(), (
        "sst-manager §γ (Score gaps) must mention project-scoped objectives "
        "or ## Project: header handling for multi-project gap scoring"
    )
