"""Tests for bin/check-ssp-sync.py: detect ssp-* wrappers drifted behind base.

Covers the upgrade-flow hardening: a proprietary wrapper pins the base
transferable version it was last reconciled against (`base-version:`), and this
tool flags wrappers whose base has moved ahead, is unpinned, or points at an
unknown base.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT = _REPO_ROOT / "bin" / "check-ssp-sync.py"


def _load_module():
    """Load check-ssp-sync.py as a module (hyphenated filename)."""
    spec = importlib.util.spec_from_file_location("check_ssp_sync", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_skill(path: Path, name: str, version: str | None = None,
                 transferable: str | None = None, base_version: str | None = None) -> None:
    """Create <path>/SKILL.md with the given frontmatter keys."""
    path.mkdir(parents=True, exist_ok=True)
    fm = [f"name: {name}"]
    if version is not None:
        fm.append(f"version: {version}")
    if transferable is not None:
        fm.append(f"transferable: {transferable}")
    if base_version is not None:
        fm.append(f"base-version: {base_version}")
    body = "---\n" + "\n".join(fm) + "\n---\n\n# " + name + "\n"
    (path / "SKILL.md").write_text(body, encoding="utf-8")


@pytest.fixture()
def env(tmp_path: Path):
    """A tmp base repo (skills/) + a tmp installed-skills dir."""
    base = tmp_path / "skill-set"
    base_skills = base / "skills" / "framework"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True)
    # Base transferables.
    _write_skill(base_skills / "sst-manager", "sst-manager", version="2.2.0")
    _write_skill(base_skills / "sst-dev-cycle", "sst-dev-cycle", version="1.7.0")
    return {"base": base, "skills_dir": skills_dir}


# ── Availability ─────────────────────────────────────────────────────────────

def test_script_exists():
    assert _SCRIPT.exists(), f"Missing: {_SCRIPT}"


# ── Unit: version parsing + classification ───────────────────────────────────

def test_parse_version():
    mod = _load_module()
    assert mod.parse_version("2.2.0") == (2, 2, 0)
    assert mod.parse_version("1.7.0-rc1") == (1, 7, 0)
    assert mod.parse_version(None) is None
    assert mod.parse_version("nope") is None


def test_classify():
    mod = _load_module()
    assert mod._classify("2.2.0", "2.2.0") == "ok"
    assert mod._classify("2.1.0", "2.2.0") == "stale"
    assert mod._classify("2.3.0", "2.2.0") == "ahead"
    assert mod._classify(None, "2.2.0") == "unpinned"
    assert mod._classify("2.2.0", None) == "unknown-base"
    assert mod._classify("x", "2.2.0") == "unparseable"


# ── Integration via main(argv) ───────────────────────────────────────────────

def _run(env, mod, capsys, extra=None):
    argv = ["--base", str(env["base"]), "--skills-dir", str(env["skills_dir"])]
    if extra:
        argv += extra
    rc = mod.main(argv)
    out = capsys.readouterr().out
    return rc, out


def test_all_in_sync_exit_0(env, capsys):
    mod = _load_module()
    _write_skill(env["skills_dir"] / "ssp-cm-manager", "ssp-cm-manager",
                 version="1.3.0", transferable="sst-manager", base_version="2.2.0")
    rc, out = _run(env, mod, capsys)
    assert rc == 0
    assert "OK" in out


def test_stale_wrapper_exit_1(env, capsys):
    mod = _load_module()
    _write_skill(env["skills_dir"] / "ssp-cm-manager", "ssp-cm-manager",
                 version="1.3.0", transferable="sst-manager", base_version="2.1.0")
    rc, out = _run(env, mod, capsys)
    assert rc == 1
    assert "stale" in out
    assert "ssp-cm-manager" in out


def test_unpinned_wrapper_exit_1(env, capsys):
    mod = _load_module()
    _write_skill(env["skills_dir"] / "ssp-cm-dev", "ssp-cm-dev",
                 version="1.7.0", transferable="sst-dev-cycle")  # no base-version
    rc, out = _run(env, mod, capsys)
    assert rc == 1
    assert "unpinned" in out


def test_unknown_base_exit_1(env, capsys):
    mod = _load_module()
    _write_skill(env["skills_dir"] / "ssp-cm-ghost", "ssp-cm-ghost",
                 version="1.0.0", transferable="sst-nonexistent", base_version="1.0.0")
    rc, out = _run(env, mod, capsys)
    assert rc == 1
    assert "unknown-base" in out


def test_ahead_wrapper_exit_1(env, capsys):
    mod = _load_module()
    _write_skill(env["skills_dir"] / "ssp-cm-manager", "ssp-cm-manager",
                 version="1.3.0", transferable="sst-manager", base_version="2.3.0")
    rc, out = _run(env, mod, capsys)
    assert rc == 1
    assert "ahead" in out


def test_non_wrapper_skipped(env, capsys):
    mod = _load_module()
    # A plain transferable copy (no `transferable:` key) must be ignored.
    _write_skill(env["skills_dir"] / "sst-manager", "sst-manager", version="2.2.0")
    rc, out = _run(env, mod, capsys)
    assert rc == 0  # no wrappers => no drift
    assert "no proprietary wrappers" in out


def test_mixed_reports_only_drift(env, capsys):
    mod = _load_module()
    _write_skill(env["skills_dir"] / "ssp-cm-manager", "ssp-cm-manager",
                 version="1.3.0", transferable="sst-manager", base_version="2.2.0")  # ok
    _write_skill(env["skills_dir"] / "ssp-cm-dev", "ssp-cm-dev",
                 version="1.7.0", transferable="sst-dev-cycle", base_version="1.6.0")  # stale
    rc, out = _run(env, mod, capsys)
    assert rc == 1
    assert "ssp-cm-dev" in out and "stale" in out
    assert "ssp-cm-manager" in out  # listed under in-sync


def test_json_output(env, capsys):
    mod = _load_module()
    _write_skill(env["skills_dir"] / "ssp-cm-manager", "ssp-cm-manager",
                 version="1.3.0", transferable="sst-manager", base_version="2.1.0")
    rc, out = _run(env, mod, capsys, extra=["--json"])
    assert rc == 1
    payload = json.loads(out)
    assert payload["drift"] is True
    assert payload["wrappers"][0]["status"] == "stale"


def test_missing_base_dir_exit_2(tmp_path):
    mod = _load_module()
    rc = mod.main(["--base", str(tmp_path / "nope"),
                   "--skills-dir", str(tmp_path)])
    assert rc == 2


def test_missing_skills_dir_exit_2(env):
    mod = _load_module()
    rc = mod.main(["--base", str(env["base"]),
                   "--skills-dir", str(env["base"] / "nope")])
    assert rc == 2


def test_messy_description_still_parsed(env, capsys):
    """A wrapper whose single-line description contains ': ' (invalid strict
    YAML) must still be detected via line-based key extraction."""
    mod = _load_module()
    d = env["skills_dir"] / "ssp-cm-manager"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\n"
        "name: ssp-cm-manager\n"
        "description: Oversight manager. Three modes: periodic, feedback, planner. "
        "Reads docs/HUMAN.md: fires alerts; never commits.\n"
        "version: 1.3.0\n"
        "transferable: sst-manager\n"
        "base-version: 2.2.0\n"  # matches fixture base sst-manager 2.2.0 => in sync
        "---\n\n# ssp-cm-manager\n",
        encoding="utf-8",
    )
    rc, out = _run(env, mod, capsys)
    assert rc == 0
    assert "ssp-cm-manager" in out  # detected + parsed despite the messy description
