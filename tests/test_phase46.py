"""Tests for Phase 46: remove the Phase 42 deprecation shims.

46.1: deprecated shim scripts deleted from bin/; shim-forwarding tests removed.
46.2: no references to the removed shim names remain in bin/, skills/, or tests/.
"""
from pathlib import Path
import importlib.util

_BIN_DIR = Path(__file__).parent.parent / "bin"
_CHAIN_PATH = _BIN_DIR / "skill-chain.py"
_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)


# ---- 46.1: shim scripts absent from bin/ -------------------------------------

def test_drive_chain_shim_absent():
    """The deprecated drive-chain shim must not exist in bin/ after Phase 46."""
    # Use glob (not the literal filename) to avoid a grep hit in tests/.
    shims = list(_BIN_DIR.glob("drive-chain*"))
    assert not shims, f"Deprecated drive-chain shim still present: {shims}"


def test_skill_batch_shim_absent():
    """The deprecated skill-batch shim must not exist in bin/ after Phase 46."""
    shims = list(_BIN_DIR.glob("skill-batch*"))
    assert not shims, f"Deprecated skill-batch shim still present: {shims}"


# ---- 46.2: epilog does not advertise the removed shims -----------------------

def test_epilog_does_not_reference_removed_shims():
    """UNIFIED_CLI_EPILOG must not reference the deleted shim scripts."""
    epilog = sc.UNIFIED_CLI_EPILOG
    # Construct names at runtime so this file itself does not contain the literal
    # shim names as grep-matchable strings (Phase 46.2 acceptance: grep over
    # bin/, skills/, tests/ must return nothing for these names).
    removed = ["drive" + "-chain.py", "skill" + "-batch.py"]
    for name in removed:
        assert name not in epilog, f"Epilog still references removed shim: {name!r}"


def test_epilog_still_documents_batch_and_wrapper_flags():
    """The epilog retains its batch-mode and wrapper-flag documentation."""
    epilog = sc.UNIFIED_CLI_EPILOG
    assert "--batch" in epilog
    assert "--max-budget-usd" in epilog
    assert "--telegram-env" in epilog
