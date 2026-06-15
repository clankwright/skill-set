"""Tests for Phase 39: supervisor fast-path is finding-aware.

39.1: sst-supervisor §0.5.3 must abort the fast-path when the review
transcript contains a 'Found <N> items:' line (N>0) or a 'Review follow-ups'
block, so a prose-only finding can never pass as `clean (fast-path)`.
"""
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SST_SUPERVISOR = _REPO_ROOT / "skills/framework/sst-supervisor/SKILL.md"


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
