"""CursorHarness unit tests — build_command + normalize_event against the
live 2026-07-14 stream-json fixture (tests/fixtures/cursor-stream-sample.jsonl).
"""
import json
import importlib.util
from pathlib import Path

_CHAIN_PATH = Path(__file__).parent.parent / "bin" / "skill-chain.py"
_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

CursorHarness = sc.CursorHarness
ClaudeCodeHarness = sc.ClaudeCodeHarness
_cursor_tool_call_fields = sc._cursor_tool_call_fields
DEFAULT_CURSOR_MODEL = sc.DEFAULT_CURSOR_MODEL

FIXTURE = Path(__file__).parent / "fixtures" / "cursor-stream-sample.jsonl"


def _fixture_events():
    return [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]


# ---- build_command ----------------------------------------------------------

def test_cursor_cold_start_uses_stream_json_and_force():
    h = CursorHarness()
    cmd = h.build_command("sst-translator")
    assert cmd[0] == "cursor-agent"
    assert "-p" in cmd
    assert "--force" in cmd
    assert cmd[cmd.index("--output-format") + 1] == "stream-json"
    assert "--model" in cmd
    assert cmd[cmd.index("--model") + 1] == DEFAULT_CURSOR_MODEL
    assert "-m" not in cmd  # short alias dropped in cursor-agent 2026.07
    assert "--resume" not in cmd


def test_cursor_cold_start_inlines_skill_body():
    """Cursor has no Skill tool — cold start inlines SKILL.md into the prompt."""
    h = CursorHarness()
    cmd = h.build_command("sst-translator")
    prompt = cmd[-1]
    assert "===== SKILL: sst-translator =====" in prompt
    assert "Use the Skill tool" not in prompt
    # Body should include transferable skill prose (not just the wrapper).
    assert "Translate" in prompt or "translate" in prompt


def test_cursor_resume_bare_continue():
    h = CursorHarness()
    cmd = h.build_command("sst-translator", resume_session_id="sess_cursor_abc")
    assert "--resume" in cmd
    idx = cmd.index("--resume")
    assert cmd[idx + 1] == "sess_cursor_abc"
    assert cmd[-1] == "continue"
    # Resume path must NOT re-inline the skill body.
    assert "===== SKILL:" not in " ".join(cmd)


def test_cursor_tester_cold_start_appends_wind_down():
    h = CursorHarness()
    prompt = h.build_command("sst-tester")[-1]
    assert "Turn budget:" in prompt
    assert f"hard ceiling is in force it is {h.max_turns}" in prompt


def test_cursor_non_tester_has_no_wind_down():
    h = CursorHarness()
    prompt = h.build_command("sst-translator")[-1]
    assert "Turn budget:" not in prompt


def test_claude_code_identity_unchanged_by_cursor():
    """Registering CursorHarness must not alter Claude Code command shape."""
    h = ClaudeCodeHarness()
    cmd = h.build_command("sst-dev-cycle")
    assert "claude" in cmd[0] or cmd[0].endswith("claude")
    assert "--resume" not in cmd
    assert "Use the Skill tool" in cmd[-1]


def test_get_harness_cursor():
    h = sc.get_harness("cursor")
    assert isinstance(h, CursorHarness)
    assert h.name == "cursor"


# ---- _cursor_tool_call_fields / normalize_event -----------------------------

def test_edit_tool_call_maps_to_edit_with_file_path():
    """Live Cursor writes via editToolCall with args.path (not writeToolCall)."""
    name, inp = _cursor_tool_call_fields({
        "editToolCall": {"args": {"path": "/tmp/run/tester-guidance.md", "streamContent": "x"}},
        "toolCallId": "t1",
    })
    assert name == "Edit"
    assert inp["file_path"] == "/tmp/run/tester-guidance.md"
    assert inp["path"] == "/tmp/run/tester-guidance.md"


def test_read_tool_call_maps_path_to_file_path():
    name, inp = _cursor_tool_call_fields({
        "readToolCall": {"args": {"path": "/tmp/foo.txt"}},
    })
    assert name == "Read"
    assert inp["file_path"] == "/tmp/foo.txt"


def test_shell_tool_call_maps_to_bash():
    name, inp = _cursor_tool_call_fields({
        "shellToolCall": {"args": {"command": "echo hi", "timeout": 30}},
    })
    assert name == "Bash"
    assert inp["command"] == "echo hi"


def test_write_tool_call_still_supported():
    """Forward-compat: writeToolCall (if Cursor ever emits it) still maps."""
    name, inp = _cursor_tool_call_fields({
        "writeToolCall": {"args": {"path": "/tmp/w.txt", "contents": "hi"}},
    })
    assert name == "Write"
    assert inp["file_path"] == "/tmp/w.txt"


def test_normalize_event_tool_call_started_becomes_tool_use():
    h = CursorHarness()
    event = {
        "type": "tool_call",
        "subtype": "started",
        "session_id": "s1",
        "tool_call": {
            "editToolCall": {"args": {"path": "/x/tester-guidance.md", "streamContent": "g"}},
            "toolCallId": "tc1",
        },
    }
    out = h.normalize_event(event)
    assert out["type"] == "assistant"
    block = out["message"]["content"][0]
    assert block["type"] == "tool_use"
    assert block["name"] == "Edit"
    assert block["input"]["file_path"].endswith("tester-guidance.md")


def test_normalize_event_passthrough_system_assistant_result():
    h = CursorHarness()
    for event in _fixture_events():
        if event.get("type") == "tool_call" and event.get("subtype") == "started":
            continue
        assert h.normalize_event(event) is event or h.normalize_event(event) == event


def test_fixture_covers_expected_event_types():
    types = {(e.get("type"), e.get("subtype")) for e in _fixture_events()}
    assert ("system", "init") in types
    assert ("tool_call", "started") in types
    assert ("tool_call", "completed") in types
    assert ("result", "success") in types
    # At least one assistant text frame
    assert any(e.get("type") == "assistant" for e in _fixture_events())


def test_fixture_normalize_maps_edit_and_read():
    h = CursorHarness()
    names = []
    for e in _fixture_events():
        if e.get("type") == "tool_call" and e.get("subtype") == "started":
            n = h.normalize_event(e)
            names.append(n["message"]["content"][0]["name"])
    assert "Edit" in names
    assert "Read" in names
    assert "Bash" in names


def test_wrote_tester_guidance_detects_cursor_edit(tmp_path):
    """Phase 49 gate: Cursor editToolCall of tester-guidance.md must set the flag."""
    h = CursorHarness()
    sink = sc._Sink(None)
    rec: dict = {}
    event = h.normalize_event({
        "type": "tool_call",
        "subtype": "started",
        "session_id": "s",
        "tool_call": {
            "editToolCall": {
                "args": {
                    "path": str(tmp_path / "tester-guidance.md"),
                    "streamContent": "# guidance\n",
                }
            }
        },
    })
    sc.handle_event(sink, event, rec)
    assert rec.get("wrote_tester_guidance") is True


def test_default_cursor_model_is_valid_grok_id():
    """DEFAULT_CURSOR_MODEL must be a real cursor-agent --model id, not bare 'grok'."""
    assert DEFAULT_CURSOR_MODEL == "cursor-grok-4.5-high"
    assert DEFAULT_CURSOR_MODEL != "grok"
