"""Tests for bin/install-skills.sh (TODO next-up item 2026-05-26):
.installed-body marker distinguishes UPDATE-from-source from DIVERGED (hand-edited).

Behavior under test:
  - No marker + bodies differ                          → DIVERGED (backward compat)
  - Marker present, target body matches marker         → UPDATE   (source-only bump)
  - Marker present, target body differs from marker    → DIVERGED (hand-edited)
  - Successful install/update writes .installed-body containing the new body
  - DIVERGED-skipped install does NOT update .installed-body
"""
import os
import subprocess
from pathlib import Path

INSTALL_SCRIPT = Path(__file__).parent.parent / "bin" / "install-skills.sh"

_FRONTMATTER = "name: myfakeskill\ndescription: test skill\n"
_BODY_V1 = "# Old body\n\nContent version one.\n"
_BODY_V2 = "# New body\n\nContent version two.\n"
_BODY_EDITED = "# Hand-edited body\n\nSomeone changed this manually.\n"


def _make_skill(parent: Path, name: str, frontmatter: str, body: str) -> Path:
    """Create <parent>/<name>/SKILL.md and return the skill dir."""
    skill_dir = parent / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\n{frontmatter}---\n{body}", encoding="utf-8"
    )
    return skill_dir


def _run(
    source: Path,
    target: Path,
    *extra_args: str,
    assume_yes: bool = True,
) -> subprocess.CompletedProcess:
    """Run install-skills.sh with the given source/target and return the result."""
    cmd = [
        "bash", str(INSTALL_SCRIPT),
        "--source", str(source),
        "--target", str(target),
    ]
    if assume_yes:
        cmd.append("-y")
    cmd.extend(extra_args)
    env = {**os.environ}  # inherit PATH etc.
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


# ---------------------------------------------------------------------------
# Status display (via --dry-run)
# ---------------------------------------------------------------------------

class TestStatusDisplay:
    """Verify UPDATE vs DIVERGED labels in dry-run output."""

    def test_unchanged_when_source_and_target_identical(self, tmp_path):
        """Identical source and target → 'unchanged'."""
        src = tmp_path / "skills"
        tgt = tmp_path / "target"
        _make_skill(src, "myfakeskill", _FRONTMATTER, _BODY_V1)
        _make_skill(tgt, "myfakeskill", _FRONTMATTER, _BODY_V1)

        result = _run(src, tgt, "--dry-run")
        assert result.returncode == 0, result.stderr
        assert "unchanged" in result.stdout

    def test_update_when_source_bumped_and_marker_matches_target(self, tmp_path):
        """Source body updated; target unchanged with matching marker → UPDATE not DIVERGED."""
        src = tmp_path / "skills"
        tgt = tmp_path / "target"
        # Source at v2 (bumped upstream).
        _make_skill(src, "myfakeskill", _FRONTMATTER, _BODY_V2)
        # Target still at v1 (unchanged since last install).
        tgt_skill = tgt / "myfakeskill"
        tgt_skill.mkdir(parents=True)
        (tgt_skill / "SKILL.md").write_text(
            f"---\n{_FRONTMATTER}---\n{_BODY_V1}", encoding="utf-8"
        )
        # Marker records that _BODY_V1 was installed.
        (tgt_skill / ".installed-body").write_text(_BODY_V1, encoding="utf-8")

        result = _run(src, tgt, "--dry-run")
        assert result.returncode == 0, result.stderr
        assert "UPDATE" in result.stdout, (
            f"expected UPDATE when marker matches target and source was bumped;\n{result.stdout}"
        )
        assert "DIVERGED" not in result.stdout, (
            f"unexpected DIVERGED when target was not hand-edited;\n{result.stdout}"
        )

    def test_diverged_when_target_hand_edited_and_marker_present(self, tmp_path):
        """Source updated; target also hand-edited (differs from marker) → DIVERGED."""
        src = tmp_path / "skills"
        tgt = tmp_path / "target"
        _make_skill(src, "myfakeskill", _FRONTMATTER, _BODY_V2)
        # Target was hand-edited to _BODY_EDITED.
        tgt_skill = tgt / "myfakeskill"
        tgt_skill.mkdir(parents=True)
        (tgt_skill / "SKILL.md").write_text(
            f"---\n{_FRONTMATTER}---\n{_BODY_EDITED}", encoding="utf-8"
        )
        # Marker records that _BODY_V1 was the last install.
        (tgt_skill / ".installed-body").write_text(_BODY_V1, encoding="utf-8")

        result = _run(src, tgt, "--dry-run")
        assert result.returncode == 0, result.stderr
        assert "DIVERGED" in result.stdout, (
            f"expected DIVERGED when target was hand-edited;\n{result.stdout}"
        )

    def test_diverged_without_marker_when_bodies_differ(self, tmp_path):
        """No marker, bodies differ → DIVERGED (backward compatibility)."""
        src = tmp_path / "skills"
        tgt = tmp_path / "target"
        _make_skill(src, "myfakeskill", _FRONTMATTER, _BODY_V2)
        _make_skill(tgt, "myfakeskill", _FRONTMATTER, _BODY_V1)
        # No .installed-body marker.

        result = _run(src, tgt, "--dry-run")
        assert result.returncode == 0, result.stderr
        assert "DIVERGED" in result.stdout, (
            f"expected DIVERGED when no marker and bodies differ;\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# Marker file management (actual installs, no --dry-run)
# ---------------------------------------------------------------------------

class TestMarkerFileManagement:
    """Verify .installed-body is created/updated/left alone correctly."""

    def test_marker_created_on_fresh_install(self, tmp_path):
        """A fresh --install creates .installed-body containing the source body."""
        src = tmp_path / "skills"
        tgt = tmp_path / "target"
        tgt.mkdir(parents=True)
        _make_skill(src, "myfakeskill", _FRONTMATTER, _BODY_V1)

        result = _run(src, tgt, "--install", "myfakeskill")
        assert result.returncode == 0, result.stderr

        marker = tgt / "myfakeskill" / ".installed-body"
        assert marker.exists(), ".installed-body must be created after a fresh install"
        assert marker.read_text(encoding="utf-8") == _BODY_V1, (
            ".installed-body must contain the installed body content"
        )

    def test_marker_updated_after_source_update(self, tmp_path):
        """Overwriting an existing skill updates .installed-body to the new body."""
        src = tmp_path / "skills"
        tgt = tmp_path / "target"
        # Pre-existing target at v1 with matching marker.
        _make_skill(src, "myfakeskill", _FRONTMATTER, _BODY_V1)
        tgt_skill = tgt / "myfakeskill"
        tgt_skill.mkdir(parents=True)
        (tgt_skill / "SKILL.md").write_text(
            f"---\n{_FRONTMATTER}---\n{_BODY_V1}", encoding="utf-8"
        )
        (tgt_skill / ".installed-body").write_text(_BODY_V1, encoding="utf-8")

        # Bump source to v2.
        _make_skill(src, "myfakeskill", _FRONTMATTER, _BODY_V2)

        result = _run(src, tgt)
        assert result.returncode == 0, result.stderr

        marker = tgt / "myfakeskill" / ".installed-body"
        assert marker.exists(), ".installed-body must exist after an update"
        assert marker.read_text(encoding="utf-8") == _BODY_V2, (
            ".installed-body must be updated to the new body after overwriting"
        )

    def test_force_overwrites_diverged_and_updates_marker(self, tmp_path):
        """--force on a DIVERGED (hand-edited) skill overwrites target and updates .installed-body to the new source body."""
        src = tmp_path / "skills"
        tgt = tmp_path / "target"
        # Source at v2.
        _make_skill(src, "myfakeskill", _FRONTMATTER, _BODY_V2)
        # Target was hand-edited; marker records v1 as the last install.
        tgt_skill = tgt / "myfakeskill"
        tgt_skill.mkdir(parents=True)
        (tgt_skill / "SKILL.md").write_text(
            f"---\n{_FRONTMATTER}---\n{_BODY_EDITED}", encoding="utf-8"
        )
        (tgt_skill / ".installed-body").write_text(_BODY_V1, encoding="utf-8")

        result = _run(src, tgt, "--force")
        assert result.returncode == 0, result.stderr
        assert "DIVERGED" in result.stdout, (
            f"expected DIVERGED label in --force overwrite output;\n{result.stdout}"
        )

        # Key assertion: marker must reflect the new source body, not the old v1 or the hand-edited body.
        marker = tgt_skill / ".installed-body"
        assert marker.exists(), ".installed-body must exist after --force overwrite"
        assert marker.read_text(encoding="utf-8") == _BODY_V2, (
            ".installed-body must be updated to the new source body after --force overwrite of a DIVERGED target"
        )
        # Target SKILL.md body must now contain the source body.
        tgt_body = (tgt_skill / "SKILL.md").read_text(encoding="utf-8")
        assert _BODY_V2 in tgt_body, (
            "target SKILL.md must be overwritten with source body after --force on DIVERGED"
        )

    def test_diverged_skip_leaves_marker_unchanged(self, tmp_path):
        """In -y mode, a DIVERGED-skipped install must not modify .installed-body."""
        src = tmp_path / "skills"
        tgt = tmp_path / "target"
        # Source at v2.
        _make_skill(src, "myfakeskill", _FRONTMATTER, _BODY_V2)
        # Target was hand-edited; marker records v1 as the last install.
        tgt_skill = tgt / "myfakeskill"
        tgt_skill.mkdir(parents=True)
        (tgt_skill / "SKILL.md").write_text(
            f"---\n{_FRONTMATTER}---\n{_BODY_EDITED}", encoding="utf-8"
        )
        (tgt_skill / ".installed-body").write_text(_BODY_V1, encoding="utf-8")

        result = _run(src, tgt)
        assert result.returncode == 0, result.stderr
        assert "DIVERGED" in result.stdout, "expected DIVERGED in output for hand-edited target"

        # Marker must be unchanged.
        marker_content = (tgt_skill / ".installed-body").read_text(encoding="utf-8")
        assert marker_content == _BODY_V1, (
            ".installed-body must not change when install was skipped (DIVERGED)"
        )
        # Target SKILL.md body must also be unchanged.
        tgt_body = (tgt_skill / "SKILL.md").read_text(encoding="utf-8")
        assert _BODY_EDITED in tgt_body, (
            "target SKILL.md must be unchanged when skipped due to DIVERGED"
        )
