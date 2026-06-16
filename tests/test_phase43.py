"""Tests for Phase 43: stop the dev cycle halting before commit.

Covers:
- 43.1 close the sanitize→commit seam in `sst-dev-cycle` §5 (sanitize gate runs
  during implementation, before the §4 verify gate; commit is the final action).
- 43.2 close the same seam in `sst-dev-review §0.2` recovery (sanitize gate runs
  before staging, not immediately before the recovery commit).
- 43.3 recovery-first commit in `sst-dev-review` (health predicate documented).
- 43.4 relax the runner's `contract_violation` kill (no abort when the
  reviewer/recovery follower advanced HEAD).
- 43.5 regression grep-guard that fails if either skill re-introduces a sanitize
  `/skill` invocation as the step immediately before commit.
"""
import importlib.util
import re
from pathlib import Path

_REPO = Path(__file__).parent.parent
_DEV_CYCLE = _REPO / "skills/dev/sst-dev-cycle/SKILL.md"
_DEV_REVIEW = _REPO / "skills/dev/sst-dev-review/SKILL.md"
_CHAIN_PATH = _REPO / "bin" / "skill-chain.py"

_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

run_iteration = sc.run_iteration


def _ver(text: str):
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "frontmatter must contain a version: field"
    return tuple(int(x) for x in m.groups())


# ---------------------------------------------------------------------------
# 43.1: sst-dev-cycle version + seam fix
# ---------------------------------------------------------------------------

def test_dev_cycle_version_bumped():
    """43.1: sst-dev-cycle version must be >= 1.8.0 after the seam fix."""
    assert _ver(_DEV_CYCLE.read_text()) >= (1, 8, 0), (
        "sst-dev-cycle version must be bumped to >= 1.8.0 for the Phase 43 seam fix"
    )


def test_dev_cycle_sanitize_before_verify_gate():
    """43.1/43.5: the `/sst-sanitize-transferable` invocation must appear before
    the §4 verify gate — i.e. the sanitize scan runs right after the transferable
    edit, not as the last `/skill` step wedged between test-green and the commit.
    """
    text = _DEV_CYCLE.read_text()
    i_san = text.find("/sst-sanitize-transferable")
    i_verify = text.find("## 4. Verify")
    assert i_san != -1, "sst-dev-cycle must still invoke /sst-sanitize-transferable"
    assert i_verify != -1, "sst-dev-cycle must retain its §4 Verify section"
    assert i_san < i_verify, (
        "the sanitize gate must be invoked before §4 Verify (right after the "
        "transferable edit), not as the last /skill step before commit"
    )


def test_dev_cycle_no_sanitize_invocation_in_commit_region():
    """43.1/43.5: no `/sst-sanitize-transferable` invocation may sit between the
    §6 spec-update section and the §7 commit — that region is the seam the bug
    lived in, and the commit must be the final action with no sub-skill return
    immediately preceding it.
    """
    text = _DEV_CYCLE.read_text()
    i_six = text.find("## 6. Update the spec")
    assert i_six != -1, "sst-dev-cycle must retain its §6 section"
    assert "/sst-sanitize-transferable" not in text[i_six:], (
        "no sanitize /skill invocation may appear from §6 onward (the spec-update "
        "→ commit region); the gate runs earlier, during implementation"
    )


def test_dev_cycle_commit_documented_as_final_action():
    """43.1: §7 must document the commit + push as the skill's final action."""
    text = _DEV_CYCLE.read_text()
    assert "final action" in text, (
        "§7 must state that git commit + push is the skill's final action with no "
        "/skill sub-invocation between test-green and the commit"
    )


# ---------------------------------------------------------------------------
# 43.2 / 43.3: sst-dev-review version + recovery seam fix + recovery-first
# ---------------------------------------------------------------------------

def test_dev_review_version_bumped():
    """43.2/43.3: sst-dev-review version must be >= 1.10.0."""
    assert _ver(_DEV_REVIEW.read_text()) >= (1, 10, 0), (
        "sst-dev-review version must be bumped to >= 1.10.0 for Phase 43"
    )


def test_dev_review_recovery_sanitize_before_stage():
    """43.2/43.5: in §0.2 recovery, the `/sst-sanitize-transferable` gate must run
    BEFORE the 'Stage all changed files' step — so the sanitize sub-skill is not
    the step immediately before the recovery commit.
    """
    text = _DEV_REVIEW.read_text()
    i_san = text.find("/sst-sanitize-transferable")
    i_stage = text.find("Stage all changed files")
    assert i_san != -1, "§0.2 recovery must still invoke /sst-sanitize-transferable"
    assert i_stage != -1, "§0.2 recovery must retain its stage step"
    assert i_san < i_stage, (
        "the recovery sanitize gate must run before staging (and thus before the "
        "recovery commit), not immediately before the commit"
    )


def test_dev_review_documents_recovery_first_health_predicate():
    """43.3: §0.2 must document the recovery-first health predicate — the five
    signals that mark an incomplete-but-healthy dev cycle the reviewer commits at
    the START of its turn, before the review pass.
    """
    text = _DEV_REVIEW.read_text()
    for token in ["dirty tree", "In-flight", "HEAD unchanged", "tests green", "sanitize clean"]:
        assert token in text, (
            f"§0.2 must document the '{token}' signal of the recovery-first health "
            "predicate (dirty tree + In-flight line + HEAD unchanged + tests green "
            "+ sanitize clean)"
        )


def test_dev_review_documents_recover_then_review_order():
    """43.3: §0.2 must state the order — recover (commit) FIRST, then review."""
    text = _DEV_REVIEW.read_text().lower()
    assert "recover" in text and "before the review pass" in text, (
        "§0.2 must document that recovery (the recovery commit) happens before the "
        "review pass (recover, then review)"
    )


# ---------------------------------------------------------------------------
# 43.4: relax the runner's contract_violation kill
# ---------------------------------------------------------------------------

def test_contract_violation_aborts_when_head_unchanged():
    """43.4: a recorded violation aborts when HEAD did not advance (no recovery)."""
    im = {
        "contract_violation": {
            "kind": "incomplete-cycle",
            "skill": "sst-dev-cycle",
            "head_at_violation": "abc1234",
        },
        "git_sha_after": "abc1234",
    }
    assert sc._contract_violation_aborts(im) is True


def test_contract_violation_no_abort_when_follower_advanced_head():
    """43.4: a recovered cycle (follower committed → HEAD advanced) does NOT abort."""
    im = {
        "contract_violation": {
            "kind": "incomplete-cycle",
            "skill": "sst-dev-cycle",
            "head_at_violation": "abc1234",
        },
        "git_sha_after": "def5678",
    }
    assert sc._contract_violation_aborts(im) is False


def test_contract_violation_no_abort_when_no_violation_recorded():
    """43.4: no contract_violation recorded → never aborts on this path."""
    assert sc._contract_violation_aborts({}) is False
    assert sc._contract_violation_aborts({"git_sha_after": "abc1234"}) is False


def test_contract_violation_aborts_when_violation_sha_missing():
    """43.4: when the violation SHA is unavailable we cannot prove recovery, so
    abort conservatively (preserves the no-git-harness / unknown-state behavior).
    """
    im = {
        "contract_violation": {"kind": "incomplete-cycle", "skill": "sst-dev-cycle"},
        "git_sha_after": "def5678",
    }
    assert sc._contract_violation_aborts(im) is True


def test_run_iteration_records_head_at_violation():
    """43.4: run_iteration must stamp head_at_violation on the violation record so
    the loop-level abort check can tell whether a follower later advanced HEAD.
    """
    import unittest.mock as mock

    h = sc.ClaudeCodeHarness()

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        return (0, {})

    _ROUTE = {
        "difficulty": "medium",
        "model_floor": "sonnet",
        "effort_floor": "high",
        "item_model": "sonnet",
        "item_effort": "high",
        "effective_model": "sonnet",
        "effective_effort": "high",
    }
    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=True):
        _rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-dev-review"],
            None,
            None,
            1,
            1,
            "/tmp",
        )

    assert "contract_violation" in iter_manifest
    assert iter_manifest["contract_violation"].get("head_at_violation") == "abc1234", (
        "run_iteration must record the dev skill's HEAD SHA on the violation so the "
        "loop can detect a later follower-recovery commit"
    )
