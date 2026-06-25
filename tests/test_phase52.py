"""Tests for Phase 52: test-design anti-pattern guards.

52.1 — `skills/framework/sst-tester/SKILL.md` (and its `ssp-cm-tester` mirror) must
       enumerate FOUR anti-pattern RED-FLAGS that the tester MUST flag when assessing
       a change's tests:
       (a) SYNTHETIC-DATA MASKING: a unit test pre-populates the data the change is
           meant to FETCH/merge, hiding the fetch-seam bug. Tester must demand a test
           that drives the real fetch path or asserts the fetch/merge is invoked.
       (b) JSDOM-CAN'T-TEST-LAYOUT: layout, virtualization, map, or color behavior
           asserted only in jsdom is NOT coverage — a real-browser (Playwright) check
           is required. A green Jest test for layout/visual DOES NOT count.
       (c) CARDINALITY GAPS: absent All/none/many coverage (aggregate view, zero rows,
           large set alongside the single-item happy path).
       (d) REQUEST-NOT-RESULT: a test asserting the REQUEST/intent but not the
           downstream RESULT (the generated artifact's contents).
       Version must be bumped to >= 1.8.0.

52.2 — `skills/dev/sst-dev-cycle/SKILL.md` §6 **E2e-only guard** must include a
       synthetic-data-masking note: a test that injects the data a NEW fetch/merge
       is meant to produce DOES NOT satisfy that change's coverage.
       Version must be bumped.
       `/sst-sanitize-transferable` must report must-fix=0 (verified in cycle).
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent
_SST_TESTER = _REPO / "skills/framework/sst-tester/SKILL.md"
_SST_DEV_CYCLE = _REPO / "skills/dev/sst-dev-cycle/SKILL.md"
_SSP_CM_TESTER = Path("/home/rob/Dev/claim_management/.claude/skills/ssp-cm-tester/SKILL.md")


def _tester_text() -> str:
    assert _SST_TESTER.exists(), f"{_SST_TESTER} must exist"
    return _SST_TESTER.read_text()


def _dev_cycle_text() -> str:
    assert _SST_DEV_CYCLE.exists(), f"{_SST_DEV_CYCLE} must exist"
    return _SST_DEV_CYCLE.read_text()


def _cm_tester_text() -> str:
    assert _SSP_CM_TESTER.exists(), f"{_SSP_CM_TESTER} must exist"
    return _SSP_CM_TESTER.read_text()


# ---------------------------------------------------------------------------
# 52.1 -- four anti-pattern RED-FLAGS in sst-tester SKILL.md
# ---------------------------------------------------------------------------

def test_sst_tester_anti_pattern_synthetic_data_masking():
    """sst-tester SKILL.md must flag the synthetic-data-masking anti-pattern:
    a unit test that pre-populates the data the change is meant to FETCH/merge
    hides the fetch-seam bug. The tester must demand a test that drives the
    real fetch path or asserts the fetch/merge is invoked with the right args."""
    text = _tester_text()
    assert re.search(
        r"(?i)synthetic.data|pre.popul\w*.*fetch|inject.*data.*meant.*fetch|"
        r"mock.*fetch.*seam|mask.*fetch|fetch.*seam",
        text,
    ), (
        "sst-tester SKILL.md must enumerate the synthetic-data-masking anti-pattern: "
        "a test pre-populates the data a change is meant to fetch, hiding the fetch-seam bug"
    )


def test_sst_tester_anti_pattern_jsdom_layout_real_browser_required():
    """sst-tester SKILL.md must flag jsdom-can't-test-layout: layout, virtualization,
    map, or color behavior asserted only in jsdom is NOT coverage; a real-browser
    (Playwright) check is required. A green Jest test does NOT count for these."""
    text = _tester_text()
    assert re.search(
        r"(?i)jsdom|jest.*layout|layout.*jest|jsdom.*cannot|jsdom.*not.*cover",
        text,
    ), (
        "sst-tester SKILL.md must flag jsdom-can't-test-layout: layout/virtualization/"
        "map/color behavior asserted only in jsdom is NOT coverage"
    )
    assert re.search(
        r"(?i)real.browser.*required|playwright.*required|require.*real.browser|"
        r"green.*jest.*does\s+not\s+count|jest.*not.*count.*layout",
        text,
    ), (
        "sst-tester SKILL.md must state that a green Jest test DOES NOT count as "
        "coverage for layout/virtualization/map/color behavior; a real-browser "
        "(Playwright) check is required"
    )


def test_sst_tester_anti_pattern_cardinality_gaps():
    """sst-tester SKILL.md must flag absent All/none/many cardinality coverage:
    single-item happy paths that never hit aggregate, zero-rows, or large-set cases."""
    text = _tester_text()
    assert re.search(
        r"(?i)cardinality.gap|single.item.*happy|absent.*all.*none.*many|"
        r"aggregate.*zero.*large|happy.path.*hide|never.*hit.*aggregate",
        text,
    ), (
        "sst-tester SKILL.md must flag absent All/none/many cardinality coverage as "
        "an anti-pattern: single-item happy paths hide failures in aggregate views, "
        "zero-row states, and large data sets"
    )


def test_sst_tester_anti_pattern_request_not_result():
    """sst-tester SKILL.md must flag the request-not-result anti-pattern:
    a test that asserts the REQUEST/intent but not the downstream RESULT
    (the generated artifact's contents)."""
    text = _tester_text()
    assert re.search(
        r"(?i)request.not.result|assert.*request.*not.*result|"
        r"intent.*not.*result|result.*artifact.*content|"
        r"assert.*POST.*body.*not.*content|not.*the.*contents",
        text,
    ), (
        "sst-tester SKILL.md must flag the request-not-result anti-pattern: a test "
        "asserting the REQUEST/intent (e.g. the POST body) but not the downstream "
        "RESULT (the generated artifact's contents) is incomplete coverage"
    )


def test_sst_tester_red_flag_language():
    """sst-tester SKILL.md must use RED-FLAG / red-flag language to name these patterns
    explicitly as things the tester must flag when assessing a change's tests."""
    text = _tester_text()
    assert re.search(r"(?i)red.flag|anti.pattern", text), (
        "sst-tester SKILL.md must use 'RED-FLAG' or 'anti-pattern' language to label "
        "the four test-design anti-patterns the tester must flag"
    )


def test_sst_tester_version_bumped_to_at_least_1_8_0():
    """sst-tester must be bumped to >= v1.8.0 to record Phase 52 anti-pattern guards."""
    text = _tester_text()
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "sst-tester SKILL.md must carry a 'version:' field"
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch) >= (1, 8, 0), (
        f"sst-tester version is {major}.{minor}.{patch}; must be >= 1.8.0 to record "
        "the Phase 52 test-design anti-pattern guards"
    )


def test_validate_frontmatter_sst_tester():
    """bin/validate-frontmatter.py must exit 0 on sst-tester after Phase 52 changes."""
    result = subprocess.run(
        [sys.executable, str(_REPO / "bin" / "validate-frontmatter.py"), str(_SST_TESTER)],
        capture_output=True, text=True, cwd=str(_REPO),
    )
    assert result.returncode == 0, (
        f"validate-frontmatter.py failed on sst-tester:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# 52.1 -- ssp-cm-tester mirror
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SSP_CM_TESTER.exists(), reason="ssp-cm-tester not present")
def test_ssp_cm_tester_base_version_bumped_for_52():
    """ssp-cm-tester base-version must be >= 1.8.0 to reflect the anti-pattern sync."""
    text = _cm_tester_text()
    m = re.search(r"^base-version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "ssp-cm-tester SKILL.md must carry a 'base-version:' field"
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch) >= (1, 8, 0), (
        f"ssp-cm-tester base-version is {major}.{minor}.{patch}; must be >= 1.8.0 "
        "to reflect the Phase 52 anti-pattern guards synced from sst-tester"
    )


@pytest.mark.skipif(not _SSP_CM_TESTER.exists(), reason="ssp-cm-tester not present")
def test_ssp_cm_tester_ssp_sync_checker_clean_for_52():
    """check-ssp-sync.py must report ssp-cm-tester as in-sync after Phase 52 bump."""
    cm_skills_dir = str(_SSP_CM_TESTER.parent.parent)
    result = subprocess.run(
        [sys.executable, str(_REPO / "bin" / "check-ssp-sync.py"),
         "--skills-dir", cm_skills_dir],
        capture_output=True, text=True, cwd=str(_REPO),
    )
    stdout = result.stdout
    assert re.search(r"in sync.*ssp-cm-tester", stdout), (
        f"ssp-cm-tester must appear in check-ssp-sync.py's 'in sync' list:\n{stdout}"
    )


# ---------------------------------------------------------------------------
# 52.2 -- synthetic-data-masking note in sst-dev-cycle §6 E2e-only guard
# ---------------------------------------------------------------------------

def test_sst_dev_cycle_e2e_guard_synthetic_data_masking():
    """sst-dev-cycle SKILL.md §6 E2e-only guard must include a synthetic-data-masking
    note: a test that injects the data a NEW fetch/merge is meant to produce DOES NOT
    satisfy that change's coverage."""
    text = _dev_cycle_text()
    assert re.search(
        r"(?i)synthetic.data.*inject|inject.*data.*new.*fetch|"
        r"inject.*data.*meant.*produc|does\s+not\s+satisfy.*coverage|"
        r"pre.popul.*data.*fetch.*does\s+not",
        text,
    ), (
        "sst-dev-cycle SKILL.md §6 E2e-only guard must include a synthetic-data-masking "
        "note: a test that injects/pre-populates the data a NEW fetch/merge is meant to "
        "produce does NOT satisfy that change's coverage"
    )


def test_sst_dev_cycle_version_bumped_for_52():
    """sst-dev-cycle must be bumped from its pre-52 version after adding the
    synthetic-data-masking note."""
    text = _dev_cycle_text()
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "sst-dev-cycle SKILL.md must carry a 'version:' field"
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch) >= (1, 13, 0), (
        f"sst-dev-cycle version is {major}.{minor}.{patch}; must be >= 1.13.0 to "
        "record the Phase 52 synthetic-data-masking note"
    )


def test_validate_frontmatter_sst_dev_cycle():
    """bin/validate-frontmatter.py must exit 0 on sst-dev-cycle after Phase 52 changes."""
    result = subprocess.run(
        [sys.executable, str(_REPO / "bin" / "validate-frontmatter.py"), str(_SST_DEV_CYCLE)],
        capture_output=True, text=True, cwd=str(_REPO),
    )
    assert result.returncode == 0, (
        f"validate-frontmatter.py failed on sst-dev-cycle:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
