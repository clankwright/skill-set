"""Tests for Phase 48: looped standalone tester drain.

48.1 — `templates/TODO.md` has `## Tester sweep targets` section.
       `skills/framework/sst-tester/SKILL.md` documents the looped-standalone
       scope resolver: selects the next target from `## Tester sweep targets`
       in `docs/TODO.md` not yet recorded in the out-of-tree state file.
       Unit test: selector returns the first unrecorded target and None when all
       items are recorded.

48.2 — `sst-tester` SKILL.md documents the `[no-test-work]` sentinel (printed
       when the resolver finds no unrecorded target, without starting a browser
       or the local stack).
       `bin/skill-chain.py`'s loop-abort predicate recognizes `[no-test-work]`
       and breaks the loop: run_iteration records no_test_work_bail and never
       calls the next skill.

48.3 — `sst-tester` SKILL.md has a "Looped standalone drain" subsection
       documenting `bin/skill-chain.py <tester-skill> --loop N`.
       `README.md` Usage section shows that command.
       No example references a removed shim or a per-iter `--phase`.
"""
import importlib.util
import re
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).parent.parent
_SST_TESTER = _REPO / "skills/framework/sst-tester/SKILL.md"
_TEMPLATES_TODO = _REPO / "templates/TODO.md"
_README = _REPO / "README.md"

_CHAIN_PATH = _REPO / "bin" / "skill-chain.py"
_sc_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_sc_spec)
_sc_spec.loader.exec_module(sc)

ClaudeCodeHarness = sc.ClaudeCodeHarness


def _tester_text() -> str:
    assert _SST_TESTER.exists(), f"{_SST_TESTER} must exist"
    return _SST_TESTER.read_text()


# ---------------------------------------------------------------------------
# 48.1: draining selector unit tests (executable form of the 48.1 algorithm)
# ---------------------------------------------------------------------------

def _make_targets_block(items: list) -> str:
    """Build a `## Tester sweep targets` block for fixture use."""
    lines = ["## Tester sweep targets", ""]
    for item in items:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _resolve_next_target(todo_text: str, already_exercised: set):
    """Executable form of the 48.1 draining selector.

    Parses `## Tester sweep targets` from todo_text, skips items whose key
    (the item text stripped of the leading `- `) appears in already_exercised,
    and returns the first unrecorded key.  Returns None when the section is
    absent, empty, or all items are already recorded.
    """
    m = re.search(r"^##\s+Tester sweep targets\b", todo_text, re.MULTILINE)
    if not m:
        return None
    tail = todo_text[m.end():]
    next_heading = re.search(r"^##\s+", tail, re.MULTILINE)
    section_text = tail[: next_heading.start()] if next_heading else tail
    for line in section_text.splitlines():
        if not line.startswith("- "):
            continue
        key = line[2:].strip()
        if key not in already_exercised:
            return key
    return None


def test_selector_picks_first_unrecorded_target():
    """Selector returns the first item not in already_exercised (K=3, J=1)."""
    items = ["[P1] Login flow GAP", "[P2] Allocation UI partial", "[P3] CSV upload covered"]
    todo_text = _make_targets_block(items)
    already = {"[P1] Login flow GAP"}
    result = _resolve_next_target(todo_text, already)
    assert result == "[P2] Allocation UI partial", result


def test_selector_returns_none_when_all_recorded():
    """Selector returns None when all K items are in already_exercised (K=J=2)."""
    items = ["[P1] Login flow GAP", "[P2] Allocation UI partial"]
    todo_text = _make_targets_block(items)
    already = {"[P1] Login flow GAP", "[P2] Allocation UI partial"}
    result = _resolve_next_target(todo_text, already)
    assert result is None, result


def test_selector_returns_none_on_absent_section():
    """Selector returns None when there is no `## Tester sweep targets` section."""
    result = _resolve_next_target("## Next up\n- some item\n", set())
    assert result is None


def test_selector_picks_first_when_none_recorded():
    """With an empty exercised set the selector returns the first item."""
    items = ["[P1] Login flow GAP", "[P2] Allocation UI partial"]
    todo_text = _make_targets_block(items)
    result = _resolve_next_target(todo_text, set())
    assert result == "[P1] Login flow GAP", result


# ---------------------------------------------------------------------------
# 48.1: templates/TODO.md and SKILL.md prose requirements
# ---------------------------------------------------------------------------

def test_templates_todo_has_tester_sweep_targets_section():
    """templates/TODO.md must contain a `## Tester sweep targets` section."""
    text = _TEMPLATES_TODO.read_text()
    assert "## Tester sweep targets" in text, \
        "templates/TODO.md must have a ## Tester sweep targets section"


def test_tester_skill_documents_tester_sweep_targets_queue():
    """sst-tester SKILL.md must document the ## Tester sweep targets queue."""
    text = _tester_text()
    assert "Tester sweep targets" in text, \
        "sst-tester SKILL.md must document the ## Tester sweep targets queue format"


def test_tester_skill_documents_out_of_tree_exercised_state():
    """sst-tester SKILL.md documents the out-of-tree exercised-state tracking."""
    text = _tester_text()
    assert "exercised" in text.lower(), \
        "sst-tester SKILL.md must document exercised-state tracking"
    assert "~/.claude/state/sst-tester/" in text, \
        "exercised-state must be under the out-of-tree state dir"


# ---------------------------------------------------------------------------
# 48.2: NO_TEST_WORK_SENTINEL_RE in skill-chain.py
# ---------------------------------------------------------------------------

def test_no_test_work_sentinel_re_exists():
    """skill-chain.py must define NO_TEST_WORK_SENTINEL_RE."""
    assert hasattr(sc, "NO_TEST_WORK_SENTINEL_RE"), \
        "bin/skill-chain.py must define NO_TEST_WORK_SENTINEL_RE"


def test_no_test_work_sentinel_re_matches_basic():
    """NO_TEST_WORK_SENTINEL_RE matches the bare sentinel with a reason."""
    assert sc.NO_TEST_WORK_SENTINEL_RE.search(
        "[no-test-work] queue drained"
    ) is not None


def test_no_test_work_sentinel_re_captures_reason():
    """NO_TEST_WORK_SENTINEL_RE captures the reason text in group(1)."""
    m = sc.NO_TEST_WORK_SENTINEL_RE.search(
        "[no-test-work] no Tester sweep targets section"
    )
    assert m is not None
    assert "no Tester sweep targets section" in (m.group(1) or "")


def test_no_test_work_sentinel_re_matches_in_multiline_output():
    """NO_TEST_WORK_SENTINEL_RE is found when embedded in surrounding output."""
    output = (
        "Reading docs/TODO.md; ## Tester sweep targets section found.\n"
        "All 3 items already recorded in the exercised-state file.\n"
        "[no-test-work] queue drained; 3/3 targets exercised this run\n"
        "Exiting cleanly.\n"
    )
    assert sc.NO_TEST_WORK_SENTINEL_RE.search(output) is not None


def test_no_test_work_does_not_match_no_work():
    """NO_TEST_WORK_SENTINEL_RE must not accidentally match [no-work]."""
    assert sc.NO_TEST_WORK_SENTINEL_RE.search("[no-work] queue empty") is None


def test_no_work_sentinel_does_not_match_no_test_work():
    """Existing NO_WORK_SENTINEL_RE must not match [no-test-work]."""
    assert sc.NO_WORK_SENTINEL_RE.search("[no-test-work] queue drained") is None


_ROUTE_RECORD_48 = {
    "difficulty": "medium",
    "model_floor": "sonnet",
    "effort_floor": "high",
    "item_model": "sonnet",
    "item_effort": "high",
    "effective_model": "sonnet",
    "effective_effort": "high",
}


def test_run_iteration_no_test_work_bail_skips_remaining_skills():
    """run_iteration aborts after the tester fires [no-test-work].

    The tester returns no_test_work_bail; sst-dev-review must never be called;
    rc must be 0; iter_manifest must record no_test_work_bail with the bailing
    skill name and reason.
    """
    h = ClaudeCodeHarness()
    calls = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kwargs):
        calls.append(skill_name)
        if skill_name == "sst-tester":
            return (0, {"no_test_work_bail": "queue drained; 3/3 targets exercised"})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", _ROUTE_RECORD_48)), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"):
        rc, iter_manifest = sc.run_iteration(
            h,
            ["sst-tester", "sst-dev-review"],
            None,
            None,
            1,
            1,
            "/tmp",
        )

    assert rc == 0, "no-test-work bail must be a clean exit (rc=0)"
    assert "no_test_work_bail" in iter_manifest, \
        "iter_manifest must record no_test_work_bail after the bail"
    assert iter_manifest["no_test_work_bail"]["skill"] == "sst-tester"
    assert iter_manifest["no_test_work_bail"]["reason"] == "queue drained; 3/3 targets exercised"
    assert calls == ["sst-tester"], \
        "sst-dev-review must NOT be called after a no-test-work bail"


def test_no_work_bail_unchanged_after_48_addition():
    """Existing [no-work] bail still fires correctly after the 48.2 addition."""
    assert hasattr(sc, "NO_WORK_SENTINEL_RE")
    assert sc.NO_WORK_SENTINEL_RE.search(
        "[no-work] queue empty and spec fully checked; nothing to do"
    ) is not None


# ---------------------------------------------------------------------------
# 48.2: sst-tester SKILL.md prose requirements for [no-test-work]
# ---------------------------------------------------------------------------

def test_tester_documents_no_test_work_sentinel():
    """sst-tester SKILL.md must document the [no-test-work] sentinel."""
    text = _tester_text()
    assert "[no-test-work]" in text, \
        "sst-tester SKILL.md must document the [no-test-work] sentinel"


def test_tester_documents_no_stack_browser_on_no_test_work():
    """sst-tester SKILL.md must say no browser/stack starts on [no-test-work]."""
    text = _tester_text().lower()
    assert "no-test-work" in text
    assert (
        "without starting" in text
        or "no browser" in text
        or "spawns no" in text
        or "never start" in text
        or "exits 0 without" in text
    ), "sst-tester SKILL.md must document that [no-test-work] exits without starting the browser or local stack"


# ---------------------------------------------------------------------------
# 48.3: SKILL.md looped-standalone drain subsection + README example
# ---------------------------------------------------------------------------

def test_tester_skill_md_has_looped_standalone_drain_subsection():
    """sst-tester SKILL.md must have a looped-standalone drain subsection."""
    text = _tester_text().lower()
    assert "looped" in text and "standalone" in text and "drain" in text, \
        "sst-tester SKILL.md must have a looped-standalone drain subsection"


def test_tester_skill_md_documents_loop_n_command():
    """sst-tester SKILL.md must document `bin/skill-chain.py <tester> --loop N`."""
    text = _tester_text()
    assert "bin/skill-chain.py" in text and "--loop" in text, \
        "sst-tester SKILL.md must show the `bin/skill-chain.py <tester> --loop N` command"


def test_tester_skill_md_no_per_iter_phase_in_drain_section():
    """The `## Looped standalone drain` section must not instruct per-iter --phase use."""
    text = _tester_text()
    # Find the actual ## heading, not a forward-reference mention of it.
    heading_idx = text.find("## Looped standalone drain")
    if heading_idx == -1:
        return
    # Read the drain section up to the next ## heading.
    tail = text[heading_idx + len("## Looped standalone drain"):]
    next_heading = re.search(r"^##\s+", tail, re.MULTILINE)
    drain_section = tail[: next_heading.start()] if next_heading else tail
    assert "--phase" not in drain_section, \
        "## Looped standalone drain section must not tell users to pass --phase per iteration"


def test_readme_has_looped_tester_example():
    """README.md Usage section must show `bin/skill-chain.py <tester> --loop N`."""
    text = _README.read_text()
    usage_start = text.find("## Usage")
    assert usage_start != -1, "README must have a ## Usage section"
    usage_text = text[usage_start:]
    assert "skill-chain.py" in usage_text and "--loop" in usage_text, \
        "README Usage section must reference skill-chain.py --loop"
    assert "tester" in usage_text.lower(), \
        "README Usage section must mention tester in the looped example"


def test_readme_looped_tester_no_removed_shim():
    """The looped tester example in README must not reference removed shims."""
    text = _README.read_text()
    usage_start = text.find("## Usage")
    usage_text = text[usage_start:] if usage_start != -1 else text
    for shim in ("drive-chain.py", "skill-batch.py"):
        assert shim not in usage_text, \
            f"README Usage must not reference removed shim {shim}"


def test_tester_version_bumped_for_looped_standalone():
    """sst-tester version must be bumped to at least 1.2.0 for Phase 48."""
    text = _tester_text()
    assert text.startswith("---\n")
    end = text.index("\n---", 4)
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([a-z][a-z0-9-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    version = fm.get("version", "0.0.0")
    parts = version.split(".")
    assert (
        len(parts) == 3
        and parts[0] == "1"
        and int(parts[1]) >= 2
    ), f"sst-tester version must be at least 1.2.0 after Phase 48 (got {version})"


# ---------------------------------------------------------------------------
# 48.4: D1 dispatch discriminator (in-chain guard) + stale line 132 fix
# ---------------------------------------------------------------------------

def test_d1_dispatch_includes_in_chain_discriminator():
    """D1 mode-select paragraph must include the tester-guidance.md in-chain guard.

    A project that has a `## Tester sweep targets` queue AND runs the tester
    in-chain (with tester-guidance.md present from the dev skill) must NOT enter
    looped-standalone mode.  The fix adds the discriminator to line 62's rule:
    'queue present AND no tester-guidance.md from the preceding dev skill'.
    """
    text = _tester_text()
    # The D1 mode-selection paragraph is the one that starts with
    # "The presence of `--phase` or `--todos`".
    assert "tester-guidance.md" in text, (
        "D1 dispatch paragraph must reference tester-guidance.md as the in-chain discriminator"
    )
    # The looped-standalone trigger condition must mention the in-chain guard,
    # not just "queue present".
    d1_para_match = re.search(
        r"The presence of `--phase`.*?(?=\n\n|\Z)", text, re.DOTALL
    )
    assert d1_para_match is not None, "D1 dispatch paragraph not found"
    d1_para = d1_para_match.group(0)
    assert "tester-guidance.md" in d1_para, (
        "D1 dispatch paragraph must reference tester-guidance.md to discriminate "
        "in-chain from looped-standalone when a queue is present"
    )


def test_standalone_arg_surface_d1_updated_for_third_mode():
    """Standalone-mode D1 paragraph must not claim 'in-chain (default) exactly as before'.

    Phase 48 added looped-standalone as a third mode, so 'with neither flag the
    skill runs in-chain (default) exactly as before' is now stale and must be
    replaced with text that acknowledges the third mode.
    """
    text = _tester_text()
    # The stale phrase must no longer appear verbatim.
    stale_phrase = "runs in-chain (default) exactly as before"
    assert stale_phrase not in text, (
        f"Stale phrase '{stale_phrase}' must be removed from standalone D1 paragraph; "
        "replace it with text acknowledging looped-standalone as the third mode"
    )
