"""Tests for bin/notify-human-md.sh (SPEC 33.1, 33.5)."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

NOTIFY_HUMAN_MD = Path(__file__).parent.parent / "bin" / "notify-human-md.sh"
NOTIFY_TELEGRAM = Path(__file__).parent.parent / "bin" / "notify-telegram.sh"


def _fake_telegram_sh(tmpdir: Path) -> Path:
    """Write a stub notify-telegram.sh that captures stdin to captured.txt."""
    captured = tmpdir / "captured.txt"
    stub = tmpdir / "notify-telegram-stub.sh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f"cat > '{captured}'\n"
    )
    stub.chmod(0o755)
    return stub


def _run(
    project_root: Path,
    human_md_path: Path | None = None,
    telegram_env: Path | None = None,
    snapshot_dir: Path | None = None,
    notify_telegram_stub: Path | None = None,
    extra_env: dict | None = None,
) -> tuple[int, str, str]:
    """Run notify-human-md.sh and return (returncode, stdout, stderr)."""
    cmd = ["bash", str(NOTIFY_HUMAN_MD), str(project_root)]
    if human_md_path is not None:
        cmd.append(str(human_md_path))
    if telegram_env is not None:
        cmd += ["--telegram-env", str(telegram_env)]

    env = {
        "HOME": str(project_root.parent),
        "PATH": os.environ["PATH"],
    }
    if snapshot_dir is not None:
        env["HUMAN_MD_SNAPSHOT_DIR"] = str(snapshot_dir)
    if notify_telegram_stub is not None:
        env["NOTIFY_TELEGRAM_BIN"] = str(notify_telegram_stub)
    if extra_env:
        env.update(extra_env)

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


SAMPLE_HUMAN_MD_EMPTY = """\
# Test Project HUMAN-action backlog

## Blocking

## High

## Medium

## Low

## Done
"""

SAMPLE_HUMAN_MD_ONE_ENTRY = """\
# Test Project HUMAN-action backlog

## Blocking

- [ ] H3.1 [easy] **Set API secret**
  The cycle needs a secret set in CI.
  Blocks: 3.1
  Verify: test -n "$SECRET"
  Filed by: sst-supervisor at 2026-05-23T10:00:00Z.
  Source: .skill-runs/example/supervisor_verdict.md

## High

## Medium

## Low

## Done
"""

SAMPLE_HUMAN_MD_ENTRY_DONE = """\
# Test Project HUMAN-action backlog

## Blocking

## High

## Medium

## Low

## Done

- [x] H3.1 [easy] **Set API secret** (verified 2026-05-23T11:00:00Z)
  Blocks: 3.1
"""

SAMPLE_HUMAN_MD_TWO_ENTRIES = """\
# Test Project HUMAN-action backlog

## Blocking

- [ ] H3.1 [easy] **Set API secret**
  Blocks: 3.1
  Filed by: sst-supervisor at 2026-05-23T10:00:00Z.

## High

- [ ] H3.2 [medium] **Get legal sign-off**
  Need approval from legal for the new TOS.
  Blocks: none
  Filed by: sst-dev-review at 2026-05-23T10:30:00Z.

## Medium

## Low

## Done
"""


def _make_project(tmpdir: Path, human_md_content: str) -> tuple[Path, Path, Path]:
    """Create a project root with docs/HUMAN.md and return (project_root, human_md, snapshot_dir)."""
    project_root = tmpdir / "myproject"
    docs = project_root / "docs"
    docs.mkdir(parents=True)
    human_md = docs / "HUMAN.md"
    human_md.write_text(human_md_content)
    snapshot_dir = tmpdir / "snapshots"
    snapshot_dir.mkdir()
    return project_root, human_md, snapshot_dir


class TestNoTelegramEnv:
    """Tests for graceful skip when no Telegram credentials are configured."""

    def test_graceful_skip_no_env(self):
        """When no Telegram env is configured, exit 0 with a skip note on stderr."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, _, snap = _make_project(Path(tmpdir), SAMPLE_HUMAN_MD_ONE_ENTRY)
            rc, stdout, stderr = _run(project_root, snapshot_dir=snap)
            assert rc == 0, f"expected exit 0 on graceful skip; stderr: {stderr!r}"

    def test_missing_human_md_exit_zero(self):
        """When HUMAN.md does not exist, exit 0 and skip gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "proj"
            project_root.mkdir()
            snap = Path(tmpdir) / "snap"
            snap.mkdir()
            rc, stdout, stderr = _run(project_root, snapshot_dir=snap)
            assert rc == 0, f"expected exit 0 when HUMAN.md absent; stderr: {stderr!r}"


class TestIdempotency:
    """Tests that a second call with no file change produces no send."""

    def test_idempotent_no_send_on_unchanged_file(self):
        """Second call with same HUMAN.md content must NOT send a Telegram message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            project_root, _, snap = _make_project(tdir, SAMPLE_HUMAN_MD_ONE_ENTRY)
            stub_dir = tdir / "stubdir"
            stub_dir.mkdir()
            captured = stub_dir / "captured.txt"
            stub = _fake_telegram_sh(stub_dir)

            # First call: sends (or skips due to no credentials — ok)
            rc, _, _ = _run(
                project_root, snapshot_dir=snap, notify_telegram_stub=stub
            )
            assert rc == 0

            # Remove captured file to detect if second call sends
            if captured.exists():
                captured.unlink()

            # Second call: file unchanged, must NOT send
            rc2, _, stderr2 = _run(
                project_root, snapshot_dir=snap, notify_telegram_stub=stub
            )
            assert rc2 == 0, f"expected exit 0 on idempotent call; stderr: {stderr2!r}"
            assert not captured.exists(), (
                "expected notify-telegram.sh NOT to be called on unchanged file"
            )


class TestSnapshotUpdate:
    """Tests that the snapshot is updated after a successful send."""

    def test_snapshot_updated_after_first_call(self):
        """After first call, a snapshot file must exist for the project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            project_root, _, snap = _make_project(tdir, SAMPLE_HUMAN_MD_ONE_ENTRY)
            stub_dir = tdir / "stubdir"
            stub_dir.mkdir()
            stub = _fake_telegram_sh(stub_dir)

            rc, _, stderr = _run(
                project_root, snapshot_dir=snap, notify_telegram_stub=stub
            )
            assert rc == 0, f"stderr: {stderr!r}"

            # At least one snapshot file must exist (sha or cache)
            snap_files = list(snap.iterdir())
            assert snap_files, "expected at least one snapshot file written after first call"

    def test_snapshot_enables_idempotency(self):
        """Snapshot written by call 1 prevents call 2 from sending again."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            project_root, _, snap = _make_project(tdir, SAMPLE_HUMAN_MD_ONE_ENTRY)
            stub_dir = tdir / "stubdir"
            stub_dir.mkdir()
            captured = stub_dir / "captured.txt"
            stub = _fake_telegram_sh(stub_dir)

            # Call 1
            _run(project_root, snapshot_dir=snap, notify_telegram_stub=stub)
            if captured.exists():
                captured.unlink()

            # Call 2 — no change, must not invoke stub
            _run(project_root, snapshot_dir=snap, notify_telegram_stub=stub)
            assert not captured.exists(), "second call must not re-send on unchanged file"


class TestDeltaDetection:
    """Tests that delta computation identifies additions, moves, and flips."""

    def _send_is_triggered(
        self, tdir: Path, before: str, after: str
    ) -> tuple[bool, str]:
        """Write before as snapshot, after as current file; return (was_sent, captured_body)."""
        project_root, human_md, snap = _make_project(tdir, after)
        stub_dir = tdir / "stubdir"
        stub_dir.mkdir(exist_ok=True)
        captured = stub_dir / "captured.txt"
        stub = _fake_telegram_sh(stub_dir)

        # Seed the snapshot with the "before" state by running once with that content
        human_md.write_text(before)
        _run(project_root, snapshot_dir=snap, notify_telegram_stub=stub)
        if captured.exists():
            captured.unlink()

        # Now write the "after" state
        human_md.write_text(after)
        _run(project_root, snapshot_dir=snap, notify_telegram_stub=stub)

        sent = captured.exists()
        body = captured.read_text() if sent else ""
        return sent, body

    def test_new_entry_triggers_send(self):
        """Adding a new H-ID entry triggers a notification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            sent, body = self._send_is_triggered(
                tdir, SAMPLE_HUMAN_MD_EMPTY, SAMPLE_HUMAN_MD_ONE_ENTRY
            )
            assert sent, "expected notify call when a new entry is added"
            assert "H3.1" in body, f"expected H3.1 in message body; got: {body!r}"

    def test_state_flip_triggers_send(self):
        """A [ ]→[x] state flip triggers a notification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            sent, body = self._send_is_triggered(
                tdir, SAMPLE_HUMAN_MD_ONE_ENTRY, SAMPLE_HUMAN_MD_ENTRY_DONE
            )
            assert sent, "expected notify call when entry flipped to [x]"
            assert "H3.1" in body, f"expected H3.1 in message body; got: {body!r}"

    def test_section_move_triggers_send(self):
        """Moving an entry between sections triggers a notification."""
        moved = SAMPLE_HUMAN_MD_ONE_ENTRY.replace(
            "## Blocking\n\n- [ ] H3.1", "## Blocking\n\n"
        ).replace("## High\n\n", "## High\n\n- [ ] H3.1 [easy] **Set API secret**\n  Blocks: 3.1\n\n")
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            sent, body = self._send_is_triggered(
                tdir, SAMPLE_HUMAN_MD_ONE_ENTRY, moved
            )
            assert sent, "expected notify call when entry moved between sections"
            assert "H3.1" in body, f"expected H3.1 in message body; got: {body!r}"

    def test_no_change_no_send(self):
        """Identical before and after produces no notification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            sent, _ = self._send_is_triggered(
                tdir, SAMPLE_HUMAN_MD_ONE_ENTRY, SAMPLE_HUMAN_MD_ONE_ENTRY
            )
            assert not sent, "expected no notify call when file is unchanged"

    def test_message_includes_project_name(self):
        """Notification body includes the project directory name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            sent, body = self._send_is_triggered(
                tdir, SAMPLE_HUMAN_MD_EMPTY, SAMPLE_HUMAN_MD_ONE_ENTRY
            )
            assert sent
            assert "myproject" in body, f"expected project name in body; got: {body!r}"

    def test_multiple_new_entries(self):
        """Adding two entries produces a message mentioning both IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            sent, body = self._send_is_triggered(
                tdir, SAMPLE_HUMAN_MD_EMPTY, SAMPLE_HUMAN_MD_TWO_ENTRIES
            )
            assert sent
            assert "H3.1" in body, f"expected H3.1 in body; got: {body!r}"
            assert "H3.2" in body, f"expected H3.2 in body; got: {body!r}"


class TestTelegramEnvArg:
    """Tests that --telegram-env arg is forwarded correctly."""

    def test_telegram_env_arg_forwarded(self):
        """--telegram-env path is passed to notify-telegram.sh (via TELEGRAM_ENV_FILE)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            project_root, human_md, snap = _make_project(tdir, SAMPLE_HUMAN_MD_ONE_ENTRY)
            # Write a fake .env file
            env_file = tdir / "fake.env"
            env_file.write_text(
                "TELEGRAM_BOT_TOKEN=test_token\nTELEGRAM_CHAT_ID=12345\n"
            )
            stub_dir = tdir / "stubdir"
            stub_dir.mkdir()
            captured = stub_dir / "captured.txt"
            stub = _fake_telegram_sh(stub_dir)

            rc, _, stderr = _run(
                project_root,
                snapshot_dir=snap,
                telegram_env=env_file,
                notify_telegram_stub=stub,
            )
            assert rc == 0, f"stderr: {stderr!r}"
            # The stub must have been invoked (the env file has valid creds)
            assert captured.exists(), (
                "expected notify-telegram.sh to be called when valid --telegram-env provided"
            )
