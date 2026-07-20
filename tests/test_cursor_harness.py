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
    assert "--approve-mcps" in cmd  # Phase 61.2 — headless MCP auto-approve
    assert "--trust" in cmd         # Phase 61.2 — trust workspace in -p mode
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
    # Claude-style Skill-tool *bootstrap* must not be the cold-start lead-in
    # (Phase 64 nested-skill directive may quote the phrase as what to replace).
    assert not prompt.lstrip().startswith("Use the Skill tool")
    # Body should include transferable skill prose (not just the wrapper).
    assert "Translate" in prompt or "translate" in prompt
    # Phase 64 — nested-skill Read+follow directive (sanitize gate path).
    assert "Nested skills / Skill tool (Cursor harness)" in prompt
    assert "sst-sanitize-transferable" in prompt
    assert "same session" in prompt
    # Phase 61.1 — Brave WebSearch/WebFetch substitute directive.
    assert "brave-web.py" in prompt
    assert "Web search / fetch (Cursor harness)" in prompt
    # Phase 62 — Playwright MCP browser directive (never cursor-ide-browser).
    assert "Browser automation (Cursor harness)" in prompt
    assert "cursor-ide-browser" in prompt  # named as forbidden
    assert "Playwright" in prompt


def test_cursor_resume_skips_brave_directive():
    """Resume path must not re-inject Brave/web/nested-skill directives."""
    h = CursorHarness()
    cmd = h.build_command("sst-translator", resume_session_id="sess_x")
    joined = " ".join(cmd)
    assert "brave-web.py" not in joined
    assert "Browser automation (Cursor harness)" not in joined
    assert "Nested skills / Skill tool (Cursor harness)" not in joined
    assert "--approve-mcps" in cmd  # flags still present on resume
    assert "--trust" in cmd


def test_claude_code_has_no_brave_directive():
    """Brave/Playwright/nested-skill substitutes are Cursor-only."""
    h = ClaudeCodeHarness()
    cmd = h.build_command("sst-dev-cycle")
    joined = " ".join(cmd)
    assert "brave-web.py" not in joined
    assert "Browser automation (Cursor harness)" not in joined
    assert "Nested skills / Skill tool (Cursor harness)" not in joined
    assert "--approve-mcps" not in cmd
    assert "--trust" not in cmd


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
    assert out.get("_synthetic_from_tool_call") is True
    block = out["message"]["content"][0]
    assert block["type"] == "tool_use"
    assert block["name"] == "Edit"
    assert block["input"]["file_path"].endswith("tester-guidance.md")


def test_normalize_event_passthrough_system_assistant_result():
    h = CursorHarness()
    for event in _fixture_events():
        if event.get("type") == "tool_call" and event.get("subtype") == "started":
            continue
        # result frames with usage are reshaped (usage → modelUsage); skip them.
        if event.get("type") == "result" and event.get("usage"):
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
    # Synthetic tool_call frames must not inflate the turn proxy (64.3).
    assert rec.get("_turn_proxy", 0) == 0


def test_turn_proxy_counts_native_assistant_not_synthetic_tool_calls():
    """Phase 64.3: mixed text + tool_call stream — only native assistant frames count."""
    h = CursorHarness()
    sink = sc._Sink(None)
    rec: dict = {}
    # 2 native assistant text frames + 5 synthetic tool_call frames → proxy=2.
    stream = [
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "thinking"}]},
            "session_id": "s",
        },
        {
            "type": "tool_call",
            "subtype": "started",
            "session_id": "s",
            "tool_call": {
                "readToolCall": {"args": {"path": "/tmp/a.txt"}},
                "toolCallId": "tc1",
            },
        },
        {
            "type": "tool_call",
            "subtype": "started",
            "session_id": "s",
            "tool_call": {
                "shellToolCall": {"args": {"command": "ls"}},
                "toolCallId": "tc2",
            },
        },
        {
            "type": "tool_call",
            "subtype": "started",
            "session_id": "s",
            "tool_call": {
                "readToolCall": {"args": {"path": "/tmp/b.txt"}},
                "toolCallId": "tc3",
            },
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "done"}]},
            "session_id": "s",
        },
        {
            "type": "tool_call",
            "subtype": "started",
            "session_id": "s",
            "tool_call": {
                "editToolCall": {
                    "args": {"path": "/tmp/c.txt", "streamContent": "x"},
                },
                "toolCallId": "tc4",
            },
        },
        {
            "type": "tool_call",
            "subtype": "started",
            "session_id": "s",
            "tool_call": {
                "shellToolCall": {"args": {"command": "echo hi"}},
                "toolCallId": "tc5",
            },
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "duration_ms": 10,
            "usage": {
                "inputTokens": 10,
                "outputTokens": 5,
                "cacheReadTokens": 0,
                "cacheWriteTokens": 0,
            },
            "model": "cursor-grok-4.5-high",
        },
    ]
    for e in stream:
        sc.handle_event(sink, h.normalize_event(e), rec)
    assert rec["num_turns"] == 2
    assert "_turn_proxy" not in rec


def test_default_cursor_model_is_valid_grok_id():
    """DEFAULT_CURSOR_MODEL must be a real cursor-agent --model id, not bare 'grok'."""
    assert DEFAULT_CURSOR_MODEL == "cursor-grok-4.5-high"
    assert DEFAULT_CURSOR_MODEL != "grok"


# ---- Phase 63: Grok ladder routing ------------------------------------------

def test_cursor_grok_id_maps_effort_and_model_floors(monkeypatch):
    """max(model-band, effort-band) → cursor-grok-4.5-{low,medium,high}."""
    monkeypatch.delenv("CURSOR_MODEL", raising=False)
    assert sc._cursor_grok_id_for_route("haiku", "low") == "cursor-grok-4.5-low"
    assert sc._cursor_grok_id_for_route("sonnet", "low") == "cursor-grok-4.5-medium"
    assert sc._cursor_grok_id_for_route("sonnet", "medium") == "cursor-grok-4.5-medium"
    assert sc._cursor_grok_id_for_route("opus", "medium") == "cursor-grok-4.5-high"
    assert sc._cursor_grok_id_for_route("opus", "high") == "cursor-grok-4.5-high"
    assert sc._cursor_grok_id_for_route("fable", "xhigh") == "cursor-grok-4.5-high"
    assert sc._cursor_grok_id_for_route("haiku", "high") == "cursor-grok-4.5-high"
    # Neither → default high
    assert sc._cursor_grok_id_for_route(None, None) == DEFAULT_CURSOR_MODEL


def test_cursor_grok_id_env_pin_overrides_ladder(monkeypatch):
    monkeypatch.setenv("CURSOR_MODEL", "cursor-grok-4.5-low")
    assert sc._cursor_grok_id_for_route("opus", "xhigh") == "cursor-grok-4.5-low"


def test_cursor_grok_id_passes_through_concrete_ids(monkeypatch):
    monkeypatch.delenv("CURSOR_MODEL", raising=False)
    assert sc._cursor_grok_id_for_route("cursor-grok-4.5-medium-fast", None) == (
        "cursor-grok-4.5-medium-fast"
    )
    assert sc._cursor_grok_id_for_route("composer-2.5", "high") == "composer-2.5"


def test_cursor_resolve_cli_route_and_build_command_honor_ladder(monkeypatch):
    monkeypatch.delenv("CURSOR_MODEL", raising=False)
    h = CursorHarness()
    cli_model, cli_effort = h.resolve_cli_route("sonnet", "low")
    assert cli_model == "cursor-grok-4.5-medium"
    assert cli_effort is None
    cmd = h.build_command("sst-translator", model="sonnet", effort="low")
    assert cmd[cmd.index("--model") + 1] == "cursor-grok-4.5-medium"
    # Claude harness still passes tiers through.
    ch = ClaudeCodeHarness()
    cm, ce = ch.resolve_cli_route("sonnet", "low")
    assert (cm, ce) == ("sonnet", "low")


def test_cursor_build_command_uses_passed_cli_model(monkeypatch):
    """run_iteration may pass an already-resolved Grok id."""
    monkeypatch.delenv("CURSOR_MODEL", raising=False)
    h = CursorHarness()
    cmd = h.build_command("sst-translator", model="cursor-grok-4.5-low", effort=None)
    assert cmd[cmd.index("--model") + 1] == "cursor-grok-4.5-low"


# ---- Cursor telemetry (usage → modelUsage + budget loud-skip) ---------------

def test_cursor_usage_to_model_usage_renames_cache_keys():
    usage = {
        "inputTokens": 21442,
        "outputTokens": 134,
        "cacheReadTokens": 34048,
        "cacheWriteTokens": 0,
    }
    out = sc._cursor_usage_to_model_usage(usage, "cursor-grok-4.5-high")
    assert "cursor-grok-4.5-high" in out
    u = out["cursor-grok-4.5-high"]
    assert u["inputTokens"] == 21442
    assert u["outputTokens"] == 134
    assert u["cacheReadInputTokens"] == 34048
    assert u["cacheCreationInputTokens"] == 0
    # Grok 4.5 rates: $2/M in + $0.50/M cache-read + $6/M out
    expected = (21442 * 2.0 + 134 * 6.0 + 34048 * 0.50) / 1_000_000
    assert abs(u["costUSD"] - expected) < 1e-9


def test_estimate_cursor_cost_usd_grok_rates():
    usage = {
        "inputTokens": 1_000_000,
        "outputTokens": 500_000,
        "cacheReadTokens": 2_000_000,
        "cacheWriteTokens": 100_000,
    }
    # 1M*$2 + 0.5M*$6 + 2M*$0.50 + 0.1M*$2 = 2 + 3 + 1 + 0.2 = 6.2
    assert sc._estimate_cursor_cost_usd(usage, "cursor-grok-4.5-high") == 6.2


def test_estimate_cursor_cost_usd_claude_sonnet_rates():
    usage = {
        "inputTokens": 1_000_000,
        "outputTokens": 1_000_000,
        "cacheReadTokens": 1_000_000,
        "cacheWriteTokens": 1_000_000,
    }
    # Cursor docs: $3 / $3.75 / $0.3 / $15
    assert sc._estimate_cursor_cost_usd(usage, "claude-4.5-sonnet") == (
        3.0 + 3.75 + 0.3 + 15.0
    )


def test_normalize_result_maps_usage_to_model_usage():
    h = CursorHarness()
    result = next(e for e in _fixture_events() if e.get("type") == "result")
    assert "usage" in result and "modelUsage" not in result
    out = h.normalize_event(result)
    assert "modelUsage" in out
    model_key = next(iter(out["modelUsage"]))
    u = out["modelUsage"][model_key]
    assert u["inputTokens"] == result["usage"]["inputTokens"]
    assert u["cacheReadInputTokens"] == result["usage"]["cacheReadTokens"]
    expected = sc._estimate_cursor_cost_usd(
        result["usage"], "cursor-grok-4.5-high"
    )
    assert abs(out.get("total_cost_usd") - expected) < 1e-9
    assert abs(u["costUSD"] - expected) < 1e-9
    # Raw fixture event must stay untouched (jsonl writes pre-normalize).
    assert "modelUsage" not in result


def test_handle_event_cursor_result_fills_model_usage_and_turn_proxy():
    """Full path: normalize + handle_event → skill_record has tokens + turn proxy."""
    h = CursorHarness()
    sink = sc._Sink(None)
    rec: dict = {}
    # Two assistant frames → turn_proxy=2 when result omits num_turns.
    for e in _fixture_events():
        ev = h.normalize_event(e)
        sc.handle_event(sink, ev, rec)
    expected = sc._estimate_cursor_cost_usd(
        next(e for e in _fixture_events() if e.get("type") == "result")["usage"],
        "cursor-grok-4.5-high",
    )
    assert abs(rec["total_cost_usd"] - expected) < 1e-9
    assert rec["num_turns"] >= 1  # native assistant text only (tool_call frames excluded, 64.3)
    assert rec["model_usage"]
    model_key = next(iter(rec["model_usage"]))
    assert rec["model_usage"][model_key]["inputTokens"] == 21442
    assert "_turn_proxy" not in rec  # cleaned up after result


def test_claude_result_num_turns_not_overwritten_by_proxy():
    sink = sc._Sink(None)
    rec: dict = {"_turn_proxy": 99}
    sc.handle_event(sink, {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 100,
        "total_cost_usd": 0.12,
        "num_turns": 5,
        "modelUsage": {"claude-opus": {"inputTokens": 1, "outputTokens": 1,
                                       "cacheReadInputTokens": 0,
                                       "cacheCreationInputTokens": 0,
                                       "costUSD": 0.12}},
    }, rec)
    assert rec["num_turns"] == 5
    assert rec["total_cost_usd"] == 0.12


def test_handle_event_null_num_turns_uses_proxy(capsys):
    """Live Cursor emits num_turns:null; inject proxy so summary is not 'None turns'."""
    sink = sc._Sink(None)
    rec: dict = {"_turn_proxy": 7}
    sc.handle_event(sink, {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 1500,
        "total_cost_usd": 0,
        "num_turns": None,  # key present, value null (live Cursor shape)
        "modelUsage": {},
    }, rec)
    assert rec["num_turns"] == 7
    out = capsys.readouterr().out
    assert "7 turns" in out
    assert "None turns" not in out


def test_cursor_budget_cap_kept_with_estimate_note(capsys):
    """--max-budget-usd under cursor stays set; note says costs are estimated."""
    args = sc.parse_args([
        "--harness", "cursor",
        "--max-budget-usd", "30",
        "--max-cycles", "2",
        "--no-log",
        "--no-supervisor",
        "sst-translator",
    ])
    harness = sc.get_harness(args.harness)
    harness.apply_budget_constraints(args, loop_count=2)
    assert args.max_budget_usd == 30.0
    out = capsys.readouterr().out
    assert "estimated" in out.lower()
    assert "cursor" in out.lower()


def test_cursor_budget_clear_noop_for_claude():
    args = sc.parse_args([
        "--harness", "claude-code",
        "--max-budget-usd", "30",
        "--no-log",
        "--no-supervisor",
        "sst-translator",
    ])
    harness = sc.get_harness(args.harness)
    harness.apply_budget_constraints(args, loop_count=1)
    assert args.max_budget_usd == 30.0


def test_cursor_overnight_budget_only_ok(capsys):
    """Overnight + budget alone is valid again (estimates meter the gate)."""
    args = sc.parse_args([
        "--harness", "cursor",
        "--overnight",
        "--max-budget-usd", "80",
        "--no-log",
        "--no-supervisor",
        "sst-translator",
    ])
    args.max_budget_usd = 80.0
    args.max_cycles = None
    harness = sc.get_harness("cursor")
    harness.apply_budget_constraints(args, loop_count=0)
    assert args.max_budget_usd == 80.0
    assert "estimated" in capsys.readouterr().out.lower()


def test_cursor_overnight_budget_plus_cycles_ok(capsys):
    args = sc.parse_args([
        "--harness", "cursor",
        "--overnight",
        "--max-budget-usd", "80",
        "--max-cycles", "5",
        "--no-log",
        "--no-supervisor",
        "sst-translator",
    ])
    harness = sc.get_harness("cursor")
    harness.apply_budget_constraints(args, loop_count=0)
    assert args.max_budget_usd == 80.0
    assert args.max_cycles == 5
    assert "estimated" in capsys.readouterr().out.lower()


# ---- Phase 62: Playwright MCP discovery + fable-stdout suppress -------------

def test_discover_playwright_from_project_mcp_json(tmp_path, monkeypatch):
    """Project .cursor/mcp.json servers named/commanded with playwright are found."""
    mcp_dir = tmp_path / ".cursor"
    mcp_dir.mkdir()
    (mcp_dir / "mcp.json").write_text(json.dumps({
        "mcpServers": {
            "playwright-browser": {
                "command": "npx",
                "args": ["@playwright/mcp", "--headless"],
            },
            "memory": {"command": "echo"},
            "cursor-ide-browser": {"command": "ide-only"},
        }
    }))
    # Hide user-global so only project config is visible.
    monkeypatch.setattr(sc.Path, "home", lambda: tmp_path / "nohome")
    found = sc._discover_playwright_mcp_servers(tmp_path)
    assert found == ["playwright-browser"]


def test_discover_playwright_matches_command_not_just_name(tmp_path, monkeypatch):
    mcp_dir = tmp_path / ".cursor"
    mcp_dir.mkdir()
    (mcp_dir / "mcp.json").write_text(json.dumps({
        "mcpServers": {
            "browser": {
                "command": "/opt/bin/playwright-universal-mcp",
                "args": ["--headful"],
            },
        }
    }))
    monkeypatch.setattr(sc.Path, "home", lambda: tmp_path / "nohome")
    assert sc._discover_playwright_mcp_servers(tmp_path) == ["browser"]


def test_discover_playwright_project_wins_over_user(tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    home = tmp_path / "home"
    (proj / ".cursor").mkdir(parents=True)
    (home / ".cursor").mkdir(parents=True)
    (proj / ".cursor" / "mcp.json").write_text(json.dumps({
        "mcpServers": {"playwright-project": {"command": "npx", "args": ["@playwright/mcp"]}}
    }))
    (home / ".cursor" / "mcp.json").write_text(json.dumps({
        "mcpServers": {
            "playwright-project": {"command": "npx", "args": ["@playwright/mcp", "--user"]},
            "playwright-user": {"command": "npx", "args": ["@playwright/mcp"]},
        }
    }))
    monkeypatch.setattr(sc.Path, "home", lambda: home)
    found = sc._discover_playwright_mcp_servers(proj)
    assert found == ["playwright-project", "playwright-user"]


def test_discover_excludes_ide_browser(tmp_path, monkeypatch):
    mcp_dir = tmp_path / ".cursor"
    mcp_dir.mkdir()
    (mcp_dir / "mcp.json").write_text(json.dumps({
        "mcpServers": {
            "cursor-ide-browser": {"command": "whatever"},
            "ide-browser": {"command": "playwright"},  # blocklisted by name
        }
    }))
    monkeypatch.setattr(sc.Path, "home", lambda: tmp_path / "nohome")
    assert sc._discover_playwright_mcp_servers(tmp_path) == []


def test_cursor_playwright_directive_names_servers_and_display(tmp_path, monkeypatch):
    mcp_dir = tmp_path / ".cursor"
    mcp_dir.mkdir()
    (mcp_dir / "mcp.json").write_text(json.dumps({
        "mcpServers": {
            "playwright-mcp": {"command": "npx", "args": ["@playwright/mcp"]},
        }
    }))
    monkeypatch.setattr(sc.Path, "home", lambda: tmp_path / "nohome")
    monkeypatch.setenv("DISPLAY", ":0")
    text = sc._cursor_playwright_directive(tmp_path)
    assert "`playwright-mcp`" in text
    assert "cursor-ide-browser" in text
    assert "DISPLAY is set" in text
    assert "prefer headed" in text


def test_cursor_playwright_directive_no_display_expects_headless(tmp_path, monkeypatch):
    monkeypatch.setattr(sc.Path, "home", lambda: tmp_path / "nohome")
    monkeypatch.delenv("DISPLAY", raising=False)
    text = sc._cursor_playwright_directive(tmp_path)
    assert "No Playwright MCP server found" in text
    assert "no DISPLAY" in text
    assert "headless" in text.lower()


def test_cursor_playwright_directive_force_headless_ignores_display(tmp_path, monkeypatch):
    """--tester-headless must force headless even when DISPLAY is set."""
    monkeypatch.setattr(sc.Path, "home", lambda: tmp_path / "nohome")
    monkeypatch.setenv("DISPLAY", ":0")
    text = sc._cursor_playwright_directive(tmp_path, force_headless=True)
    assert "FORCE HEADLESS" in text
    assert "prefer headed" not in text
    assert "--tester-headless" in text


def test_cursor_tester_headless_flag_forces_headless_in_prompt(tmp_path, monkeypatch):
    """CursorHarness.tester_headless injects force-headless for *-tester only."""
    monkeypatch.setattr(sc.Path, "home", lambda: tmp_path / "nohome")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.chdir(tmp_path)
    h = CursorHarness()
    h.tester_headless = True
    tester_prompt = h.build_command("sst-tester")[-1]
    assert "FORCE HEADLESS" in tester_prompt
    assert sc.TESTER_HEADLESS_DIRECTIVE in tester_prompt
    other_prompt = h.build_command("sst-translator")[-1]
    assert "FORCE HEADLESS" not in other_prompt
    assert sc.TESTER_HEADLESS_DIRECTIVE not in other_prompt


def test_cursor_cold_start_embeds_discovered_playwright(tmp_path, monkeypatch):
    mcp_dir = tmp_path / ".cursor"
    mcp_dir.mkdir()
    (mcp_dir / "mcp.json").write_text(json.dumps({
        "mcpServers": {
            "playwright-browser": {"command": "npx", "args": ["@playwright/mcp"]},
        }
    }))
    monkeypatch.setattr(sc.Path, "home", lambda: tmp_path / "nohome")
    monkeypatch.chdir(tmp_path)
    prompt = CursorHarness().build_command("sst-translator")[-1]
    assert "`playwright-browser`" in prompt
    assert "Never call `cursor-ide-browser`" in prompt


def test_cursor_suppresses_fable_model_note(capsys, monkeypatch):
    """Phase 62: --harness cursor must not print Claude-only fable banner."""
    monkeypatch.setattr(sc, "_RUNTIME_MODEL_CEILING", "opus")
    CursorHarness().print_runtime_model_notes()
    out = capsys.readouterr().out
    assert "fable" not in out.lower()


def test_claude_emits_fable_model_note(capsys, monkeypatch):
    monkeypatch.setattr(sc, "_RUNTIME_MODEL_CEILING", "opus")
    ClaudeCodeHarness().print_runtime_model_notes()
    out = capsys.readouterr().out
    assert "fable disabled" in out
    assert "opus" in out


def test_claude_skips_fable_note_when_ceiling_lifted(capsys, monkeypatch):
    monkeypatch.setattr(sc, "_RUNTIME_MODEL_CEILING", None)
    ClaudeCodeHarness().print_runtime_model_notes()
    assert capsys.readouterr().out == ""


# ---- Phase 64: nested-skill directive + runner max-turns --------------------

def test_cursor_runner_enforces_max_turns_claude_does_not():
    assert CursorHarness().runner_enforces_max_turns() is True
    assert ClaudeCodeHarness().runner_enforces_max_turns() is False


def test_find_skill_md_repo_fallback(tmp_path, monkeypatch):
    """When not installed under .claude/, resolve from skill-set skills/ tree."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sc.Path, "home", lambda: tmp_path / "nohome")
    # sst-translator lives under REPO_ROOT/skills/... — should still resolve.
    found = sc._find_skill_md("sst-translator", str(tmp_path))
    assert found is not None
    assert found.name == "SKILL.md"
    assert "sst-translator" in str(found)


def test_run_skill_cursor_turn_watchdog_kills_at_max_turns(tmp_path, monkeypatch, capsys):
    """Phase 64: runner terminates Cursor subprocess when _turn_proxy >= max_turns."""
    import io
    import threading

    h = CursorHarness()
    h.max_turns = 3

    # Stream 5 assistant frames; watchdog should kill after the 3rd.
    events = []
    for i in range(5):
        events.append(json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": f"turn {i}"}]},
            "session_id": "sess_wd",
        }))
    # Extra lines after the kill point (should not all be consumed if kill is
    # prompt — but our loop breaks on kill, so leftover unread is fine).
    stream = io.StringIO("\n".join(events) + "\n")

    class FakeProc:
        def __init__(self):
            self.stdout = stream
            self._terminated = False
            self.returncode = None

        def terminate(self):
            self._terminated = True
            self.returncode = -15

        def kill(self):
            self._terminated = True
            self.returncode = -9

        def wait(self, timeout=None):
            return self.returncode if self.returncode is not None else 0

        def poll(self):
            return self.returncode

    fake = FakeProc()
    monkeypatch.setattr(
        sc.subprocess, "Popen",
        lambda *a, **k: fake,
    )
    # Avoid real skill-body / brave / playwright prompt work in build_command
    # by stubbing build_command — we only care about the stream loop.
    monkeypatch.setattr(
        CursorHarness, "build_command",
        lambda self, *a, **k: ["cursor-agent", "-p", "noop"],
    )

    rc, rec = sc.run_skill(h, "sst-translator", 0, tmp_path)
    assert fake._terminated is True
    assert rec.get("turn_limit_killed") is True
    assert rec.get("result_subtype") == "error_max_turns"
    assert rec.get("is_error") is True
    assert rec.get("num_turns") == 3
    assert rc != 0
    out = capsys.readouterr().out
    assert "[turn-limit]" in out


def test_run_skill_claude_does_not_runner_kill(tmp_path, monkeypatch):
    """Claude path: runner_enforces_max_turns is False — no terminate on proxy."""
    import io

    h = ClaudeCodeHarness()
    h.max_turns = 2
    events = [
        json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": f"t{i}"}]},
        })
        for i in range(4)
    ] + [
        json.dumps({
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "duration_ms": 10,
            "total_cost_usd": 0,
            "num_turns": 4,
            "modelUsage": {},
        })
    ]
    stream = io.StringIO("\n".join(events) + "\n")

    class FakeProc:
        def __init__(self):
            self.stdout = stream
            self._terminated = False
            self.returncode = 0

        def terminate(self):
            self._terminated = True

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    fake = FakeProc()
    monkeypatch.setattr(sc.subprocess, "Popen", lambda *a, **k: fake)
    monkeypatch.setattr(
        ClaudeCodeHarness, "build_command",
        lambda self, *a, **k: ["claude", "-p", "noop"],
    )
    rc, rec = sc.run_skill(h, "sst-translator", 0, tmp_path)
    assert fake._terminated is False
    assert not rec.get("turn_limit_killed")
    assert rec.get("num_turns") == 4
    assert rc == 0

