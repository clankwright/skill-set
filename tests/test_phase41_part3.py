"""Tests for Phase 41.7 + 41.8.

41.7 — Codify clean-exit and artifact-hygiene invariants in both SKILL bodies:
        (a) zero files written under any repo working tree (git status --porcelain clean);
        (b) guaranteed teardown via finally/trap even on exception/timeout;
        (c) no orphan processes or listeners on the documented ports after teardown.
        Fixture walkthrough asserts evidence paths are out-of-tree.

41.8 — Wire tooling, install, and docs:
        bin/install-skills.sh --list-new surfaces sst-tester;
        README.md describes the dev→tester→review chain order and floor table;
        CLAUDE.md updated for the inserted tester stage.
"""
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent
_SST_TESTER = _REPO / "skills/framework/sst-tester/SKILL.md"
_README = _REPO / "README.md"
_FIXTURE = _REPO / "tests/fixtures/tester-findings.json"
_INSTALL_SCRIPT = _REPO / "bin/install-skills.sh"


def _sst_text() -> str:
    return _SST_TESTER.read_text()


# ---------------------------------------------------------------------------
# 41.7: sst-tester artifact-hygiene documentation
# ---------------------------------------------------------------------------

def test_sst_tester_documents_zero_files_under_repo_working_tree():
    """41.7: SKILL.md must assert zero files written under any repo working tree."""
    text = _sst_text()
    assert "Zero files under any repo working tree" in text, (
        "sst-tester must state 'Zero files under any repo working tree'"
    )


def test_sst_tester_documents_git_status_porcelain():
    """41.7: SKILL.md must document that git status --porcelain is empty after a run."""
    text = _sst_text()
    assert "git status --porcelain" in text, (
        "sst-tester must document 'git status --porcelain' as the post-run clean check"
    )


def test_sst_tester_documents_out_of_tree_artifact_dir():
    """41.7: SKILL.md must document the out-of-tree artifact dir."""
    text = _sst_text()
    assert "~/.claude/state/sst-tester/" in text, (
        "sst-tester must document the out-of-tree artifact dir ~/.claude/state/sst-tester/"
    )


# ---------------------------------------------------------------------------
# 41.7: sst-tester guaranteed teardown
# ---------------------------------------------------------------------------

def test_sst_tester_documents_finally_trap_teardown():
    """41.7: SKILL.md must document a finally/trap guaranteed-teardown path."""
    text = _sst_text()
    assert "finally" in text or "trap" in text, (
        "sst-tester must document a finally/trap guaranteed-teardown path"
    )


def test_sst_tester_teardown_confirms_ports_free():
    """41.7: Teardown section must state that documented ports have no remaining listener."""
    text = _sst_text()
    assert "no remaining listener" in text or "ports have no remaining" in text, (
        "sst-tester teardown must confirm documented ports have no remaining listener"
    )


def test_sst_tester_documents_no_orphan_processes():
    """41.7: SKILL.md must state that no orphan server/browser processes survive teardown."""
    text = _sst_text()
    assert "orphan" in text.lower(), (
        "sst-tester must document that no orphan processes survive after teardown"
    )


# ---------------------------------------------------------------------------
# 41.7: fixture evidence paths are out of tree
# ---------------------------------------------------------------------------

def test_tester_findings_fixture_evidence_paths_out_of_tree():
    """41.7: all non-empty evidence paths in tester-findings.json must be out-of-tree
    (under ~/.claude/state/sst-tester/), never a repo-relative or absolute repo path."""
    data = json.loads(_FIXTURE.read_text())
    for check in data.get("checks", []):
        evidence = check.get("evidence", "")
        if not evidence:
            continue
        assert evidence.startswith("~/.claude/state/sst-tester/"), (
            f"evidence path must be under ~/.claude/state/sst-tester/, got: {evidence!r}"
        )


# ---------------------------------------------------------------------------
# 41.8: install-skills.sh --list-new surfaces sst-tester
# ---------------------------------------------------------------------------

def test_install_skills_lists_sst_tester_as_new(tmp_path):
    """41.8: bin/install-skills.sh --list-new (with empty temp target) must list sst-tester."""
    result = subprocess.run(
        [
            "bash", str(_INSTALL_SCRIPT),
            "--list-new",
            "--target", str(tmp_path / "skills"),
        ],
        capture_output=True,
        text=True,
        env={**os.environ},
        cwd=str(_REPO),
    )
    assert result.returncode == 0, (
        f"install-skills.sh --list-new failed (rc={result.returncode}):\n{result.stderr}"
    )
    assert "sst-tester" in result.stdout, (
        f"install-skills.sh --list-new must list sst-tester; got:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# 41.8: README.md describes dev→tester→review chain order
# ---------------------------------------------------------------------------

def test_readme_mentions_sst_tester():
    """41.8: README.md must mention sst-tester (the inserted chain stage)."""
    text = _README.read_text()
    assert "sst-tester" in text, (
        "README.md must mention sst-tester (the inserted chain stage)"
    )


def test_readme_describes_dev_tester_review_chain_order():
    """41.8: README.md must describe the dev→tester→review stage ordering."""
    text = _README.read_text()
    # Accept 'dev → tester' or 'tester →' or 'between dev and review' etc.
    assert "→ tester" in text or "tester →" in text or (
        re.search(r"tester.{0,40}(between|review)", text) is not None
    ), (
        "README.md must describe the dev→tester→review ordering of the chain"
    )


def test_readme_model_tier_table_includes_sst_tester():
    """41.8: README.md model-tier floor table must list sst-tester."""
    text = _README.read_text()
    # sst-tester must appear in a floor-table row (between | pipes)
    # Check it's in a table context near floor keywords
    assert "sst-tester" in text, (
        "README.md model-tier floor table must include sst-tester"
    )
    # More specifically: it should be on a line with pipe chars (table row)
    for line in text.splitlines():
        if "sst-tester" in line and "|" in line:
            break
    else:
        pytest.fail(
            "sst-tester must appear in a markdown table row in README.md "
            "(model-tier floor table)"
        )
