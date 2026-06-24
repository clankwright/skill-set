"""Tests for two TODO follow-ups shipped in one cycle:

Item 1 (e2e blind-ship guard):
  sst-dev-cycle §6 must explicitly guard against marking an e2e-only SPEC item
  [x] when the only passing evidence is a parse-only / mock-only test run. The
  guard adds prose requiring a live-stack run before the flip, and names the
  [needs-live-stack] follow-up path when the live stack is unavailable.

Item 3 (batch-pick non-emission formal acceptance):
  sst-dev-cycle §1 must document the known model-behavior gap where models skip
  the mandatory [batch-pick] / [picked-difficulty] emission despite clear
  instructions. The runner's batch_pick_missing flag is the mitigation; this
  change formally records the acceptance so downstream review + supervisor know
  the fallback path is intentional, not an undiagnosed root cause.
"""
import re
from pathlib import Path

_REPO = Path(__file__).parent.parent
_DEV_CYCLE = _REPO / "skills/dev/sst-dev-cycle/SKILL.md"


def _ver(text: str):
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "frontmatter must contain a version: field"
    return tuple(int(x) for x in m.groups())


def _sec6(text: str) -> str:
    start = text.find("## 6. Update the spec")
    end = text.find("## 7. Commit", start)
    assert start != -1, "§6 section not found"
    assert end != -1, "§7 section boundary not found"
    return text[start:end]


# ---------------------------------------------------------------------------
# Version bump
# ---------------------------------------------------------------------------

def test_dev_cycle_version_bumped_for_contracts():
    """sst-dev-cycle version must be >= 1.12.0 after the two contract additions."""
    assert _ver(_DEV_CYCLE.read_text()) >= (1, 12, 0), (
        "sst-dev-cycle version must be bumped to >= 1.12.0 for the e2e guard + "
        "batch_pick_missing documentation"
    )


# ---------------------------------------------------------------------------
# Item 1: e2e blind-ship guard in §6
# ---------------------------------------------------------------------------

def test_e2e_guard_mentions_live_stack():
    """§6 must warn that e2e-only items require live-stack verification before [x]."""
    sec6 = _sec6(_DEV_CYCLE.read_text())
    assert "live stack" in sec6.lower() or "live-stack" in sec6.lower(), (
        "§6 must mention 'live stack' or 'live-stack' to guard against marking "
        "e2e-only items [x] without running them against the real service"
    )


def test_e2e_guard_mentions_e2e():
    """§6 must name e2e tests as the category requiring the live-stack guard."""
    sec6 = _sec6(_DEV_CYCLE.read_text())
    assert "e2e" in sec6.lower() or "end-to-end" in sec6.lower(), (
        "§6 must name 'e2e' or 'end-to-end' tests in the live-stack guard rule"
    )


def test_e2e_guard_prohibits_x_flip_without_live_run():
    """§6 must explicitly prohibit marking an e2e-only item [x] without a live run."""
    sec6 = _sec6(_DEV_CYCLE.read_text()).lower()
    has_prohibition = (
        "do not mark" in sec6
        or "must not" in sec6
        or "do not flip" in sec6
    )
    has_target = (
        "e2e" in sec6
        or "end-to-end" in sec6
        or "live stack" in sec6
        or "live-stack" in sec6
    )
    assert has_prohibition and has_target, (
        "§6 must prohibit (using 'do not mark', 'must not', or 'do not flip') "
        "flipping an e2e-only item to [x] without a live-stack run"
    )


def test_e2e_guard_names_followup_path():
    """§6 must name a [needs-live-stack] or equivalent marker for unavailable live stacks."""
    sec6 = _sec6(_DEV_CYCLE.read_text()).lower()
    assert "needs-live" in sec6, (
        "§6 must name '[needs-live-stack]' (or a similarly-named marker) for cycles "
        "where the live stack is unavailable — a general 'Next up' mention is "
        "insufficient; the guard must provide a specific actionable path"
    )


# ---------------------------------------------------------------------------
# Item 3: batch-pick emission — documented mitigation
# ---------------------------------------------------------------------------

def test_batch_pick_missing_mitigation_documented():
    """§1 must name batch_pick_missing as the runner mitigation for skipped emission.

    Root-cause decision (item 3, 2026-06-18): models skip the [batch-pick]
    emission despite clear instructions; the runner's batch_pick_missing flag is
    the accepted mitigation. Documenting this in the SKILL.md formally closes
    the 'masked root cause' flag and tells review/supervisor the fallback is
    intentional.
    """
    text = _DEV_CYCLE.read_text()
    assert "batch_pick_missing" in text, (
        "§1 must document 'batch_pick_missing' as the runner's fallback flag for "
        "cycles that skip the [batch-pick] emission — this is the formal acceptance "
        "of the known model-behavior gap (item 3, 2026-06-18)"
    )
