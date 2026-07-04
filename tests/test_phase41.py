"""Tests for Phase 41.1 + 41.2: the `sst-tester` transferable + the
tester→reviewer findings contract.

41.1 — `skills/framework/sst-tester/SKILL.md` exists with the right frontmatter
       and documents chain position, authority envelope, lifecycle, degrade/
       self-skip, headed/headless policy, out-of-tree artifacts, and the
       "what changed" derivation. No port literal, no project-specific noun.
41.2 — the findings artifact contract (`tester-findings.{md,json}`) is documented
       in the SKILL body and matched by a sample fixture under tests/fixtures/.
"""
import json
import re
from pathlib import Path

_REPO = Path(__file__).parent.parent
_SST_TESTER = _REPO / "skills/framework/sst-tester/SKILL.md"
_FIXTURE = _REPO / "tests/fixtures/tester-findings.json"


def _frontmatter(text: str) -> dict:
    """Parse the simple `key: value` frontmatter block (top of file)."""
    assert text.startswith("---\n"), "SKILL.md must open with a --- frontmatter fence"
    end = text.index("\n---", 4)
    block = text[4:end]
    fm = {}
    for line in block.splitlines():
        m = re.match(r"^([a-z][a-z0-9-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def _tester_text() -> str:
    assert _SST_TESTER.exists(), f"{_SST_TESTER} must exist (41.1)"
    return _SST_TESTER.read_text()


# ---------------------------------------------------------------------------
# 41.1: file + frontmatter
# ---------------------------------------------------------------------------

def test_sst_tester_file_exists():
    assert _SST_TESTER.exists(), "skills/framework/sst-tester/SKILL.md must exist"


def test_sst_tester_frontmatter():
    fm = _frontmatter(_tester_text())
    assert fm.get("name") == "sst-tester", "name: must be sst-tester"
    # Version advances as the skill gains features (44.1 added standalone mode,
    # bumping past the 1.0.0 initial author); assert a valid major-1 semver, not a pin.
    _v = fm.get("version", "")
    assert re.match(r"^1\.\d+\.\d+$", _v), f"version: must be a major-1 semver, got {_v!r}"
    assert fm.get("model-floor") == "opus", "model-floor: must be opus (Phase 56 tier shift)"
    assert fm.get("effort-floor") == "high", "effort-floor: must be high"
    assert fm.get("user-invocable") == "true", "user-invocable: must be true"
    # Transferable skills never declare a transferable: back-link.
    assert "transferable" not in fm, "transferable skills must not carry a transferable: field"


def test_sst_tester_description_is_block_scalar():
    """41.1: description must be a `description: |` block scalar."""
    text = _tester_text()
    assert re.search(r"^description:\s*\|", text, re.MULTILINE), (
        "description must be a block scalar (description: |)"
    )


# ---------------------------------------------------------------------------
# 41.1: body covers the required contract surfaces
# ---------------------------------------------------------------------------

def test_sst_tester_documents_chain_position():
    text = _tester_text().lower()
    assert "after the dev" in text or "between" in text and "review" in text, (
        "must document its chain position (after the dev skill, before review)"
    )


def test_sst_tester_documents_authority_envelope():
    """D5: never commits, deploys, or edits repo source."""
    text = _tester_text().lower()
    assert "never commit" in text, "must state it never commits"
    assert "never deploy" in text or "does not deploy" in text, "must state it never deploys"


def test_sst_tester_documents_self_skip():
    """D4/D7: self-skip to verdict: skipped when nothing FE/UI is exercisable."""
    text = _tester_text()
    assert "verdict: skipped" in text, "must document the verdict: skipped self-skip record"


def test_sst_tester_documents_degrade_dont_hang():
    """D2: degrade to a finding rather than blocking on interactive login."""
    text = _tester_text().lower()
    assert "degrade" in text, "must document the degrade-don't-hang policy"
    assert "never block" in text or "never hang" in text or "timeout" in text, (
        "must document not hanging (timeout / never-block on interactive login)"
    )


def test_sst_tester_documents_headed_headless():
    """D2: headed when a display exists, headless fallback."""
    text = _tester_text().lower()
    assert "headed" in text and "headless" in text, (
        "must document the headed/headless policy"
    )


def test_sst_tester_documents_out_of_tree_artifacts():
    """D3: zero files under any repo working tree; binary artifacts to a
    non-repo state dir; findings doc to the run-log dir."""
    text = _tester_text()
    assert "~/.claude/state/sst-tester/" in text, (
        "must name the out-of-tree state dir ~/.claude/state/sst-tester/"
    )
    low = text.lower()
    assert "working tree" in low or "repo tree" in low, (
        "must state zero files written under any repo working tree"
    )


def test_sst_tester_documents_what_changed_derivation():
    """41.1: derive 'what changed' from git show HEAD + TODO Just shipped +
    flipped SPEC items."""
    text = _tester_text()
    assert "git show HEAD" in text, "must read git show HEAD to derive what changed"
    assert "Just shipped" in text, "must read docs/TODO.md ## Just shipped"


def test_sst_tester_reads_tester_guidance():
    """D6: reads the dev-authored tester-guidance.md from the run-log dir."""
    assert "tester-guidance.md" in _tester_text(), (
        "must read the dev-authored tester-guidance.md"
    )


# ---------------------------------------------------------------------------
# 41.1: no proprietary leakage (no port literal, no project noun)
# ---------------------------------------------------------------------------

def test_sst_tester_no_port_literals():
    text = _tester_text()
    for port in ("5003", "3000"):
        assert port not in text, f"transferable body must contain no port literal ({port})"


def test_sst_tester_no_project_nouns():
    low = _tester_text().lower()
    for noun in ("claim_management", "claim management", "cm_flask_api", "web/e2e", "dahrouge"):
        assert noun not in low, f"transferable body must not name a project noun ({noun})"


# ---------------------------------------------------------------------------
# 41.2: findings contract documented + matched by the fixture
# ---------------------------------------------------------------------------

def test_sst_tester_documents_findings_files():
    text = _tester_text()
    assert "tester-findings.md" in text, "must document the reviewer-facing tester-findings.md"
    assert "tester-findings.json" in text, "must document the machine-readable tester-findings.json"


def test_sst_tester_documents_record_keys():
    text = _tester_text()
    for key in ("area", "change_ref", "status", "evidence", "recommendation"):
        assert key in text, f"findings per-check record must document the `{key}` key"


def test_sst_tester_documents_status_and_verdict_enums():
    text = _tester_text()
    for status in ("pass", "fail", "needs-change"):
        assert status in text, f"per-check status enum must document `{status}`"
    for verdict in ("green", "red", "degraded", "skipped"):
        assert verdict in text, f"overall verdict enum must document `{verdict}`"


def test_fixture_exists_and_parses():
    assert _FIXTURE.exists(), "tests/fixtures/tester-findings.json must exist (41.2)"
    json.loads(_FIXTURE.read_text())


def test_fixture_has_required_top_level_keys():
    data = json.loads(_FIXTURE.read_text())
    assert "verdict" in data, "fixture must carry a top-level verdict"
    assert data["verdict"] in ("green", "red", "degraded", "skipped"), (
        "verdict must be one of green|red|degraded|skipped"
    )
    assert "summary" in data, "fixture must carry a one-line summary"
    assert isinstance(data.get("checks"), list), "fixture must carry a checks array"
    assert data["checks"], "fixture checks array must be non-empty"


def test_fixture_check_records_have_required_keys():
    data = json.loads(_FIXTURE.read_text())
    required = {"area", "change_ref", "status", "evidence", "recommendation"}
    seen_status = set()
    for check in data["checks"]:
        missing = required - set(check)
        assert not missing, f"check record missing keys: {missing}"
        assert check["status"] in ("pass", "fail", "needs-change"), (
            f"check status must be pass|fail|needs-change, got {check['status']!r}"
        )
        seen_status.add(check["status"])
    # The sample must exercise more than one status so consumers can see the shape.
    assert len(seen_status) >= 2, "fixture should exercise at least two distinct statuses"
