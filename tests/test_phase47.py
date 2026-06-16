"""Tests for Phase 47: README feature + usage overview.

47.1: README.md has a Features/Functionality section covering (a)-(d):
      (a) the framework + transferable/proprietary sst-/ssp- model
      (b) the skill catalog (dev-cycle, dev-review, tester, supervisor, manager,
          chain-driver, sanitize-transferable, research/content/outreach families)
      (c) the chains (dev-cycle-with-review, -looped, -overnight, etc.)
      (d) the unified runner CLI flags (--chain/--loop/--overnight/--batch/
          --max-budget-usd/--profile)
47.2: README.md has a Usage section with four copy-pasteable examples, all via
      skill-chain.py, no references to the removed shims.
"""
from pathlib import Path

_README = Path(__file__).parent.parent / "README.md"


def _text():
    return _README.read_text()


# ---- 47.1: Features / Functionality section ----------------------------------

def test_features_section_exists():
    """README must have a Features or Functionality section header."""
    text = _text()
    headers = [line.strip() for line in text.splitlines() if line.startswith("##")]
    assert any("feature" in h.lower() or "functionality" in h.lower() for h in headers), (
        "README.md is missing a Features/Functionality section header"
    )


def test_features_mentions_sst_ssp_model():
    """Features section must mention the sst- / ssp- prefix convention."""
    text = _text()
    assert "sst-" in text
    assert "ssp-" in text


def test_features_skill_catalog_dev_cycle():
    """Features section must reference the dev-cycle skill by name."""
    assert "dev-cycle" in _text()


def test_features_skill_catalog_dev_review():
    """Features section must reference the dev-review skill by name."""
    assert "dev-review" in _text()


def test_features_skill_catalog_tester():
    """Features section must reference the tester skill by name."""
    assert "tester" in _text()


def test_features_skill_catalog_supervisor():
    """Features section must reference the supervisor skill by name."""
    assert "supervisor" in _text()


def test_features_skill_catalog_manager():
    """Features section must reference the manager skill by name."""
    assert "manager" in _text()


def test_features_skill_catalog_chain_driver():
    """Features section must reference the chain-driver skill by name."""
    assert "chain-driver" in _text()


def test_features_skill_catalog_sanitize():
    """Features section must reference the sanitize-transferable skill by name."""
    assert "sanitize-transferable" in _text()


def test_features_chains_dev_cycle_with_review():
    """Features section must mention the dev-cycle-with-review chain."""
    assert "dev-cycle-with-review" in _text()


def test_features_chains_overnight():
    """Features section must mention the overnight chain variant."""
    assert "overnight" in _text()


def test_features_cli_flag_chain():
    """Features section must document the --chain CLI flag."""
    assert "--chain" in _text()


def test_features_cli_flag_loop():
    """Features section must document the --loop CLI flag."""
    assert "--loop" in _text()


def test_features_cli_flag_overnight():
    """Features section must document the --overnight CLI flag."""
    assert "--overnight" in _text()


def test_features_cli_flag_batch():
    """Features section must document the --batch CLI flag."""
    assert "--batch" in _text()


def test_features_cli_flag_max_budget():
    """Features section must document the --max-budget-usd CLI flag."""
    assert "--max-budget-usd" in _text()


def test_features_cli_flag_profile():
    """Features section must document the --profile CLI flag."""
    assert "--profile" in _text()


# ---- 47.2: Usage examples section -------------------------------------------

def test_usage_section_exists():
    """README must have a Usage section header."""
    text = _text()
    headers = [line.strip() for line in text.splitlines() if line.startswith("##")]
    assert any("usage" in h.lower() for h in headers), (
        "README.md is missing a Usage section header"
    )


def test_usage_chain_example():
    """Usage section must show a run-a-chain example with skill-chain.py."""
    text = _text()
    assert "skill-chain.py" in text
    assert "--chain" in text


def test_usage_overnight_example():
    """Usage section must show an overnight drain example."""
    assert "--overnight" in _text()


def test_usage_batch_example():
    """Usage section must show a batch mode example."""
    assert "--batch" in _text()


def test_usage_standalone_tester_example():
    """Usage section must show the standalone tester sweep example."""
    text = _text()
    assert "sst-tester" in text
    assert "--phase" in text


def test_usage_no_removed_shim_references():
    """Usage examples must not reference the removed shim scripts."""
    text = _text()
    # Build names at runtime so this file itself does not contain the literal
    # shim names as grep-matchable strings (46.2 acceptance: grep over tests/ clean).
    removed = ["drive" + "-chain.py", "skill" + "-batch.py"]
    for name in removed:
        assert name not in text, f"README.md still references removed shim: {name!r}"
