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
