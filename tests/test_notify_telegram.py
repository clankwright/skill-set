"""Tests for TELEGRAM_LABEL feature in bin/notify-telegram.sh (SPEC 28.1)."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

NOTIFY_TELEGRAM = Path(__file__).parent.parent / "bin" / "notify-telegram.sh"


def _run_notify(message: str, env_extra: dict | None = None) -> tuple[int, dict | None]:
    """Run notify-telegram.sh with a mock curl that captures the --data payload.

    Returns (returncode, parsed_payload_dict | None).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        captured = Path(tmpdir) / "captured.json"
        fake_curl = Path(tmpdir) / "curl"
        # Mock curl: parse args to find --data value, write it, return ok JSON.
        fake_curl.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, json\n"
            "args = sys.argv[1:]\n"
            "for i, a in enumerate(args):\n"
            f"    if a == '--data' and i + 1 < len(args):\n"
            f"        open('{captured}', 'w').write(args[i + 1])\n"
            "        break\n"
            "print(json.dumps({'ok': True, 'result': {'message_id': 1}}))\n"
        )
        fake_curl.chmod(0o755)

        env = {
            "TELEGRAM_BOT_TOKEN": "fake_token",
            "TELEGRAM_CHAT_ID": "12345",
            "PATH": f"{tmpdir}:{os.environ['PATH']}",
            "HOME": os.environ.get("HOME", "/root"),
        }
        if env_extra:
            env.update(env_extra)

        proc = subprocess.run(
            ["bash", str(NOTIFY_TELEGRAM)],
            input=message,
            env=env,
            capture_output=True,
            text=True,
        )

        payload = None
        if captured.exists():
            try:
                payload = json.loads(captured.read_text())
            except json.JSONDecodeError:
                pass
        return proc.returncode, payload


def test_label_unset_body_unchanged():
    rc, payload = _run_notify("hello world")
    assert rc == 0, "expected success"
    assert payload is not None
    assert payload["text"] == "hello world"


def test_label_empty_body_unchanged():
    rc, payload = _run_notify("hello world", env_extra={"TELEGRAM_LABEL": ""})
    assert rc == 0, "expected success"
    assert payload is not None
    assert payload["text"] == "hello world"


def test_label_prepended():
    rc, payload = _run_notify("hello world", env_extra={"TELEGRAM_LABEL": "foo"})
    assert rc == 0, "expected success"
    assert payload is not None
    assert payload["text"] == "[foo]\n\nhello world"


def test_label_persona_cm():
    rc, payload = _run_notify("status update", env_extra={"TELEGRAM_LABEL": "cm"})
    assert rc == 0, "expected success"
    assert payload is not None
    assert payload["text"].startswith("[cm]\n\n"), f"got: {payload['text']!r}"


def test_label_multiline_body():
    body = "line one\nline two"
    rc, payload = _run_notify(body, env_extra={"TELEGRAM_LABEL": "skill-set"})
    assert rc == 0
    assert payload is not None
    assert payload["text"] == "[skill-set]\n\nline one\nline two"


# ===== Phase 34: base-dir fallback resolution chain =====

def _run_notify_custom(
    message: str, home: Path, env_extra: dict | None = None
) -> tuple[int, dict | None, str]:
    """Run notify-telegram.sh with a custom HOME (no default credentials).

    Returns (returncode, payload_or_None, stderr).
    """
    bin_dir = home / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    captured = home / "captured.json"

    fake_curl = bin_dir / "curl"
    fake_curl.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, json\n"
        "args = sys.argv[1:]\n"
        "for i, a in enumerate(args):\n"
        f"    if a == '--data' and i + 1 < len(args):\n"
        f"        open(r'{captured}', 'w').write(args[i + 1])\n"
        "        break\n"
        "print(json.dumps({'ok': True, 'result': {'message_id': 1}}))\n"
    )
    fake_curl.chmod(0o755)

    env = {
        "HOME": str(home),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
    }
    if env_extra:
        env.update(env_extra)

    proc = subprocess.run(
        ["bash", str(NOTIFY_TELEGRAM)],
        input=message,
        env=env,
        capture_output=True,
        text=True,
    )

    payload = None
    if captured.exists():
        try:
            payload = json.loads(captured.read_text())
        except json.JSONDecodeError:
            pass
    return proc.returncode, payload, proc.stderr


def test_base_dir_fallback_fires_when_no_explicit_env():
    """When no explicit env is set but ~/Dev/skill-set/telegram.env exists, it is auto-sourced."""
    with tempfile.TemporaryDirectory() as tmpdir:
        home = Path(tmpdir)
        sst_dir = home / "Dev" / "skill-set"
        sst_dir.mkdir(parents=True)
        (sst_dir / "telegram.env").write_text(
            "TELEGRAM_BOT_TOKEN=fallback_tok\nTELEGRAM_CHAT_ID=77777\n"
        )
        rc, payload, stderr = _run_notify_custom("fallback fires", home)
        assert rc == 0, f"expected success via base-dir fallback; stderr: {stderr!r}"
        assert payload is not None, "expected curl to be called"
        assert payload["chat_id"] == 77777


def test_explicit_token_beats_base_dir_fallback():
    """Explicitly set TELEGRAM_BOT_TOKEN wins over the base-dir fallback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        home = Path(tmpdir)
        sst_dir = home / "Dev" / "skill-set"
        sst_dir.mkdir(parents=True)
        (sst_dir / "telegram.env").write_text(
            "TELEGRAM_BOT_TOKEN=base_tok\nTELEGRAM_CHAT_ID=99999\n"
        )
        rc, payload, stderr = _run_notify_custom(
            "explicit wins",
            home,
            env_extra={"TELEGRAM_BOT_TOKEN": "explicit_tok", "TELEGRAM_CHAT_ID": "12345"},
        )
        assert rc == 0, f"expected success; stderr: {stderr!r}"
        assert payload is not None
        assert payload["chat_id"] == 12345  # explicit wins, not 99999 from base-dir


def test_env_file_beats_base_dir_fallback():
    """TELEGRAM_ENV_FILE wins over the base-dir fallback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        home = Path(tmpdir)
        sst_dir = home / "Dev" / "skill-set"
        sst_dir.mkdir(parents=True)
        (sst_dir / "telegram.env").write_text(
            "TELEGRAM_BOT_TOKEN=base_tok\nTELEGRAM_CHAT_ID=99999\n"
        )
        env_file = home / "my.env"
        env_file.write_text("TELEGRAM_BOT_TOKEN=file_tok\nTELEGRAM_CHAT_ID=55555\n")
        rc, payload, stderr = _run_notify_custom(
            "env-file wins",
            home,
            env_extra={"TELEGRAM_ENV_FILE": str(env_file)},
        )
        assert rc == 0, f"expected success; stderr: {stderr!r}"
        assert payload is not None
        assert payload["chat_id"] == 55555  # TELEGRAM_ENV_FILE wins, not 99999


def test_no_env_graceful_skip():
    """When no credentials are configured anywhere, exit 0 with a skip log on stderr."""
    with tempfile.TemporaryDirectory() as tmpdir:
        home = Path(tmpdir)
        # No telegram.env in base-dir, no explicit creds.
        rc, payload, stderr = _run_notify_custom("should skip", home)
        assert rc == 0, f"expected graceful skip (exit 0), not hard failure; stderr: {stderr!r}"
        assert payload is None, "expected curl NOT to be called when no credentials configured"
        assert "skip" in stderr.lower(), f"expected 'skip' in stderr; got: {stderr!r}"
