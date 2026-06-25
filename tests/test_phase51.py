"""Tests for Phase 51: make the tester broaden beyond the dev's named scope.

51.4 (review follow-up) — sst-tester SKILL.md step 6a "Read the diff for blast
       radius" bullet must include a mode-conditional note: in standalone mode
       the diff source is per-file commit history (`git log -p -- <file>`) for
       each resolved file, not `git show HEAD` alone (which misses commits
       from earlier in the same phase).  The in-chain path using `git show HEAD`
       remains correct and must still be named.

51.1 — `skills/framework/sst-tester/SKILL.md` must carry a blast-radius /
       adjacent-surface mandate in its Run lifecycle section stating:
       - derive-from-diff: tester reads the diff and enumerates what ELSE
         consumes each touched component/state/endpoint;
       - adjacent/integrated-surface probing (not just the named surface);
       - All/none/many cardinalities (aggregate, zero rows, large sets);
       - guidance-as-floor: explicitly states tester-guidance.md is a FLOOR,
         not a ceiling;
       - record-uncovered-gaps: documents that self-derived cases run AND
         high-risk gaps not covered are recorded in findings;
       - wind-down/budget reconciliation: broadening is coverage-thinking
         within the existing budget, not unbounded.
       Version must be bumped to at least 1.7.0.

51.2 — `ssp-cm-tester` (at /home/rob/Dev/claim_management/.claude/skills/
       ssp-cm-tester/SKILL.md) must carry the inherited blast-radius mandate
       (base-version bumped to >= 1.7.0) PLUS CM-specific heuristics:
       - merged claims table: scroll/virtualization (scraped rows), select-all
         across both partitions, fly-zoom;
       - AppContext/shared client-data or data-fetch path: Dashboard + Expenses
         + Reports for "All clients" aggregate AND specific client AND
         switch-back, client dropdown must not disappear;
       - map styling/CSS vars: legend swatch must match the rendered layer;
       - report/credit path: sanity-check numbers, not merely that it renders.
       The SSP sync checker must report the wrapper as in-sync.

51.3 — README.md must describe the tester as ALSO deriving and running its own
       adjacent/blast-radius cases (guidance is a floor, not a ceiling), not
       merely executing the dev's guidance.
       `bin/validate-frontmatter.py` must exit clean on sst-tester.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent
_SST_TESTER = _REPO / "skills/framework/sst-tester/SKILL.md"
_SSP_CM_TESTER = Path("/home/rob/Dev/claim_management/.claude/skills/ssp-cm-tester/SKILL.md")
_README = _REPO / "README.md"


def _tester_text() -> str:
    assert _SST_TESTER.exists(), f"{_SST_TESTER} must exist"
    return _SST_TESTER.read_text()


def _cm_tester_text() -> str:
    assert _SSP_CM_TESTER.exists(), f"{_SSP_CM_TESTER} must exist"
    return _SSP_CM_TESTER.read_text()


def _readme_text() -> str:
    assert _README.exists(), f"{_README} must exist"
    return _README.read_text()


# ---------------------------------------------------------------------------
# 51.1 -- blast-radius mandate in sst-tester SKILL.md
# ---------------------------------------------------------------------------

def test_sst_tester_blast_radius_derive_from_diff():
    """sst-tester SKILL.md must instruct the tester to read the diff and enumerate
    what else consumes each touched component/state/endpoint."""
    text = _tester_text()
    assert re.search(r"(?i)diff|touched\s+files?", text), (
        "sst-tester SKILL.md must instruct the tester to read the diff / touched "
        "files to enumerate blast-radius surfaces"
    )
    assert re.search(r"(?i)blast.radius|what\s+else\s+consumes|adjacent.+surface", text), (
        "sst-tester SKILL.md must include blast-radius language: enumerating what "
        "else consumes touched components/state/endpoints"
    )


def test_sst_tester_blast_radius_adjacent_integrated_surfaces():
    """sst-tester SKILL.md must mandate exercising adjacent and integrated surfaces."""
    text = _tester_text()
    assert re.search(r"(?i)adjacent.+surface|integrated.+surface|adjacent.+integrated", text), (
        "sst-tester SKILL.md must explicitly require exercising adjacent + "
        "integrated surfaces beyond the dev's named guidance"
    )


def test_sst_tester_blast_radius_all_none_many_cardinalities():
    """sst-tester SKILL.md must explicitly require probing all/none/many cardinalities."""
    text = _tester_text()
    assert re.search(r"(?i)all.+none.+many|cardinali|aggregate.+zero|all.clients", text), (
        "sst-tester SKILL.md must explicitly require probing 'All / none / many' "
        "cardinalities (aggregate views, zero rows, large sets)"
    )


def test_sst_tester_blast_radius_guidance_as_floor():
    """sst-tester SKILL.md must explicitly state guidance is a FLOOR, not a ceiling."""
    text = _tester_text()
    assert re.search(r"(?i)floor.*ceiling|floor,\s*not\s*a\s*ceiling|guidance.*floor", text), (
        "sst-tester SKILL.md must explicitly state that tester-guidance.md is a "
        "FLOOR, not a ceiling"
    )


def test_sst_tester_blast_radius_record_uncovered_gaps():
    """sst-tester SKILL.md must require recording self-derived cases AND uncovered gaps."""
    text = _tester_text()
    assert re.search(r"(?i)uncovered.+gap|gap.*not.*cover|could\s+not\s+cover|high.risk.*surface.*not", text), (
        "sst-tester SKILL.md must require the tester to record high-risk surfaces "
        "it could NOT cover in the findings, so gaps are visible to the reviewer"
    )
    assert re.search(r"(?i)self.derived|derived.+case|own.+test\s+case", text), (
        "sst-tester SKILL.md must mention recording self-derived test cases in the findings"
    )


def test_sst_tester_blast_radius_budget_reconciliation():
    """sst-tester SKILL.md must reconcile blast-radius broadening with session budget."""
    text = _tester_text()
    assert re.search(
        r"(?i)coverage.thinking|within.+budget|priorit\w+.+risk.*budget|budget.*highest.risk",
        text
    ), (
        "sst-tester SKILL.md must reconcile blast-radius broadening with the Phase "
        "49 session budget: broadening is coverage-thinking within the existing budget "
        "(highest-risk adjacent surfaces first), not unbounded testing"
    )


def test_sst_tester_version_bumped_to_at_least_1_7_0():
    """sst-tester must be bumped to at least v1.7.0 to record the blast-radius mandate."""
    text = _tester_text()
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "sst-tester SKILL.md must carry a 'version:' field"
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch) >= (1, 7, 0), (
        f"sst-tester version is {major}.{minor}.{patch}; must be >= 1.7.0 to "
        "record the Phase 51 blast-radius mandate"
    )


# ---------------------------------------------------------------------------
# 51.2 -- ssp-cm-tester inherits mandate + CM-specific heuristics
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SSP_CM_TESTER.exists(), reason="ssp-cm-tester not present")
def test_ssp_cm_tester_base_version_bumped():
    """ssp-cm-tester base-version must be >= 1.7.0 to reflect the mandate sync."""
    text = _cm_tester_text()
    m = re.search(r"^base-version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "ssp-cm-tester SKILL.md must carry a 'base-version:' field"
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch) >= (1, 7, 0), (
        f"ssp-cm-tester base-version is {major}.{minor}.{patch}; must be >= 1.7.0 "
        "so the CM wrapper reflects the Phase 51 blast-radius mandate"
    )


@pytest.mark.skipif(not _SSP_CM_TESTER.exists(), reason="ssp-cm-tester not present")
def test_ssp_cm_tester_heuristic_merged_table_virtualization():
    """ssp-cm-tester must include the merged claims table scroll/virtualization heuristic."""
    text = _cm_tester_text()
    assert re.search(r"(?i)scroll.*virtual|virtual.*scroll|scraped.*row|merged.*table.*scroll", text), (
        "ssp-cm-tester must include CM heuristic: a change touching the merged claims "
        "table -> test scroll/virtualization (scraped rows stay rendered when the "
        "custom block scrolls in)"
    )


@pytest.mark.skipif(not _SSP_CM_TESTER.exists(), reason="ssp-cm-tester not present")
def test_ssp_cm_tester_heuristic_select_all_partitions():
    """ssp-cm-tester must include the select-all across both partitions heuristic."""
    text = _cm_tester_text()
    assert re.search(r"(?i)select.all.*partition|both.*partition.*select|scraped.*custom.*select", text), (
        "ssp-cm-tester must include CM heuristic: test select-all across BOTH scraped "
        "and custom partitions when the merged claims table is touched"
    )


@pytest.mark.skipif(not _SSP_CM_TESTER.exists(), reason="ssp-cm-tester not present")
def test_ssp_cm_tester_heuristic_shared_state_all_clients():
    """ssp-cm-tester must include the AppContext/shared state -> all-clients aggregate heuristic."""
    text = _cm_tester_text()
    assert re.search(r"(?i)AppContext|shared.*client.data|data.fetch.*path", text), (
        "ssp-cm-tester must include CM heuristic: a change touching AppContext/shared "
        "client-data or a data-fetch path"
    )
    assert re.search(r"(?i)all\s+clients.*aggregate|aggregate.*all\s+clients|all.clients.*drop\w*", text), (
        "ssp-cm-tester must include CM heuristic: test Dashboard + Expenses + Reports "
        "for the 'All clients' aggregate AND a specific client AND switch-back"
    )


@pytest.mark.skipif(not _SSP_CM_TESTER.exists(), reason="ssp-cm-tester not present")
def test_ssp_cm_tester_heuristic_client_dropdown_never_disappears():
    """ssp-cm-tester must assert the client dropdown must not disappear."""
    text = _cm_tester_text()
    assert re.search(r"(?i)dropdown.*disappear|client.*dropdown.*not.*disappear|dropdown.*never.*disappear", text), (
        "ssp-cm-tester must include CM heuristic: asserting the client dropdown "
        "never disappears when testing shared state / data-fetch changes"
    )


@pytest.mark.skipif(not _SSP_CM_TESTER.exists(), reason="ssp-cm-tester not present")
def test_ssp_cm_tester_heuristic_legend_swatch_matches_layer():
    """ssp-cm-tester must include the map styling -> legend swatch vs rendered layer heuristic."""
    text = _cm_tester_text()
    assert re.search(r"(?i)legend.*swatch.*match|swatch.*match.*layer|legend.*layer.*match|legend.*rendered", text), (
        "ssp-cm-tester must include CM heuristic: a change touching map styling/CSS "
        "vars -> verify the legend swatch matches the rendered layer"
    )


@pytest.mark.skipif(not _SSP_CM_TESTER.exists(), reason="ssp-cm-tester not present")
def test_ssp_cm_tester_heuristic_report_credit_sanity():
    """ssp-cm-tester must include the report/credit path sanity-check heuristic."""
    text = _cm_tester_text()
    assert re.search(r"(?i)sanity.check.*number|credit.*number|report.*credit.*source|number.*source.*data", text), (
        "ssp-cm-tester must include CM heuristic: a change touching the report/credit "
        "path -> sanity-check the numbers against the source data (not merely that "
        "a report renders)"
    )


@pytest.mark.skipif(not _SSP_CM_TESTER.exists(), reason="ssp-cm-tester not present")
def test_ssp_cm_tester_ssp_sync_checker_clean():
    """check-ssp-sync.py must report ssp-cm-tester specifically as in-sync.
    Uses --skills-dir scoped to the CM skills dir; other pre-existing drift
    in the CM dir is not the responsibility of Phase 51.
    """
    cm_skills_dir = str(_SSP_CM_TESTER.parent.parent)
    result = subprocess.run(
        [sys.executable, str(_REPO / "bin" / "check-ssp-sync.py"),
         "--skills-dir", cm_skills_dir],
        capture_output=True, text=True, cwd=str(_REPO)
    )
    # ssp-cm-tester must appear in the "in sync" line, not the DRIFT list.
    # Other pre-existing drift in the CM skills dir is not Phase 51's scope.
    stdout = result.stdout
    assert "ssp-cm-tester" not in stdout.split("in sync")[0] or "in sync" in stdout, (
        f"check-ssp-sync.py output did not place ssp-cm-tester in the 'in sync' group:\n{stdout}"
    )
    assert re.search(r"in sync.*ssp-cm-tester", stdout), (
        f"ssp-cm-tester must appear in check-ssp-sync.py's 'in sync' list:\n{stdout}"
    )


# ---------------------------------------------------------------------------
# 51.3 -- README.md reflects the broadened tester role
# ---------------------------------------------------------------------------

def test_readme_tester_guidance_floor_language():
    """README.md must state the tester treats dev guidance as a floor, not a ceiling."""
    text = _readme_text()
    assert re.search(r"(?i)floor.*ceiling|floor,\s*not\s*a\s*ceiling|guidance.*floor", text), (
        "README.md must describe the tester as treating dev guidance as a FLOOR "
        "(not a ceiling), reflecting the Phase 51 blast-radius broadening"
    )


def test_readme_tester_blast_radius_or_adjacent():
    """README.md must mention the tester deriving/running its own adjacent cases."""
    text = _readme_text()
    assert re.search(r"(?i)blast.radius|adjacent|derives?.+own|broaden", text), (
        "README.md must describe the tester as also deriving and running its own "
        "adjacent/blast-radius cases beyond the dev's named guidance"
    )


# ---------------------------------------------------------------------------
# 51 -- validate-frontmatter on sst-tester
# ---------------------------------------------------------------------------

def test_validate_frontmatter_clean():
    """bin/validate-frontmatter.py must exit 0 on sst-tester after Phase 51 changes."""
    result = subprocess.run(
        [sys.executable, str(_REPO / "bin" / "validate-frontmatter.py"),
         str(_SST_TESTER)],
        capture_output=True, text=True, cwd=str(_REPO)
    )
    assert result.returncode == 0, (
        f"validate-frontmatter.py failed on sst-tester:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# 51.4 -- standalone blast-radius diff source mode-conditional note
# ---------------------------------------------------------------------------

def test_sst_tester_blast_radius_diff_source_in_chain_git_show_head():
    """sst-tester SKILL.md step 6a must still name git show HEAD as the in-chain diff source."""
    text = _tester_text()
    assert re.search(r"git show HEAD", text), (
        "sst-tester SKILL.md step 6a must name 'git show HEAD' as the diff source "
        "for the in-chain mode blast-radius enumeration"
    )


def test_sst_tester_blast_radius_diff_source_standalone_mode_conditional():
    """sst-tester SKILL.md step 6a must include a mode-conditional note for standalone:
    in standalone mode use git log -p per file, not git show HEAD alone."""
    text = _tester_text()
    assert re.search(r"(?i)standalone.*git\s+log|git\s+log.*standalone", text), (
        "sst-tester SKILL.md step 6a must include a mode-conditional note stating "
        "that in standalone mode the diff source is per-file commit history, not "
        "'git show HEAD' alone"
    )


def test_sst_tester_blast_radius_diff_source_git_log_p():
    """sst-tester SKILL.md must mention 'git log -p' (or git log --follow -p) as the
    per-file diff source for standalone mode."""
    text = _tester_text()
    assert re.search(r"git log.*-p|git log.*--follow", text), (
        "sst-tester SKILL.md must name 'git log -p -- <file>' (or --follow -p) as "
        "the standalone-mode diff source so blast-radius enumeration covers all "
        "commits for each resolved file, not only the HEAD commit"
    )
