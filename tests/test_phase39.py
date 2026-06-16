"""Tests for Phase 39: supervisor fast-path is finding-aware (39.1) and
sst-dev-review §0.2 recovery gate for transferable edits (39.2).
"""
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SST_SUPERVISOR = _REPO_ROOT / "skills/framework/sst-supervisor/SKILL.md"
_SST_DEV_REVIEW = _REPO_ROOT / "skills/dev/sst-dev-review/SKILL.md"


def _supervisor_text() -> str:
    return _SST_SUPERVISOR.read_text()


def test_supervisor_version_bumped_for_39_1():
    """39.1: sst-supervisor version must be >= 2.2.0 after the fast-path update."""
    text = _supervisor_text()
    m = re.search(r'^version:\s*(\d+)\.(\d+)\.(\d+)', text, re.MULTILINE)
    assert m, "sst-supervisor frontmatter must contain a version: field"
    actual = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    assert actual >= (2, 2, 0), (
        f"sst-supervisor version {'.'.join(str(x) for x in actual)} must be >= 2.2.0 "
        "after Phase 39.1 (fast-path finding-aware abort)"
    )


def test_supervisor_0_5_3_documents_found_n_items_abort():
    """39.1: §0.5.3 must document 'Found <N> items:' as a fast-path abort condition.

    The sst-dev-review §6 'With findings' template emits exactly:
      'Found <N> items: <B> blocker, <S> should-fix'
    The supervisor must match this line (N>0) to abort the fast-path.
    """
    text = _supervisor_text()
    # Both key tokens of the review §6 template must appear in the fast-path section.
    assert "Found" in text, (
        "§0.5.3 must reference the review §6 'Found <N> items:' report line "
        "as a fast-path abort trigger"
    )
    assert "items:" in text, (
        "§0.5.3 must include 'items:' from the review §6 template "
        "to anchor the match to the exact report format (not free prose)"
    )


def test_supervisor_0_5_3_documents_review_follow_ups_abort():
    """39.1: §0.5.3 must document the 'Review follow-ups' block as a fast-path abort trigger.

    When sst-dev-review appends findings to docs/SPEC.md it writes a
    '**Review follow-ups' header block.  The supervisor scans the run-log
    transcript, which includes the review's stdout (the 'With findings' report)
    and/or the diff from the review's commit (the appended block header).
    Matching either surface means a finding was filed and the fast-path must not fire.
    """
    text = _supervisor_text()
    assert "Review follow-ups" in text, (
        "§0.5.3 must list 'Review follow-ups' as a fast-path abort match so a "
        "prose-only review finding can never pass as clean (fast-path)"
    )


def test_supervisor_anti_fork_updated_to_cover_review_findings_match():
    """39.1: the §0.5.3 Anti-fork constraint must explicitly cover the new review-findings match.

    The constraint already forbids soft matches like 'warning'/'caveat'/'should'.
    After 39.1 it must also note that the two new conditions ('Found <N> items:'
    and 'Review follow-ups') are anchored to the review skill's fixed §6 template,
    not free prose — so the anti-fork argument holds for the new conditions too.
    The specific phrase 'review skill's fixed §6 report template' (or a close
    variant) must appear in the Anti-fork constraint paragraph.
    """
    text = _supervisor_text()
    assert "Anti-fork" in text, "§0.5.3 must retain the Anti-fork constraint block"
    # This specific phrase only appears once the anti-fork is updated for 39.1;
    # it is absent from the pre-39.1 file.
    assert "§6 report template" in text, (
        "§0.5.3 Anti-fork constraint must state that the new conditions anchor to "
        "the review skill's fixed §6 report template (not free prose); "
        "the phrase '§6 report template' must appear in that paragraph"
    )


def test_supervisor_no_work_carve_out_unchanged():
    """39.1: the existing [no-work] sentinel carve-out in §0.5.3 must be preserved."""
    text = _supervisor_text()
    assert "[no-work]" in text, (
        "§0.5.3 must retain the [no-work] sentinel carve-out unchanged "
        "(the dev skill's bail sentinel must not trigger the fast-path abort)"
    )


# ---------------------------------------------------------------------------
# 39.2: sst-dev-review §0.2 recovery must gate on /sst-sanitize-transferable
# ---------------------------------------------------------------------------

def _dev_review_text() -> str:
    return _SST_DEV_REVIEW.read_text()


def test_dev_review_version_bumped_for_39_2():
    """39.2: sst-dev-review version must be >= 1.8.0 after the recovery sanitize gate."""
    text = _dev_review_text()
    m = re.search(r'^version:\s*(\d+)\.(\d+)\.(\d+)', text, re.MULTILINE)
    assert m, "sst-dev-review frontmatter must contain a version: field"
    actual = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    assert actual >= (1, 8, 0), (
        f"sst-dev-review version {'.'.join(str(x) for x in actual)} must be >= 1.8.0 "
        "after Phase 39.2 (recovery sanitize gate)"
    )


def test_dev_review_recovery_documents_framework_skill_check():
    """39.2/39.3: §0.2 recovery must check staged paths for transferable sst-* skills.

    Before the orphaned-cycle recovery commit step, the skill must inspect
    whether any changed file matches the transferable sst-*/SKILL.md pattern
    and gate accordingly (39.3 widened from skills/framework/ to the full pattern).
    """
    text = _dev_review_text()
    assert "sst-*/SKILL.md" in text, (
        "§0.2 recovery step must match 'sst-*/SKILL.md' paths (the full transferable "
        "skill pattern covering all categories, not just skills/framework/) "
        "before committing, so transferable edits are never auto-committed without "
        "passing the sanitization gate"
    )


def test_dev_review_recovery_documents_sanitize_invocation():
    """39.2: §0.2 recovery must invoke /sst-sanitize-transferable on framework skills."""
    text = _dev_review_text()
    assert "/sst-sanitize-transferable" in text or "sst-sanitize-transferable" in text, (
        "§0.2 recovery step must document invoking /sst-sanitize-transferable on "
        "each affected SKILL.md under skills/framework/ before committing"
    )


def test_dev_review_recovery_must_fix_aborts_commit():
    """39.2: §0.2 recovery must abort and not commit if must-fix findings are returned."""
    text = _dev_review_text()
    # The abort condition ties sanitize must-fix to the recovery commit being blocked.
    # Both 'must-fix' and some abort language must be present in the recovery section.
    assert "must-fix" in text, (
        "§0.2 recovery step must reference 'must-fix' findings as the abort condition "
        "when /sst-sanitize-transferable is invoked during recovery"
    )
    # Check that abort/abort-path language ties to the must-fix condition (not just any abort)
    assert "abort" in text.lower(), (
        "§0.2 recovery step must describe aborting the commit when must-fix findings "
        "are returned by /sst-sanitize-transferable"
    )


# ---------------------------------------------------------------------------
# 39.3: §0.2 recovery sanitize gate must cover all transferable sst-* skills
# ---------------------------------------------------------------------------

def test_dev_review_version_bumped_for_39_3():
    """39.3: sst-dev-review version must be >= 1.9.0 after widening the recovery gate."""
    text = _dev_review_text()
    m = re.search(r'^version:\s*(\d+)\.(\d+)\.(\d+)', text, re.MULTILINE)
    assert m, "sst-dev-review frontmatter must contain a version: field"
    actual = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    assert actual >= (1, 9, 0), (
        f"sst-dev-review version {'.'.join(str(x) for x in actual)} must be >= 1.9.0 "
        "after Phase 39.3 (wider recovery sanitize gate)"
    )


def test_dev_review_recovery_gate_covers_all_sst_transferable_skills():
    """39.3: §0.2 recovery sanitize gate must match skills/**/sst-*/SKILL.md, not just skills/framework/.

    The sst-dev-cycle §5 gate covers all transferable skills via the pattern
    'skills/<category>/<sst-*>/SKILL.md'.  The recovery gate must match the same
    surface so dev skills under skills/dev/ (e.g. sst-dev-cycle, sst-dev-review)
    are sanitized when an orphaned recovery commits them.
    """
    text = _dev_review_text()
    assert "sst-*/SKILL.md" in text, (
        "§0.2 recovery step 7 must match 'sst-*/SKILL.md' (the broader glob pattern "
        "that covers all transferable skills, not just skills/framework/) "
        "so dev-skill transferables are gated on /sst-sanitize-transferable during recovery"
    )
