"""Tests for Phase 40: remove the sidecar promotion mechanism.

The supervisor and manager edit base-repo skills directly (sanitize-clean gate,
commit, push) instead of writing `SKILL.patch.md` sidecars promoted later via
`/sst-promote-skill-proposal`. There is no `auto-promote` mode, no sidecar, no
promotion tooling. `/sst-sanitize-transferable` stays as a hard pre-write gate.

These tests assert the new contract AND act as a grep-guard: if any sidecar /
auto-promote / promotion-tooling term reappears on the active skill / chain /
mechanism surface, the guard fails.
"""
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_SST_SUPERVISOR = _REPO_ROOT / "skills/framework/sst-supervisor/SKILL.md"
_SST_MANAGER = _REPO_ROOT / "skills/framework/sst-manager/SKILL.md"
_SST_SANITIZE = _REPO_ROOT / "skills/framework/sst-sanitize-transferable/SKILL.md"
_SCHEMA = _REPO_ROOT / "schema/skill-chain.schema.json"

# Terms that name the removed mechanism. None may appear on the active surface.
_FORBIDDEN_TERMS = (
    "SKILL.patch.md",
    "apply-skill-patch",
    "apply_skill_patch",
    "sst-promote-skill-proposal",
    "promote-skill-proposal",
    "auto-promote",
    "auto_promote",
    "sidecar",
)

# The active skill / chain / mechanism surface the guard scans. Excludes:
#   docs/ — handoff + archive + this phase's own context legitimately name the
#           removed mechanism (SPEC.md Phase 40, TODO.md Next up, SPEC-archive).
#   tests/ — assertion code that names the terms to prove their absence.
#   .claude/, .skill-runs/ — gitignored runtime state, not part of the framework.
_SURFACE_GLOBS = (
    "skills/**/SKILL.md",
    "chains/*.yaml",
    "bin/*.py",
    "bin/*.sh",
    "templates/*.md",
    "schema/*.json",
    "README.md",
    "CLAUDE.md",
)


def _surface_files() -> list[Path]:
    files: list[Path] = []
    for pat in _SURFACE_GLOBS:
        files.extend(sorted(_REPO_ROOT.glob(pat)))
    return files


# ── Grep-guard: the removed mechanism's vocabulary is gone from the surface ──

def test_surface_globs_match_real_files():
    """Sanity: the guard actually scans files (a typo'd glob would pass vacuously)."""
    files = _surface_files()
    assert len(files) >= 15, f"guard scanned only {len(files)} files; globs likely broken"
    # The two skills the phase rewrites must be in scope.
    assert _SST_SUPERVISOR in files
    assert _SST_MANAGER in files


@pytest.mark.parametrize("term", _FORBIDDEN_TERMS)
def test_no_forbidden_term_on_active_surface(term):
    """Grep-guard: no sidecar / auto-promote / promotion-tooling term survives
    on the active skill / chain / mechanism surface (40.6 acceptance)."""
    hits = []
    for f in _surface_files():
        text = f.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if term in line:
                hits.append(f"{f.relative_to(_REPO_ROOT)}:{i}: {line.strip()[:100]}")
    assert not hits, (
        f"forbidden term {term!r} reappeared on the active surface:\n" + "\n".join(hits)
    )


# ── Promotion tooling is deleted ─────────────────────────────────────────────

def test_promote_skill_proposal_dir_removed():
    """40.4: the sst-promote-skill-proposal skill directory is gone."""
    assert not (_REPO_ROOT / "skills/framework/sst-promote-skill-proposal").exists()


def test_apply_skill_patch_script_removed():
    """40.4: bin/apply-skill-patch.py is gone."""
    assert not (_REPO_ROOT / "bin/apply-skill-patch.py").exists()


# ── auto-promote removed from chains + schema ────────────────────────────────

def test_no_chain_carries_auto_promote():
    """40.3: no chains/*.yaml declares an auto-promote field."""
    for yaml_file in sorted((_REPO_ROOT / "chains").glob("*.yaml")):
        text = yaml_file.read_text()
        assert "auto-promote" not in text, f"{yaml_file.name} still declares auto-promote"


def test_schema_has_no_auto_promote_property():
    """40.3: the chain schema no longer defines an auto-promote property."""
    text = _SCHEMA.read_text()
    assert "auto-promote" not in text and "auto_promote" not in text


# ── sst-supervisor direct-edit contract (40.1) ───────────────────────────────

def test_supervisor_documents_direct_edit_base_repo_path():
    """40.1: the supervisor documents editing the base-repo skill source directly."""
    text = _SST_SUPERVISOR.read_text()
    assert "~/Dev/skill-set/skills/" in text, (
        "supervisor must name the base-repo skills path it edits directly"
    )


def test_supervisor_documents_commit_and_push():
    """40.1: the supervisor's new contract commits and pushes its edits."""
    lower = _SST_SUPERVISOR.read_text().lower()
    assert "commit" in lower and "push" in lower, (
        "supervisor must document the commit+push step of the direct-edit model"
    )


def test_supervisor_keeps_sanitize_gate():
    """40.1: /sst-sanitize-transferable stays a hard gate on transferable edits."""
    text = _SST_SUPERVISOR.read_text()
    assert "sst-sanitize-transferable" in text, (
        "supervisor must still gate transferable edits on sst-sanitize-transferable"
    )


# ── sst-manager direct-edit authorization (40.2) ─────────────────────────────

def test_manager_authorizes_base_repo_direct_edit():
    """40.2: the manager MAY edit base-repo skills directly + commit + push."""
    text = _SST_MANAGER.read_text()
    assert "~/Dev/skill-set/" in text, (
        "manager must name the base-repo it is now authorized to edit directly"
    )


def test_manager_documents_both_trigger_conditions():
    """40.2: the manager edits on user request OR its own judgment."""
    lower = _SST_MANAGER.read_text().lower()
    # user-request trigger
    assert "user request" in lower or "user requests" in lower or "the user requests" in lower
    # self-judgment trigger
    assert "deems it necessary" in lower or "its own judgment" in lower or "on its own" in lower


# ── sanitize skill no longer frames itself around promotion (40.4) ───────────

def test_sanitize_skill_has_no_promotion_framing():
    """40.4: sst-sanitize-transferable drops the /sst-promote-skill-proposal framing."""
    text = _SST_SANITIZE.read_text()
    assert "sst-promote-skill-proposal" not in text
    assert "sidecar" not in text.lower()
