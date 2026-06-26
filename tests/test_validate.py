"""Tests for bin/validate-frontmatter.py HUMAN.md validation (SPEC 31.9)."""
import importlib.util
from pathlib import Path

_VAL_PATH = Path(__file__).parent.parent / "bin" / "validate-frontmatter.py"
_spec = importlib.util.spec_from_file_location("validate_frontmatter", _VAL_PATH)
vf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vf)

_FIVE_SECTIONS = "## Blocking\n\n## High\n\n## Medium\n\n## Low\n\n## Done\n"


def _write_human_md(tmp_path: Path, content: str) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    p = docs / "HUMAN.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_validate_human_md_function_exists():
    """validate_human_md must be defined on the module (Phase 31.9)."""
    assert hasattr(vf, "validate_human_md"), \
        "validate_human_md not found in validate_frontmatter module"


def test_human_md_absent_returns_no_errors(tmp_path):
    """No errors when docs/HUMAN.md does not exist."""
    errors = vf.validate_human_md(tmp_path / "docs" / "HUMAN.md")
    assert errors == []


def test_human_md_valid_minimal_passes(tmp_path):
    """A valid HUMAN.md with all five sections and a proper open item passes."""
    content = (
        "# Project HUMAN-action backlog\n\n"
        "## Blocking\n\n"
        "- [ ] H3.1 [easy] **Set DB secrets**\n"
        "  Body text.\n"
        "  Blocks: 3.1\n"
        "  Filed by: sst-supervisor at 2026-05-22T00:00:00Z.\n"
        "  Source: test.\n\n"
        "## High\n\n## Medium\n\n## Low\n\n## Done\n"
    )
    p = _write_human_md(tmp_path, content)
    errors = vf.validate_human_md(p)
    assert errors == [], f"Unexpected errors: {errors}"


def test_human_md_missing_done_section_reports_error(tmp_path):
    """Missing ## Done section triggers an error."""
    content = (
        "# Project HUMAN-action backlog\n\n"
        "## Blocking\n\n## High\n\n## Medium\n\n## Low\n"
    )
    p = _write_human_md(tmp_path, content)
    errors = vf.validate_human_md(p)
    assert any("Done" in e for e in errors), f"Expected 'Done' error, got: {errors}"


def test_human_md_missing_blocking_section_reports_error(tmp_path):
    """Missing ## Blocking section triggers an error."""
    content = (
        "# Project HUMAN-action backlog\n\n"
        "## High\n\n## Medium\n\n## Low\n\n## Done\n"
    )
    p = _write_human_md(tmp_path, content)
    errors = vf.validate_human_md(p)
    assert any("Blocking" in e for e in errors), f"Expected 'Blocking' error, got: {errors}"


def test_human_md_bad_id_format_reports_error(tmp_path):
    """H-ID not matching ^H\\d+\\.\\d+$ triggers an error."""
    content = (
        "# Project HUMAN-action backlog\n\n"
        "## Blocking\n\n"
        "- [ ] H3 [easy] **Bad ID**\n"
        "  Body.\n"
        "  Blocks: 3.1\n"
        "  Filed by: sst-supervisor at 2026-05-22T00:00:00Z.\n"
        "  Source: test.\n\n"
        "## High\n\n## Medium\n\n## Low\n\n## Done\n"
    )
    p = _write_human_md(tmp_path, content)
    errors = vf.validate_human_md(p)
    assert any("H3" in e or "ID" in e for e in errors), f"Expected ID error, got: {errors}"


def test_human_md_open_item_without_blocks_reports_error(tmp_path):
    """Open [ ] item without a Blocks: line triggers an error."""
    content = (
        "# Project HUMAN-action backlog\n\n"
        "## Blocking\n\n"
        "- [ ] H3.1 [easy] **Missing Blocks**\n"
        "  Body.\n"
        "  Filed by: sst-supervisor at 2026-05-22T00:00:00Z.\n"
        "  Source: test.\n\n"
        "## High\n\n## Medium\n\n## Low\n\n## Done\n"
    )
    p = _write_human_md(tmp_path, content)
    errors = vf.validate_human_md(p)
    assert any("Blocks" in e for e in errors), f"Expected Blocks error, got: {errors}"


def test_human_md_closed_item_no_blocks_required(tmp_path):
    """Closed [x] items do not require a Blocks: line."""
    content = (
        "# Project HUMAN-action backlog\n\n"
        "## Blocking\n\n## High\n\n## Medium\n\n## Low\n\n"
        "## Done\n\n"
        "- [x] H2.1 [easy] **Old item** (verified 2026-05-01T00:00:00Z)\n"
        "  Body.\n"
        "  Filed by: sst-supervisor at 2026-05-01T00:00:00Z.\n"
        "  Source: test.\n"
    )
    p = _write_human_md(tmp_path, content)
    errors = vf.validate_human_md(p)
    assert errors == [], f"Unexpected errors for closed item: {errors}"


def test_human_md_sections_must_be_in_canonical_order(tmp_path):
    """Sections in wrong order triggers an error."""
    content = (
        "# Project HUMAN-action backlog\n\n"
        "## High\n\n## Blocking\n\n## Medium\n\n## Low\n\n## Done\n"
    )
    p = _write_human_md(tmp_path, content)
    errors = vf.validate_human_md(p)
    assert any("order" in e.lower() or "Blocking" in e for e in errors), \
        f"Expected order error, got: {errors}"


# ---------------------------------------------------------------------------
# validate_spec_item_quality tests (SPEC 38.2)
# ---------------------------------------------------------------------------

def _write_spec_todo(
    tmp_path: Path, spec_content: str = "", todo_content: str = ""
) -> tuple[Path, Path]:
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    sp = docs / "SPEC.md"
    sp.write_text(spec_content, encoding="utf-8")
    tp = docs / "TODO.md"
    tp.write_text(todo_content, encoding="utf-8")
    return sp, tp


def test_validate_spec_item_quality_function_exists():
    """validate_spec_item_quality must be defined on the module (SPEC 38.2)."""
    assert hasattr(vf, "validate_spec_item_quality"), (
        "validate_spec_item_quality not found in validate_frontmatter module"
    )


def test_vague_bullet_without_concrete_target_fails(tmp_path):
    """(a) Bullet with open-ended marker and no concrete target fails."""
    sp, tp = _write_spec_todo(
        tmp_path,
        spec_content=(
            "### Phase 99\n\n"
            "- [ ] 99.1 [medium] iterative cleanup of all components\n"
        ),
    )
    errors = vf.validate_spec_item_quality(sp, tp)
    assert errors, "Expected at least one error for vague bullet without concrete target"


def test_vague_word_inside_backticks_passes(tmp_path):
    """(b) Bullet where the denylist word is inside backticks does not trip."""
    sp, tp = _write_spec_todo(
        tmp_path,
        spec_content=(
            "### Phase 99\n\n"
            "- [ ] 99.1 [medium] do not use `iterative` loops;"
            " replace with batch call in `bin/foo.py`\n"
        ),
    )
    errors = vf.validate_spec_item_quality(sp, tp)
    assert errors == [], (
        f"Expected no errors when denylist word is inside backticks, got: {errors}"
    )


def test_concrete_target_exempts_vague_word(tmp_path):
    """(c) Bullet with a vague word but also a concrete file-path target passes."""
    sp, tp = _write_spec_todo(
        tmp_path,
        spec_content=(
            "### Phase 99\n\n"
            "- [ ] 99.1 [medium] polish bin/validate-frontmatter.py:"
            " add docstring to validate_spec_item_quality\n"
        ),
    )
    errors = vf.validate_spec_item_quality(sp, tp)
    assert errors == [], (
        f"Expected no errors when concrete file-path target is present, got: {errors}"
    )


def test_closed_spec_items_not_checked(tmp_path):
    """Closed [x] SPEC items are not checked even if they have vague wording."""
    sp, tp = _write_spec_todo(
        tmp_path,
        spec_content=(
            "### Phase 99\n\n"
            "- [x] 99.1 [medium] iterative cleanup with no concrete target\n"
        ),
    )
    errors = vf.validate_spec_item_quality(sp, tp)
    assert errors == [], f"Closed items must not be flagged, got: {errors}"


def test_todo_next_up_vague_item_fails(tmp_path):
    """A vague ## Next up TODO bullet with no concrete target is flagged."""
    sp, tp = _write_spec_todo(
        tmp_path,
        todo_content=(
            "## Next up (queued for next cycle)\n\n"
            "- [medium] ongoing general improvements to the UI — reason: spec 99.1\n"
        ),
    )
    errors = vf.validate_spec_item_quality(sp, tp)
    assert errors, "Expected error for vague Next-up item"


def test_todo_next_up_concrete_item_passes(tmp_path):
    """A concrete ## Next up TODO bullet with a file/symbol target passes."""
    sp, tp = _write_spec_todo(
        tmp_path,
        todo_content=(
            "## Next up (queued for next cycle)\n\n"
            "- [medium] 38.2 validate-frontmatter.py: add validate_spec_item_quality"
            " — reason: spec 38.2\n"
        ),
    )
    errors = vf.validate_spec_item_quality(sp, tp)
    assert errors == [], (
        f"Expected no errors for concrete Next-up item, got: {errors}"
    )


def test_real_spec_and_todo_pass_quality_check():
    """The current docs/SPEC.md and docs/TODO.md must pass the quality check."""
    errors = vf.validate_spec_item_quality()
    assert errors == [], (
        f"Current SPEC.md/TODO.md has open-ended items without concrete targets:\n"
        + "\n".join(errors)
    )


# ---- directory-argument handling (objectives-check bug, Phase 55) -------------
#
# `bin/validate-frontmatter.py skills/ chains/` (the form ssp-manager's
# objectives.md uses for skill-set-validator-clean) used to pass each bare
# directory through as a FILE target, then crash mid-run with IsADirectoryError
# when it tried to open the directory. A `grep`-based caller swallowed the
# traceback (it matches no findings) so the objective read "clean" even though
# the validator never actually ran. The fix walks a directory arg for
# SKILL.md/*.yaml instead. These guard that the dir arg is expanded, not opened.

_REPO = Path(__file__).parent.parent


def test_directory_arg_does_not_crash(monkeypatch):
    """A directory arg must be WALKED, not opened as a file. Pre-fix this raised
    IsADirectoryError; now `main()` returns an int exit code without raising."""
    import sys as _sys
    monkeypatch.setattr(
        _sys, "argv",
        ["validate-frontmatter.py", str(_REPO / "skills"), str(_REPO / "chains")],
    )
    rc = vf.main()   # must NOT raise IsADirectoryError
    assert isinstance(rc, int)
    # The repo is kept frontmatter-clean (the full suite asserts this elsewhere),
    # so the canonical objectives invocation must report clean via dir args.
    assert rc == 0, f"clean repo must validate clean through dir args, got rc={rc}"


def test_empty_directory_arg_finds_no_targets(monkeypatch, tmp_path):
    """A directory arg containing no SKILL.md/*.yaml expands to zero targets
    (and returns cleanly) rather than treating the directory path as a file."""
    import sys as _sys
    empty = tmp_path / "empty_skills"
    empty.mkdir()
    monkeypatch.setattr(_sys, "argv", ["validate-frontmatter.py", str(empty)])
    rc = vf.main()   # no targets -> clean early return, no IsADirectoryError
    assert rc == 0
