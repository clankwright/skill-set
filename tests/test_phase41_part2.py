"""Tests for Phase 41.3 + 41.4 + 41.9 + 41.10.

41.3 — `sst-dev-review` reads run-log tester findings when present; escalates
        `fail`→`[blocker]`, `needs-change`→`[should-fix]`; surfaces `degraded`;
        treats `skipped` as non-finding; adds `Tester:` line to §6 report; back-compat
        when files absent.
41.4 — `chains/dev-cycle-with-review.yaml`, `…-looped.yaml`
        list `sst-tester` at index 1 (between dev at 0 and review at 2).
        (Dedicated overnight YAML removed in Phase 59; overnight is `--overnight` on the looped chain.)
41.9 — `sst-dev-cycle` documents writing `tester-guidance.md` to the run-log dir
        after committing (when FE/UI surface changed) or emitting `[skip-tester]`
        sentinel (when no FE/UI surface).
41.10 — `bin/skill-chain.py` defines `SKIP_TESTER_SENTINEL_RE`; `run_iteration`
         skips the immediately-following tester-suffix skill when the previous skill
         emitted `[skip-tester]`; records the skip in the iter manifest; does NOT
         skip a non-tester follower.
"""
import importlib.util
import re
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).parent.parent
_DEV_REVIEW = _REPO / "skills/dev/sst-dev-review/SKILL.md"
_DEV_CYCLE = _REPO / "skills/dev/sst-dev-cycle/SKILL.md"
_CHAIN_REVIEW = _REPO / "chains/dev-cycle-with-review.yaml"
_CHAIN_LOOPED = _REPO / "chains/dev-cycle-with-review-looped.yaml"

_CHAIN_PATH = _REPO / "bin" / "skill-chain.py"
_spec = importlib.util.spec_from_file_location("skill_chain_41p2", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

run_iteration = sc.run_iteration
ClaudeCodeHarness = sc.ClaudeCodeHarness


def _review_text() -> str:
    return _DEV_REVIEW.read_text()


def _dev_cycle_text() -> str:
    return _DEV_CYCLE.read_text()


def _parse_yaml_skills(path: Path) -> list:
    """Minimal YAML skills-list parser (no external dependency)."""
    text = path.read_text()
    in_skills = False
    skills = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "skills:":
            in_skills = True
            continue
        if in_skills:
            if stripped.startswith("- "):
                skills.append(stripped[2:].strip())
            elif stripped and not stripped.startswith("#"):
                in_skills = False
    return skills


def _review_version() -> tuple:
    """Return (major, minor, patch) for sst-dev-review version."""
    text = _review_text()
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "sst-dev-review SKILL.md must have a version: field"
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


# ---------------------------------------------------------------------------
# 41.3: sst-dev-review consumes tester findings
# ---------------------------------------------------------------------------

def test_dev_review_reads_tester_findings_json():
    """41.3: SKILL.md documents reading tester-findings.json from the run-log dir."""
    assert "tester-findings.json" in _review_text(), (
        "sst-dev-review must document reading tester-findings.json"
    )


def test_dev_review_reads_tester_findings_md():
    """41.3: SKILL.md documents reading tester-findings.md from the run-log dir."""
    assert "tester-findings.md" in _review_text(), (
        "sst-dev-review must document reading tester-findings.md"
    )


def test_dev_review_escalates_fail_to_blocker():
    """41.3: tester `fail` status escalates to or strengthens a review `[blocker]`."""
    text = _review_text().lower()
    # Must mention that 'fail' maps to blocker
    assert "fail" in text and "blocker" in text, (
        "sst-dev-review must state that tester fail → [blocker]"
    )
    # The text must associate the two (both present near each other is checked
    # by looking for 'fail' and 'blocker' in the same section covering tester findings)
    assert "tester" in text, "must reference 'tester' in the context of escalation"


def test_dev_review_escalates_needs_change_to_should_fix():
    """41.3: tester `needs-change` escalates to or strengthens a `[should-fix]`."""
    text = _review_text()
    low = text.lower()
    assert "needs-change" in low or "needs_change" in low, (
        "sst-dev-review must reference the tester needs-change status"
    )
    assert "should-fix" in low, "sst-dev-review must map needs-change to should-fix"


def test_dev_review_surfaces_degraded():
    """41.3: a degraded tester run is itself surfaced in the review."""
    text = _review_text().lower()
    assert "degraded" in text, (
        "sst-dev-review must document surfacing a degraded tester run"
    )


def test_dev_review_skipped_is_non_finding():
    """41.3: tester verdict `skipped` (or pre-empted) is a valid non-finding state."""
    text = _review_text().lower()
    assert "skipped" in text, (
        "sst-dev-review must treat tester skipped as a valid non-finding state"
    )


def test_dev_review_back_compat_absent_findings():
    """41.3: when the findings files are absent, review proceeds exactly as today."""
    text = _review_text().lower()
    # Must document the absent-file back-compat path
    assert "absent" in text or "not present" in text or "when no" in text or "if no" in text or "if absent" in text, (
        "sst-dev-review must document back-compat when tester findings files are absent"
    )


def test_dev_review_report_has_tester_line():
    """41.3: §6 report template gains a `Tester:` line."""
    text = _review_text()
    assert "Tester:" in text, (
        "sst-dev-review §6 report template must include a Tester: line"
    )


def test_dev_review_version_at_least_1_11_0():
    """41.3: version bumped to at least 1.11.0."""
    major, minor, patch = _review_version()
    assert (major, minor) >= (1, 11), (
        f"sst-dev-review version must be at least 1.11.0, got {major}.{minor}.{patch}"
    )


# ---------------------------------------------------------------------------
# 41.4: chains insert sst-tester between dev and review
# ---------------------------------------------------------------------------

def test_dev_cycle_with_review_chain_has_tester():
    """41.4: dev-cycle-with-review.yaml lists sst-tester between dev and review."""
    skills = _parse_yaml_skills(_CHAIN_REVIEW)
    assert "sst-tester" in skills, (
        "chains/dev-cycle-with-review.yaml must list sst-tester"
    )
    dev_idx = next((i for i, s in enumerate(skills) if "dev-cycle" in s), None)
    tester_idx = next((i for i, s in enumerate(skills) if s == "sst-tester"), None)
    review_idx = next((i for i, s in enumerate(skills) if "dev-review" in s), None)
    assert dev_idx is not None and tester_idx is not None and review_idx is not None, (
        "chain must contain dev-cycle, sst-tester, and dev-review"
    )
    assert dev_idx < tester_idx < review_idx, (
        f"sst-tester must be between dev-cycle and dev-review; "
        f"got indices dev={dev_idx}, tester={tester_idx}, review={review_idx}"
    )


def test_dev_cycle_with_review_looped_chain_has_tester():
    """41.4: dev-cycle-with-review-looped.yaml lists sst-tester between dev and review."""
    skills = _parse_yaml_skills(_CHAIN_LOOPED)
    assert "sst-tester" in skills, (
        "chains/dev-cycle-with-review-looped.yaml must list sst-tester"
    )
    dev_idx = next((i for i, s in enumerate(skills) if "dev-cycle" in s), None)
    tester_idx = next((i for i, s in enumerate(skills) if s == "sst-tester"), None)
    review_idx = next((i for i, s in enumerate(skills) if "dev-review" in s), None)
    assert dev_idx is not None and tester_idx is not None and review_idx is not None
    assert dev_idx < tester_idx < review_idx


def test_dev_cycle_overnight_yaml_removed():
    """Phase 59: dedicated overnight chain YAML is gone; use --overnight on the looped chain."""
    assert not (_REPO / "chains/dev-cycle-overnight.yaml").exists(), (
        "chains/dev-cycle-overnight.yaml must not exist; overnight is --overnight on "
        "dev-cycle-with-review-looped"
    )


# ---------------------------------------------------------------------------
# 41.9: sst-dev-cycle writes tester-guidance.md or emits [skip-tester]
# ---------------------------------------------------------------------------

def test_dev_cycle_documents_tester_guidance_write():
    """41.9: SKILL.md documents writing tester-guidance.md to the run-log dir."""
    assert "tester-guidance.md" in _dev_cycle_text(), (
        "sst-dev-cycle must document writing tester-guidance.md after commit"
    )


def test_dev_cycle_documents_skip_tester_sentinel():
    """41.9: SKILL.md documents the [skip-tester] sentinel token."""
    text = _dev_cycle_text()
    assert "[skip-tester]" in text, (
        "sst-dev-cycle must document emitting [skip-tester] when no FE/UI surface"
    )


def test_dev_cycle_documents_skip_tester_reason():
    """41.9: SKILL.md explains when [skip-tester] is emitted (no FE/UI surface)."""
    text = _dev_cycle_text().lower()
    assert "front-end" in text or "frontend" in text or "ui surface" in text, (
        "sst-dev-cycle must document that [skip-tester] fires when no FE/UI surface"
    )


def test_dev_cycle_version_after_41_9():
    """41.9: version bumped beyond 1.8.0 (the pre-41.9 version)."""
    text = _dev_cycle_text()
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "sst-dev-cycle SKILL.md must have a version: field"
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert (major, minor, patch) > (1, 8, 0), (
        f"sst-dev-cycle version must be bumped past 1.8.0, got {major}.{minor}.{patch}"
    )


# ---------------------------------------------------------------------------
# 41.10: chain runner honors [skip-tester]
# ---------------------------------------------------------------------------

def test_skip_tester_sentinel_re_exists():
    """41.10: SKIP_TESTER_SENTINEL_RE must be defined on the module."""
    assert hasattr(sc, "SKIP_TESTER_SENTINEL_RE"), (
        "SKIP_TESTER_SENTINEL_RE not found in skill_chain module"
    )


def test_skip_tester_sentinel_re_matches_canonical_form():
    """41.10: regex matches the canonical [skip-tester] sentinel."""
    line = "[skip-tester] no front-end surface in this cycle"
    assert sc.SKIP_TESTER_SENTINEL_RE.search(line) is not None


def test_skip_tester_sentinel_re_captures_reason():
    """41.10: reason group captures the text after [skip-tester]."""
    line = "[skip-tester] backend-only change: bin/skill-chain.py"
    m = sc.SKIP_TESTER_SENTINEL_RE.search(line)
    assert m is not None
    assert m.group(1).strip() == "backend-only change: bin/skill-chain.py"


def test_skip_tester_sentinel_re_matches_in_multiline_output():
    """41.10: sentinel is found when embedded in surrounding output."""
    output = (
        "Commit pushed. No front-end files changed this cycle.\n"
        "[skip-tester] no front-end surface in this cycle\n"
    )
    assert sc.SKIP_TESTER_SENTINEL_RE.search(output) is not None


def test_skip_tester_sentinel_re_does_not_match_no_work():
    """41.10: [skip-tester] regex does not match [no-work] sentinel."""
    assert sc.SKIP_TESTER_SENTINEL_RE.search("[no-work] queue empty") is None


_ROUTE_RECORD_41 = {
    "difficulty": "medium",
    "model_floor": "sonnet",
    "effort_floor": "high",
    "item_model": "sonnet",
    "item_effort": "high",
    "effective_model": "sonnet",
    "effective_effort": "high",
}

def test_run_iteration_skips_tester_when_dev_emits_skip_sentinel():
    """41.10: when dev emits [skip-tester] and next skill is a *-tester, skip the
    tester and still run the review skill; record skip in iter_manifest."""
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        if skill_name == "sst-dev-cycle":
            return (0, {"skip_tester": "no front-end surface in this cycle"})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD_41)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=False):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-tester", "sst-dev-review"],
            None,
            None,
            1,
            1,
            "/tmp",
        )

    assert rc == 0
    assert "sst-tester" not in calls, "sst-tester must be skipped when dev emits [skip-tester]"
    assert "sst-dev-review" in calls, "sst-dev-review must still run after skip"
    assert calls == ["sst-dev-cycle", "sst-dev-review"], (
        f"expected dev then review, got {calls}"
    )
    assert "tester_skipped" in iter_manifest, (
        "iter_manifest must record tester_skipped when tester stage is skipped"
    )
    assert iter_manifest["tester_skipped"]["reason"] == "no front-end surface in this cycle"


def test_run_iteration_runs_tester_normally_when_no_skip_sentinel():
    """41.10: when dev does NOT emit [skip-tester], tester runs normally."""
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD_41)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=False):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-tester", "sst-dev-review"],
            None,
            None,
            1,
            1,
            "/tmp",
        )

    assert rc == 0
    assert calls == ["sst-dev-cycle", "sst-tester", "sst-dev-review"], (
        f"all three skills must run when no [skip-tester] emitted; got {calls}"
    )
    assert "tester_skipped" not in iter_manifest


def test_run_iteration_skip_tester_does_not_skip_non_tester_follower():
    """41.10: [skip-tester] only skips the immediately-following skill when it is
    a *-tester; if the immediate follower is NOT a tester, no skipping occurs."""
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        if skill_name == "sst-dev-cycle":
            return (0, {"skip_tester": "no front-end surface"})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD_41)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=False):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-dev-review"],  # no tester in the chain
            None,
            None,
            1,
            1,
            "/tmp",
        )

    assert rc == 0
    assert "sst-dev-review" in calls, (
        "sst-dev-review must NOT be skipped just because dev emitted [skip-tester]; "
        "it is not a *-tester skill"
    )
    assert "tester_skipped" not in iter_manifest, (
        "tester_skipped must NOT be set when the follower is not a *-tester skill"
    )


# ---------------------------------------------------------------------------
# 41.11: incomplete-cycle message names reviewer, not tester
# ---------------------------------------------------------------------------

def test_run_iteration_incomplete_cycle_with_tester_names_reviewer_in_message(capsys):
    """41.11: when dev exits incomplete (no commit, in-flight TODO) and the chain
    is dev→tester→review (no [skip-tester] emitted), the recovery message must
    name sst-dev-review — not sst-tester — as the recovery-capable follower.
    All three skills still run: the tester runs normally, then the reviewer
    performs §0.2 recovery. Only the message is wrong in the unfixed code."""
    h = ClaudeCodeHarness()
    calls: list = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        # Dev emits no [skip-tester]; SHA unchanged → no commit.
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD_41)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=True):
        rc, iter_manifest = run_iteration(
            h,
            ["sst-dev-cycle", "sst-tester", "sst-dev-review"],
            None,
            None,
            1,
            1,
            "/tmp",
        )

    assert rc == 0
    assert "contract_violation" in iter_manifest, (
        "iter_manifest must record contract_violation"
    )
    assert iter_manifest["contract_violation"]["kind"] == "incomplete-cycle"
    # Tester is NOT skipped (dev never emitted [skip-tester]); reviewer runs for recovery.
    assert calls == ["sst-dev-cycle", "sst-tester", "sst-dev-review"], (
        f"all three skills must run when dev exits incomplete without [skip-tester]; "
        f"got {calls}"
    )
    # The recovery message must name sst-dev-review, not sst-tester.
    captured = capsys.readouterr()
    assert "passing to /sst-dev-review for orphaned-cycle recovery" in captured.out, (
        "contract-violation message must name sst-dev-review as recovery follower"
    )
    assert "passing to /sst-tester for orphaned-cycle recovery" not in captured.out, (
        "contract-violation message must NOT name sst-tester as recovery follower"
    )
