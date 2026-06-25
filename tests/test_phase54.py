"""Tests for Phase 54: consolidate HUMAN.md to the oversight layer only.

54.1 — `sst-dev-cycle` must NO LONGER read or write `docs/HUMAN.md`.
       The `[blocked-on-human]` pick-gating is RE-HOMED to `sst-manager` (which
       keeps any SPEC ID in an open HUMAN.md Blocks: line off the top of Next up).
       The §7a phase-completion HUMAN.md append is RE-HOMED to `sst-supervisor`
       (which files the branch-setup Blocking entry on phase-completion bail).
       Version bumped.

54.2 — `sst-dev-review` must NO LONGER read or write `docs/HUMAN.md`.
       The §4 HUMAN.md admission-test gate is removed; human-only findings route
       to `docs/FUTURE-WORK.md` instead. Version bumped.

54.3 — Mirror 54.1 + 54.2 into the CM proprietary skills (`ssp-cm-dev` and
       `ssp-cm-dev-review`). Neither CM mirror may read/write HUMAN.md.
       Base-versions bumped. SSP sync checker clean.

54.4 — Lock the invariant: ONLY `sst-supervisor` and `sst-manager` (+ their
       mirrors) may read or write `docs/HUMAN.md`. A grep test asserts no
       `skills/dev/**` SKILL.md references HUMAN.md. SPEC Handoff docs section
       and README carry the one-line invariant.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent

_DEV_CYCLE = _REPO / "skills/dev/sst-dev-cycle/SKILL.md"
_DEV_REVIEW = _REPO / "skills/dev/sst-dev-review/SKILL.md"
_SSP_CM_DEV = Path.home() / "Dev/claim_management/.claude/skills/ssp-cm-dev/SKILL.md"
_SSP_CM_DEV_REVIEW = Path.home() / "Dev/claim_management/.claude/skills/ssp-cm-dev-review/SKILL.md"
_SUPERVISOR = _REPO / "skills/framework/sst-supervisor/SKILL.md"
_MANAGER = _REPO / "skills/framework/sst-manager/SKILL.md"
_SPEC = _REPO / "docs/SPEC.md"
_README = _REPO / "README.md"


def _text(path: Path) -> str:
    assert path.exists(), f"{path} must exist"
    return path.read_text()


# ---------------------------------------------------------------------------
# 54.1 — sst-dev-cycle: no HUMAN.md read or write
# ---------------------------------------------------------------------------

def test_dev_cycle_no_human_md_read():
    """sst-dev-cycle SKILL.md must NOT instruct the skill to read docs/HUMAN.md."""
    text = _text(_DEV_CYCLE)
    # The old §0 step 5 said: "If `docs/HUMAN.md` exists, also read it end-to-end."
    # Check that no instruction to read HUMAN.md remains.
    assert not re.search(
        r"HUMAN\.md.*read.*end.to.end|read.*HUMAN\.md.*end.to.end|"
        r"If.*HUMAN\.md.*exists.*read|also\s+read.*HUMAN\.md",
        text,
        re.IGNORECASE,
    ), "sst-dev-cycle SKILL.md must NOT instruct reading HUMAN.md end-to-end"


def test_dev_cycle_no_blocked_on_human_sentinel():
    """sst-dev-cycle SKILL.md must NOT contain the [blocked-on-human] pick-gating
    logic (the entire §6b 'Blocked-on-human check' section is removed in 54.1)."""
    text = _text(_DEV_CYCLE)
    assert "blocked-on-human" not in text, (
        "sst-dev-cycle SKILL.md must NOT reference [blocked-on-human]; "
        "that gating is re-homed to sst-manager in Phase 54"
    )


def test_dev_cycle_no_phase_completion_human_md_write():
    """sst-dev-cycle SKILL.md must NOT contain the §7a HUMAN.md handoff
    (the phase-completion branch-setup append is re-homed to sst-supervisor)."""
    text = _text(_DEV_CYCLE)
    # The old §7a was titled "HUMAN.md handoff" and appended a ## Blocking entry.
    assert not re.search(
        r"7a\.\s+HUMAN\.md\s+handoff|HUMAN\.md\s+handoff.*phase.completion|"
        r"Append.*##\s*Blocking.*HUMAN\.md.*phase.*complete|"
        r"phase.*complete.*HUMAN\.md.*##\s*Blocking",
        text,
        re.IGNORECASE,
    ), (
        "sst-dev-cycle SKILL.md must NOT contain the §7a HUMAN.md phase-completion "
        "handoff; that append is re-homed to sst-supervisor in Phase 54"
    )


def test_dev_cycle_does_not_write_human_md():
    """sst-dev-cycle SKILL.md must not instruct appending/writing to HUMAN.md."""
    text = _text(_DEV_CYCLE)
    assert not re.search(
        r"append.*HUMAN\.md|write.*HUMAN\.md|HUMAN\.md.*append|notify-human-md\.sh",
        text,
        re.IGNORECASE,
    ), (
        "sst-dev-cycle SKILL.md must NOT write to HUMAN.md; "
        "the phase-completion append is re-homed to sst-supervisor"
    )


def test_dev_cycle_version_bumped_for_54():
    """sst-dev-cycle version must be >= 1.14.0 after Phase 54 changes."""
    text = _text(_DEV_CYCLE)
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "sst-dev-cycle SKILL.md must carry a 'version:' field"
    major, minor, patch_ = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch_) >= (1, 14, 0), (
        f"sst-dev-cycle version is {major}.{minor}.{patch_}; "
        "must be >= 1.14.0 after Phase 54 HUMAN.md revocation"
    )


# ---------------------------------------------------------------------------
# 54.1 re-home: sst-supervisor files phase-completion branch-setup entry
# ---------------------------------------------------------------------------

def test_supervisor_handles_phase_completion_human_md():
    """sst-supervisor SKILL.md must contain prose stating it files the phase-completion
    branch-setup ## Blocking entry in HUMAN.md when a phase-completion bail is detected."""
    text = _text(_SUPERVISOR)
    assert re.search(
        r"phase.completion.*HUMAN\.md|HUMAN\.md.*phase.completion|"
        r"branch.setup.*Blocking.*HUMAN\.md|"
        r"phase.*complete.*no.work.*bail.*HUMAN\.md|"
        r"supervisor.*files.*branch.*setup|"
        r"phase.completion bail.*supervisor.*HUMAN",
        text,
        re.IGNORECASE,
    ), (
        "sst-supervisor SKILL.md must document that it files the phase-completion "
        "branch-setup ## Blocking entry in HUMAN.md when the dev emits a "
        "[no-work] phase <N> complete sentinel (re-homed from sst-dev-cycle §7a)"
    )


# ---------------------------------------------------------------------------
# 54.1 re-home: sst-manager keeps blocked items off the top of Next up
# ---------------------------------------------------------------------------

def test_manager_keeps_blocked_items_off_next_up():
    """sst-manager SKILL.md must contain prose explicitly stating that SPEC IDs
    named in open HUMAN.md Blocks: entries are kept off the pickable top of
    ## Next up so the dev cycle never picks a blocked item (Phase 54 re-home)."""
    text = _text(_MANAGER)
    # The test requires language specifically about the Phase 54 re-homed behavior:
    # the manager moves blocked items out of the dev cycle's pick path.
    # This must be NEWLY added language, not just coincidental co-occurrence.
    assert re.search(
        r"HUMAN\.md.*Blocks:.*off.*pickable|"
        r"SPEC\s+ID.*Blocks:.*off.*Next\s+up|"
        r"keep.*Blocks:.*off.*top.*Next\s+up|"
        r"blocked.*SPEC\s+ID.*pickable.*top|"
        r"dev.*never.*picks.*blocked|"
        r"blocked.items.*off.*dev.*pick|"
        r"HUMAN\.md.*Blocks.*dev\s+cycle.*never.*pick",
        text,
        re.IGNORECASE,
    ), (
        "sst-manager SKILL.md must document (Phase 54 re-home) that it keeps any "
        "SPEC ID in an open HUMAN.md Blocks: line off the pickable top of "
        "## Next up so the dev cycle never picks a blocked item"
    )


def test_manager_version_bumped_for_54():
    """sst-manager version must be >= 2.4.0 after Phase 54 changes."""
    text = _text(_MANAGER)
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "sst-manager SKILL.md must carry a 'version:' field"
    major, minor, patch_ = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch_) >= (2, 4, 0), (
        f"sst-manager version is {major}.{minor}.{patch_}; "
        "must be >= 2.4.0 after Phase 54 blocked-item gating re-home"
    )


# ---------------------------------------------------------------------------
# 54.2 — sst-dev-review: no HUMAN.md read or write
# ---------------------------------------------------------------------------

def test_dev_review_does_not_read_human_md():
    """sst-dev-review SKILL.md must NOT instruct reading docs/HUMAN.md on open."""
    text = _text(_DEV_REVIEW)
    # The old Handoff docs section listed docs/HUMAN.md in the "reads" list.
    assert not re.search(
        r"reads.*HUMAN\.md.*on\s+open|"
        r"HUMAN\.md.*all\s+if\s+present.*on\s+open|"
        r"reads\s+`docs/SPEC\.md`.*`docs/TODO\.md`.*`docs/HUMAN\.md`|"
        r"read.*docs/HUMAN\.md.*end.to.end",
        text,
        re.IGNORECASE,
    ), "sst-dev-review SKILL.md must NOT instruct reading HUMAN.md on open"


def test_dev_review_does_not_write_human_md():
    """sst-dev-review SKILL.md must NOT have HUMAN.md as a write destination
    in §4's route-first decision tree."""
    text = _text(_DEV_REVIEW)
    # The old §4 had a "docs/HUMAN.md (human-only blocker findings)" route.
    assert not re.search(
        r"##\s*Blocking.*HUMAN\.md.*human.only\s+blocker|"
        r"Route.*HUMAN\.md.*human.only|"
        r"HUMAN\.md\s+admission\s+test.*hard\s+gate|"
        r"admission\s+test.*hard\s+gate.*HUMAN\.md",
        text,
        re.IGNORECASE,
    ), (
        "sst-dev-review SKILL.md must NOT contain the HUMAN.md admission-test "
        "gate in §4; that write path is removed in Phase 54"
    )


def test_dev_review_routes_human_only_findings_to_future_work():
    """sst-dev-review SKILL.md must route human-only findings to FUTURE-WORK.md
    with a 'human-only:' prefix after Phase 54 (the HUMAN.md route is gone,
    FUTURE-WORK.md is the new destination for human-only findings)."""
    text = _text(_DEV_REVIEW)
    # After Phase 54 the HUMAN.md admission-test gate is removed from §4's
    # route-first decision tree. The FUTURE-WORK.md destination must explicitly
    # accept human-only findings (previously routed to HUMAN.md).
    # The spec says: "RE-HOME ... to docs/FUTURE-WORK.md (parked, with a clear
    # 'human-only:' prefix)".
    assert re.search(
        r"human.only.*prefix.*FUTURE.WORK|"
        r"FUTURE.WORK.*human.only.*prefix|"
        r"human-only:.*FUTURE.WORK|"
        r"FUTURE-WORK\.md.*human.only\s*:\s*prefix|"
        r"route.*human.only.*findings.*FUTURE.WORK|"
        r"human.only\s+findings.*FUTURE.WORK|"
        r"FUTURE.WORK.*human.only\s+findings",
        text,
        re.IGNORECASE,
    ), (
        "sst-dev-review SKILL.md must explicitly route human-only findings "
        "to docs/FUTURE-WORK.md with a 'human-only:' prefix, replacing the "
        "removed HUMAN.md admission-test gate (Phase 54)"
    )


def test_dev_review_no_notify_human_md_call():
    """sst-dev-review SKILL.md must NOT call notify-human-md.sh, since it no
    longer writes to HUMAN.md."""
    text = _text(_DEV_REVIEW)
    assert "notify-human-md.sh" not in text, (
        "sst-dev-review SKILL.md must NOT reference notify-human-md.sh; "
        "it no longer writes to HUMAN.md after Phase 54"
    )


def test_dev_review_human_md_not_in_git_add():
    """sst-dev-review SKILL.md must NOT include docs/HUMAN.md in its §5 git add
    command (since it no longer writes HUMAN.md)."""
    text = _text(_DEV_REVIEW)
    # Check that no git add line includes HUMAN.md
    assert not re.search(
        r"git\s+add\s+.*HUMAN\.md|git\s+add.*docs/HUMAN",
        text,
    ), (
        "sst-dev-review SKILL.md must NOT include docs/HUMAN.md in any git add "
        "line; the skill no longer writes HUMAN.md after Phase 54"
    )


def test_dev_review_version_bumped_for_54():
    """sst-dev-review version must be >= 1.13.0 after Phase 54 changes."""
    text = _text(_DEV_REVIEW)
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "sst-dev-review SKILL.md must carry a 'version:' field"
    major, minor, patch_ = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch_) >= (1, 13, 0), (
        f"sst-dev-review version is {major}.{minor}.{patch_}; "
        "must be >= 1.13.0 after Phase 54 HUMAN.md revocation"
    )


# ---------------------------------------------------------------------------
# 54.3 — CM proprietary mirrors: no HUMAN.md read or write
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SSP_CM_DEV.exists(), reason="ssp-cm-dev not present on this host")
def test_ssp_cm_dev_no_blocked_on_human_gate():
    """ssp-cm-dev SKILL.md must NOT contain the [blocked-on-human] gate text
    after Phase 54."""
    text = _text(_SSP_CM_DEV)
    assert "blocked-on-human" not in text, (
        "ssp-cm-dev SKILL.md must NOT reference [blocked-on-human]; "
        "that gating is re-homed to sst-manager in Phase 54"
    )


@pytest.mark.skipif(not _SSP_CM_DEV.exists(), reason="ssp-cm-dev not present on this host")
def test_ssp_cm_dev_no_human_md_filing():
    """ssp-cm-dev SKILL.md must NOT instruct filing follow-ups to HUMAN.md
    mid-cycle after Phase 54 (those now go to FUTURE-WORK.md)."""
    text = _text(_SSP_CM_DEV)
    # The old text had: "file it to docs/HUMAN.md under ## High"
    assert not re.search(
        r"file.*docs/HUMAN\.md.*##\s*High|"
        r"append.*HUMAN\.md.*##\s*High|"
        r"HUMAN\.md\s+under\s+##\s*High",
        text,
        re.IGNORECASE,
    ), (
        "ssp-cm-dev SKILL.md must NOT instruct filing human-only follow-ups to "
        "HUMAN.md ## High mid-cycle; those now route to FUTURE-WORK.md (Phase 54)"
    )


@pytest.mark.skipif(not _SSP_CM_DEV.exists(), reason="ssp-cm-dev not present on this host")
def test_ssp_cm_dev_no_human_md_backlog_reference():
    """ssp-cm-dev SKILL.md §0b must NOT reference docs/HUMAN.md as the
    'Human-blocker backlog' read on every cycle."""
    text = _text(_SSP_CM_DEV)
    assert not re.search(
        r"Human.blocker\s+backlog.*HUMAN\.md|"
        r"docs/HUMAN\.md.*read\s+on\s+every\s+cycle|"
        r"read.*HUMAN\.md.*blocked.on.human\s+gating",
        text,
        re.IGNORECASE,
    ), (
        "ssp-cm-dev §0b must NOT list docs/HUMAN.md as a file read on every cycle; "
        "the [blocked-on-human] gating is re-homed to sst-manager (Phase 54)"
    )


@pytest.mark.skipif(not _SSP_CM_DEV.exists(), reason="ssp-cm-dev not present on this host")
def test_ssp_cm_dev_base_version_updated():
    """ssp-cm-dev base-version must be >= 1.14.0 to track the bumped sst-dev-cycle."""
    text = _text(_SSP_CM_DEV)
    m = re.search(r"^base-version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "ssp-cm-dev must carry a 'base-version:' field"
    major, minor, patch_ = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch_) >= (1, 14, 0), (
        f"ssp-cm-dev base-version is {major}.{minor}.{patch_}; "
        "must be >= 1.14.0 to track the Phase 54 sst-dev-cycle bump"
    )


@pytest.mark.skipif(not _SSP_CM_DEV_REVIEW.exists(), reason="ssp-cm-dev-review not present on this host")
def test_ssp_cm_dev_review_no_inherited_human_md_section():
    """ssp-cm-dev-review SKILL.md must NOT contain the 'Inherited Phase 31
    HUMAN.md routing' section after Phase 54."""
    text = _text(_SSP_CM_DEV_REVIEW)
    assert not re.search(
        r"Inherited\s+Phase\s+31\s+HUMAN\.md\s+routing|"
        r"##\s+Inherited\s+Phase\s+31",
        text,
        re.IGNORECASE,
    ), (
        "ssp-cm-dev-review SKILL.md must NOT contain the 'Inherited Phase 31 "
        "HUMAN.md routing' section; it is removed wholesale in Phase 54"
    )


@pytest.mark.skipif(not _SSP_CM_DEV_REVIEW.exists(), reason="ssp-cm-dev-review not present on this host")
def test_ssp_cm_dev_review_no_human_md_write():
    """ssp-cm-dev-review SKILL.md must NOT instruct appending to HUMAN.md."""
    text = _text(_SSP_CM_DEV_REVIEW)
    assert not re.search(
        r"append.*HUMAN\.md|file.*HUMAN\.md|notify-human-md\.sh|"
        r"write.*HUMAN\.md",
        text,
        re.IGNORECASE,
    ), (
        "ssp-cm-dev-review SKILL.md must NOT instruct writing to HUMAN.md; "
        "that path is removed in Phase 54"
    )


@pytest.mark.skipif(not _SSP_CM_DEV_REVIEW.exists(), reason="ssp-cm-dev-review not present on this host")
def test_ssp_cm_dev_review_base_version_updated():
    """ssp-cm-dev-review base-version must be >= 1.13.0 to track bumped sst-dev-review."""
    text = _text(_SSP_CM_DEV_REVIEW)
    m = re.search(r"^base-version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "ssp-cm-dev-review must carry a 'base-version:' field"
    major, minor, patch_ = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch_) >= (1, 13, 0), (
        f"ssp-cm-dev-review base-version is {major}.{minor}.{patch_}; "
        "must be >= 1.13.0 to track the Phase 54 sst-dev-review bump"
    )


# ---------------------------------------------------------------------------
# 54.4 — Lock the invariant: only supervisor + manager may use HUMAN.md
# ---------------------------------------------------------------------------

def test_skills_dev_no_human_md_references():
    """No SKILL.md under skills/dev/** may reference HUMAN.md as a read/write
    path after Phase 54 (only oversight layer skills may use HUMAN.md)."""
    dev_skills_dir = _REPO / "skills" / "dev"
    human_md_refs = []
    for skill_md in dev_skills_dir.glob("**/SKILL.md"):
        content = skill_md.read_text()
        # Look for substantive references (path, read, write, append instructions).
        # Exclude pure historical context sentences that merely NAME the file.
        if re.search(
            r"docs/HUMAN\.md|HUMAN\.md.*read|read.*HUMAN\.md|"
            r"write.*HUMAN\.md|HUMAN\.md.*write|"
            r"append.*HUMAN\.md|HUMAN\.md.*append|"
            r"notify-human-md|blocked-on-human|"
            r"HUMAN\.md.*end.to.end",
            content,
            re.IGNORECASE,
        ):
            human_md_refs.append(str(skill_md.relative_to(_REPO)))
    assert not human_md_refs, (
        f"The following skills/dev/** SKILL.md files still reference HUMAN.md; "
        f"Phase 54 requires ONLY sst-supervisor + sst-manager to use HUMAN.md:\n"
        + "\n".join(f"  {p}" for p in human_md_refs)
    )


def test_spec_handoff_docs_has_human_md_invariant():
    """docs/SPEC.md 'Handoff docs' section (not Phase 54 context prose) must
    state the HUMAN.md invariant: only sst-supervisor and sst-manager may use it.

    The Phase 54 context paragraph already names the invariant; Phase 54.4
    requires it to also appear in the canonical 'Handoff docs' section so
    consuming projects see it as a framework rule, not just a Phase 54 note.
    """
    text = _text(_SPEC)
    # Find the Handoff docs section (it is a ## header in the Primary concepts area).
    # The invariant must appear WITHIN or AFTER the Handoff docs section header,
    # NOT just in the Phase 54 context paragraph.
    handoff_idx = text.find("### Handoff docs")
    assert handoff_idx != -1, "docs/SPEC.md must have a '### Handoff docs' section"
    # Find the next major section (##) after the Handoff docs header.
    next_section = text.find("\n##", handoff_idx + 1)
    if next_section == -1:
        next_section = len(text)
    handoff_section = text[handoff_idx:next_section]
    assert re.search(
        r"HUMAN\.md.*only.*supervisor.*manager|"
        r"supervisor.*manager.*only.*HUMAN\.md|"
        r"ONLY.*HUMAN\.md.*supervisor.*manager|"
        r"HUMAN\.md.*oversight\s+layer|"
        r"oversight\s+layer.*HUMAN\.md",
        handoff_section,
        re.IGNORECASE,
    ), (
        "docs/SPEC.md '### Handoff docs' section must state the invariant that "
        "HUMAN.md is owned exclusively by sst-supervisor + sst-manager "
        "(the oversight layer); this is a Phase 54.4 addition to the section, "
        "separate from the Phase 54 context paragraph"
    )


def test_readme_has_human_md_invariant():
    """README.md must state the HUMAN.md invariant: only supervisor + manager
    may read/write HUMAN.md (oversight layer only)."""
    text = _text(_README)
    assert re.search(
        r"HUMAN\.md.*only.*supervisor.*manager|"
        r"supervisor.*manager.*only.*HUMAN\.md|"
        r"HUMAN\.md.*oversight\s+layer|"
        r"oversight\s+layer.*HUMAN\.md|"
        r"HUMAN\.md.*sst-supervisor.*sst-manager",
        text,
        re.IGNORECASE,
    ), (
        "README.md must document the Phase 54 invariant: only sst-supervisor "
        "and sst-manager (the oversight layer) may read/write docs/HUMAN.md"
    )


def test_validate_frontmatter_dev_cycle():
    """bin/validate-frontmatter.py must exit 0 on sst-dev-cycle after Phase 54."""
    result = subprocess.run(
        [sys.executable, str(_REPO / "bin" / "validate-frontmatter.py"), str(_DEV_CYCLE)],
        capture_output=True, text=True, cwd=str(_REPO),
    )
    assert result.returncode == 0, (
        f"validate-frontmatter.py failed on sst-dev-cycle:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_validate_frontmatter_dev_review():
    """bin/validate-frontmatter.py must exit 0 on sst-dev-review after Phase 54."""
    result = subprocess.run(
        [sys.executable, str(_REPO / "bin" / "validate-frontmatter.py"), str(_DEV_REVIEW)],
        capture_output=True, text=True, cwd=str(_REPO),
    )
    assert result.returncode == 0, (
        f"validate-frontmatter.py failed on sst-dev-review:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
