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


# ===== Phase 35.7: chunked sending for bodies > 4000 chars =====


def _run_notify_multi(
    message: str, env_extra: dict | None = None
) -> tuple[int, list[dict], str]:
    """Run notify-telegram.sh and collect every curl --data payload (for chunking tests).

    Returns (returncode, list_of_parsed_payloads_in_call_order, stderr).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        captured_dir = Path(tmpdir) / "captured"
        captured_dir.mkdir()
        fake_curl = Path(tmpdir) / "curl"
        # Each curl invocation writes its --data payload to a zero-padded numbered file
        # so that sort order == call order.
        fake_curl.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, json, pathlib\n"
            "args = sys.argv[1:]\n"
            "for i, a in enumerate(args):\n"
            f"    if a == '--data' and i + 1 < len(args):\n"
            f"        p = pathlib.Path(r'{captured_dir}')\n"
            f"        existing = sorted(p.glob('chunk_*.json'))\n"
            f"        n = len(existing)\n"
            f"        (p / f'chunk_{{n:03d}}.json').write_text(args[i + 1])\n"
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

        payloads = []
        for f in sorted(captured_dir.glob("chunk_*.json")):
            try:
                payloads.append(json.loads(f.read_text()))
            except json.JSONDecodeError:
                pass
        return proc.returncode, payloads, proc.stderr


def test_short_body_single_post():
    """A body under 4000 chars produces exactly one POST."""
    body = "hello, world"
    rc, payloads, stderr = _run_notify_multi(body)
    assert rc == 0, f"unexpected failure; stderr: {stderr!r}"
    assert len(payloads) == 1, f"expected 1 POST, got {len(payloads)}"
    assert payloads[0]["text"] == body


def test_long_body_multiple_posts_in_order():
    """A body > 4000 chars is split into multiple POSTs; each chunk ≤ 4000 chars;
    concatenating chunk texts reproduces the original (no fences, no rebalancing)."""
    # 200 lines × "this is line number NNN\n" ≈ 200 × 25 = 5000 chars
    lines = [f"this is line number {i:03d}" for i in range(200)]
    body = "\n".join(lines)
    assert len(body) > 4000, "test body must be > 4000 chars"

    rc, payloads, stderr = _run_notify_multi(body)
    assert rc == 0, f"unexpected failure; stderr: {stderr!r}"
    assert len(payloads) >= 2, f"expected ≥2 POSTs for a {len(body)}-char body"
    for i, p in enumerate(payloads):
        assert len(p["text"]) <= 4000, f"chunk {i} is {len(p['text'])} chars (> 4000)"
    # Without fences, chunks are contiguous slices — concatenating recovers the original.
    combined = "".join(p["text"] for p in payloads)
    assert combined == body, "chunks do not reassemble to original body"


def test_code_fence_rebalanced_at_split():
    """A code fence that spans a chunk boundary is closed in chunk N and reopened in N+1
    so every chunk has balanced ``` markers (even count)."""
    # 100 "a"s + newline + open fence + 4000 "x"s pushes the second chunk's
    # fence opening to the start, triggering the rebalancing path.
    body = "a" * 100 + "\n```python\n" + "x" * 4000 + "\n```\nfooter"
    assert len(body) > 4000

    rc, payloads, stderr = _run_notify_multi(body)
    assert rc == 0, f"unexpected failure; stderr: {stderr!r}"
    assert len(payloads) > 1, "expected multiple chunks"
    for i, p in enumerate(payloads):
        text = p["text"]
        assert text.count("```") % 2 == 0, (
            f"chunk {i} has an odd (unbalanced) number of ``` markers: {text[:200]!r}"
        )


# ===== parse-entities fallback: a body whose literal text breaks the parser is
# retried once as plain text rather than dropped. =====


def _run_notify_parse_failing(
    message: str, env_extra: dict | None = None
) -> tuple[int, list[dict], str]:
    """Run notify-telegram.sh against a mock curl that emulates Telegram rejecting any
    payload carrying a parse_mode with "can't parse entities", but accepting a payload
    with no parse_mode. Returns (rc, payloads_in_call_order, stderr)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        captured_dir = Path(tmpdir) / "captured"
        captured_dir.mkdir()
        fake_curl = Path(tmpdir) / "curl"
        fake_curl.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, json, pathlib\n"
            "args = sys.argv[1:]\n"
            "data = None\n"
            "for i, a in enumerate(args):\n"
            "    if a == '--data' and i + 1 < len(args):\n"
            "        data = args[i + 1]\n"
            "        break\n"
            f"p = pathlib.Path(r'{captured_dir}')\n"
            "n = len(sorted(p.glob('chunk_*.json')))\n"
            "if data is not None:\n"
            "    (p / f'chunk_{n:03d}.json').write_text(data)\n"
            "payload = json.loads(data) if data else {}\n"
            "if payload.get('parse_mode'):\n"
            "    print(json.dumps({'ok': False, 'error_code': 400,\n"
            "        'description': \"Bad Request: can't parse entities: \"\n"
            "        'character at byte offset 83'}))\n"
            "else:\n"
            "    print(json.dumps({'ok': True, 'result': {'message_id': 1}}))\n"
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
        payloads = []
        for f in sorted(captured_dir.glob("chunk_*.json")):
            try:
                payloads.append(json.loads(f.read_text()))
            except json.JSONDecodeError:
                pass
        return proc.returncode, payloads, proc.stderr


def test_parse_entities_failure_retries_as_plain_text():
    """A Markdown send rejected with "can't parse entities" is retried once with no
    parse_mode, and the retry succeeds (exit 0). This is the HUMAN.md-delta bug:
    literal backticks/brackets in the body broke legacy Markdown parsing."""
    body = '[cm] HUMAN.md: +H3.16 ##Blocking [ ] "done on `feature/x`"'
    rc, payloads, stderr = _run_notify_parse_failing(body)
    assert rc == 0, f"expected success after plain-text fallback; stderr: {stderr!r}"
    assert len(payloads) == 2, f"expected 2 POSTs (markdown + plain retry), got {len(payloads)}"
    assert payloads[0].get("parse_mode") == "Markdown", "first POST should use the default Markdown mode"
    assert "parse_mode" not in payloads[1], "retry POST must omit parse_mode (plain text)"
    assert payloads[1]["text"] == body, "retry must resend the identical body"
    assert "retrying as plain text" in stderr


def test_plain_text_mode_no_retry_needed():
    """With parse_mode disabled up front (TELEGRAM_PARSE_MODE=""), the same body sends in
    a single POST with no parse_mode — no parse failure, no fallback. This is the path
    notify-human-md.sh now uses for its literal delta summaries."""
    body = '[cm] HUMAN.md: +H3.16 ##Blocking [ ] "done on `feature/x`"'
    rc, payloads, stderr = _run_notify_parse_failing(body, env_extra={"TELEGRAM_PARSE_MODE": ""})
    assert rc == 0, f"expected success; stderr: {stderr!r}"
    assert len(payloads) == 1, f"expected exactly 1 POST, got {len(payloads)}"
    assert "parse_mode" not in payloads[0], "plain-text mode must omit parse_mode"
    assert payloads[0]["text"] == body
