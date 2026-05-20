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
