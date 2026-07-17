"""Phase 67 tests: inline the sanitize gate into sst-dev-cycle (H43.1 option 1).

67.1 — the §3 step-5 sanitize gate is read-and-followed IN-SESSION (no
Skill-tool sub-invocation), so no sub-skill return exists anywhere in the dev
cycle to be mistaken for task-completion. The Phase 66 runner commit re-prompt
stays as the generic backstop (its behavior tests live in test_skill_chain.py).
Mirrors (ssp-cm-dev, ssp-dahrouge-dev) are reconciled to base 1.21.0.
"""
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent
_DEV_CYCLE = _REPO / "skills" / "dev" / "sst-dev-cycle" / "SKILL.md"
_SSP_CM_DEV = Path("/home/rob/Dev/claim_management/.claude/skills/ssp-cm-dev/SKILL.md")
_SSP_DAHROUGE_DEV = Path("/home/rob/Dev/dahrouge.com/.claude/skills/ssp-dahrouge-dev/SKILL.md")


def _ver(text: str) -> tuple:
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "SKILL.md must carry a SemVer version"
    return tuple(int(g) for g in m.groups())


def _base_ver(text: str) -> tuple:
    m = re.search(r"^base-version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "wrapper must carry a SemVer base-version"
    return tuple(int(g) for g in m.groups())


def test_dev_cycle_version_bumped_for_phase67():
    """67.1: sst-dev-cycle version must be >= 1.21.0."""
    assert _ver(_DEV_CYCLE.read_text()) >= (1, 21, 0)


def test_dev_cycle_sanitize_gate_runs_in_session():
    """67.1: §3 step 5 must instruct running the sanitize scan in-session
    (read the sanitize skill's SKILL.md and follow its Process yourself).
    """
    text = _DEV_CYCLE.read_text()
    assert "IN-SESSION" in text
    assert "follow its Process yourself" in text
    assert "sst-sanitize-transferable/SKILL.md" in text, (
        "the gate must name the sanitize skill's SKILL.md as the definition "
        "to read and follow"
    )


def test_dev_cycle_forbids_skill_tool_sub_invocation():
    """67.1: the gate must explicitly forbid the Skill-tool sub-invocation —
    the sub-skill return is the seam H43.1 documented.
    """
    text = _DEV_CYCLE.read_text()
    assert "Do NOT run the gate as a Skill-tool sub-invocation" in text


def test_dev_cycle_slash_command_block_removed():
    """67.1: the old fenced `/sst-sanitize-transferable <path>` invocation
    command is gone (a path reference to the SKILL.md remains legal).
    """
    text = _DEV_CYCLE.read_text()
    assert "/sst-sanitize-transferable <path-to-SKILL.md>" not in text


def test_dev_cycle_rigor_clause_preserved():
    """67.1: inlining must not weaken the gate — a casual judgment without the
    rubric walk and findings file still does not satisfy the requirement.
    """
    text = _DEV_CYCLE.read_text()
    assert "does NOT satisfy this requirement" in text
    assert "findings" in text


def test_dev_cycle_s5_documents_inline_seam_fix_and_backstop():
    """67.1: §5 explains the inlining (no sub-skill return anywhere in the
    cycle) and names the runner's commit re-prompt as the generic backstop
    that must not be relied on.
    """
    text = _DEV_CYCLE.read_text()
    assert "no sub-skill return exists anywhere in the cycle" in text
    assert "generic backstop" in text
    assert "never rely on it" in text


@pytest.mark.skipif(not _SSP_CM_DEV.exists(), reason="ssp-cm-dev not present")
def test_ssp_cm_dev_reconciled_to_phase67_base():
    """67.1: the CM dev mirror pins base-version to the bumped base and
    carries the in-session gate wording.
    """
    text = _SSP_CM_DEV.read_text()
    assert _base_ver(text) == _ver(_DEV_CYCLE.read_text())
    assert "IN-SESSION" in text
    assert "Skill-tool sub-invocation" in text


@pytest.mark.skipif(not _SSP_DAHROUGE_DEV.exists(),
                    reason="ssp-dahrouge-dev not present")
def test_ssp_dahrouge_dev_reconciled_to_phase67_base():
    """67.1: the dahrouge dev mirror pins base-version to the bumped base and
    carries the in-session gate wording.
    """
    text = _SSP_DAHROUGE_DEV.read_text()
    assert _base_ver(text) == _ver(_DEV_CYCLE.read_text())
    assert "IN-SESSION" in text
    assert "Skill-tool sub-invocation" in text
