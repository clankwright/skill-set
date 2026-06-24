"""Tests for Phase 50: transient 5xx server-error exponential-backoff retry.

50.1 — Capture an overload_signal distinct from rate_limit_signal.
        Detection sources: (a) result-frame api_error_status in OVERLOAD_HTTP_STATUSES
        with is_error=true; (b) api_retry system events count onto overload_retry_events;
        (c) text fallback OVERLOAD_TEXT_RE in non-JSON output lines.
        Priority: if BOTH signals appear (should not happen), rate-limit path wins.

50.2 — Exponential-backoff retry in run_skill_with_retry on overload_signal:
        sleep min(CAP, BASE * 2**attempt) + jitter; retry via --resume; cap at
        OVERLOAD_MAX_RETRIES; give up with overload_aborted=overload_retries_exhausted.
        Independent of --on-rate-limit / --max-pauses-per-session.

50.3 — Documentation: README.md lists --max-overload-retries; resilience section
        distinguishes overload-retry from rate-limit pause;
        sst-chain-driver SKILL.md documents the overload retry layer.
"""
import importlib.util
import io
from pathlib import Path
import unittest.mock as mock

_REPO = Path(__file__).parent.parent
_CHAIN_PATH = _REPO / "bin" / "skill-chain.py"
_CHAIN_DRIVER_SKILL = _REPO / "skills" / "framework" / "sst-chain-driver" / "SKILL.md"
_README = _REPO / "README.md"

_sc_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_sc_spec)
_sc_spec.loader.exec_module(sc)

ClaudeCodeHarness = sc.ClaudeCodeHarness


def _fake_sink():
    class _S:
        def write(self, _): pass
        def close(self): pass
    return _S()


# ---------------------------------------------------------------------------
# 50.1 — Constants
# ---------------------------------------------------------------------------

def test_overload_http_statuses_exists():
    """OVERLOAD_HTTP_STATUSES must be defined and contain the canonical 5xx codes."""
    assert hasattr(sc, "OVERLOAD_HTTP_STATUSES"), \
        "OVERLOAD_HTTP_STATUSES not found on skill_chain module"
    assert {500, 502, 503, 504, 529} <= sc.OVERLOAD_HTTP_STATUSES, (
        "OVERLOAD_HTTP_STATUSES must contain at least {500, 502, 503, 504, 529}; "
        f"got {sc.OVERLOAD_HTTP_STATUSES!r}"
    )


def test_overload_text_re_matches_api_error_5xx():
    """OVERLOAD_TEXT_RE matches 'API Error: 529 Overloaded' (the live error format)."""
    assert hasattr(sc, "OVERLOAD_TEXT_RE"), "OVERLOAD_TEXT_RE not found on module"
    assert sc.OVERLOAD_TEXT_RE.search("API Error: 529 Overloaded") is not None, \
        "OVERLOAD_TEXT_RE must match 'API Error: 529 Overloaded'"


def test_overload_text_re_captures_status_code():
    """OVERLOAD_TEXT_RE group(1) captures the 5xx status code when present."""
    m = sc.OVERLOAD_TEXT_RE.search("API Error: 529 Overloaded")
    assert m is not None
    assert m.group(1) == "529", \
        "OVERLOAD_TEXT_RE group(1) must capture '529' from 'API Error: 529 Overloaded'"


def test_overload_text_re_matches_overloaded_keyword():
    """OVERLOAD_TEXT_RE also matches bare 'overloaded' (fallback when no code)."""
    assert sc.OVERLOAD_TEXT_RE.search("Claude is currently overloaded") is not None, \
        "OVERLOAD_TEXT_RE must match standalone 'overloaded' text"


def test_overload_text_re_no_match_on_4xx():
    """OVERLOAD_TEXT_RE must NOT match 4xx codes (e.g. 'API Error: 429 rate-limited')."""
    assert sc.OVERLOAD_TEXT_RE.search("API Error: 429 rate-limited") is None, \
        "OVERLOAD_TEXT_RE must not match 4xx status codes"


# ---------------------------------------------------------------------------
# 50.1 — handle_event: result-frame structured detection
# ---------------------------------------------------------------------------

def test_handle_event_result_frame_529_sets_overload_signal():
    """handle_event sets overload_signal when result frame has api_error_status=529 + is_error."""
    sink = _fake_sink()
    record: dict = {}
    event = {
        "type": "result",
        "is_error": True,
        "api_error_status": 529,
        "subtype": "error",
        "total_cost_usd": 0,
        "num_turns": 5,
        "duration_ms": 1000,
        "modelUsage": {},
    }
    sc.handle_event(sink, event, record)
    assert "overload_signal" in record, \
        "overload_signal must be set when result frame has api_error_status=529 + is_error"
    assert record["overload_signal"]["status"] == 529
    assert record["overload_signal"]["source"] == "result_frame"


def test_handle_event_result_frame_529_does_not_set_rate_limit_signal():
    """A 529 result frame must NOT set rate_limit_signal (overload != rate-limit)."""
    sink = _fake_sink()
    record: dict = {}
    event = {
        "type": "result",
        "is_error": True,
        "api_error_status": 529,
        "subtype": "error",
        "total_cost_usd": 0,
        "num_turns": 5,
        "duration_ms": 1000,
        "modelUsage": {},
    }
    sc.handle_event(sink, event, record)
    assert "rate_limit_signal" not in record, \
        "rate_limit_signal must NOT be set for a 529 result frame; 529 is overload, not rate-limit"


def test_handle_event_result_frame_non_overload_5xx_sets_overload_signal():
    """Other OVERLOAD_HTTP_STATUSES codes (500, 502, 503, 504) also set overload_signal."""
    for code in (500, 502, 503, 504):
        sink = _fake_sink()
        record: dict = {}
        event = {
            "type": "result",
            "is_error": True,
            "api_error_status": code,
            "subtype": "error",
            "total_cost_usd": 0,
            "num_turns": 1,
            "duration_ms": 100,
            "modelUsage": {},
        }
        sc.handle_event(sink, event, record)
        assert "overload_signal" in record, \
            f"overload_signal must be set for api_error_status={code}"
        assert record["overload_signal"]["status"] == code


def test_handle_event_api_retry_system_event_increments_count():
    """api_retry system events for 5xx codes increment overload_retry_events."""
    sink = _fake_sink()
    record: dict = {}
    event1 = {"type": "system", "subtype": "api_retry", "error_status": 529, "attempt": 1}
    event2 = {"type": "system", "subtype": "api_retry", "error_status": 529, "attempt": 2}
    sc.handle_event(sink, event1, record)
    assert record.get("overload_retry_events") == 1, \
        "First api_retry event must set overload_retry_events=1"
    sc.handle_event(sink, event2, record)
    assert record.get("overload_retry_events") == 2, \
        "Second api_retry event must set overload_retry_events=2"


def test_handle_event_api_retry_non_5xx_does_not_increment():
    """api_retry events for non-5xx codes (e.g. 429) must NOT increment overload_retry_events."""
    sink = _fake_sink()
    record: dict = {}
    event = {"type": "system", "subtype": "api_retry", "error_status": 429, "attempt": 1}
    sc.handle_event(sink, event, record)
    assert record.get("overload_retry_events", 0) == 0, \
        "api_retry for error_status=429 (rate-limit) must not count as overload"


def test_handle_event_rate_limit_event_does_not_set_overload_signal():
    """A structured rate_limit_event must set rate_limit_signal and NOT overload_signal."""
    sink = _fake_sink()
    record: dict = {}
    event = {
        "type": "rate_limit_event",
        "rate_limit_info": {
            "rateLimitType": "token",
            "status": "exceeded",
            "utilization": 1.0,
        },
    }
    sc.handle_event(sink, event, record)
    assert "rate_limit_signal" in record, \
        "rate_limit_event must set rate_limit_signal"
    assert "overload_signal" not in record, \
        "rate_limit_event must NOT set overload_signal"


# ---------------------------------------------------------------------------
# 50.1 — run_skill: text fallback in non-JSON subprocess output
# ---------------------------------------------------------------------------

def test_overload_text_fallback_in_non_json_line():
    """run_skill sets overload_signal when subprocess emits 'API Error: 529' as non-JSON."""
    h = ClaudeCodeHarness()
    non_json_line = "API Error: 529 Overloaded\n"

    mock_proc = mock.MagicMock()
    mock_proc.stdout = iter([non_json_line])
    mock_proc.wait.return_value = 1

    with mock.patch("subprocess.Popen", return_value=mock_proc):
        rc, record = sc.run_skill(h, "test-skill", 0, None)

    assert record.get("overload_signal") is not None, (
        "overload_signal must be set when non-JSON subprocess output contains "
        "'API Error: 529'"
    )
    assert record["overload_signal"]["source"] == "text_fallback"
    assert record["overload_signal"]["status"] == 529


# ---------------------------------------------------------------------------
# 50.2 — run_skill_with_retry: overload backoff constants
# ---------------------------------------------------------------------------

def test_overload_retry_constants_exist():
    """OVERLOAD_MAX_RETRIES, OVERLOAD_BACKOFF_BASE_SECONDS, OVERLOAD_BACKOFF_CAP_SECONDS exist."""
    assert hasattr(sc, "OVERLOAD_MAX_RETRIES"), "OVERLOAD_MAX_RETRIES not found"
    assert hasattr(sc, "OVERLOAD_BACKOFF_BASE_SECONDS"), "OVERLOAD_BACKOFF_BASE_SECONDS not found"
    assert hasattr(sc, "OVERLOAD_BACKOFF_CAP_SECONDS"), "OVERLOAD_BACKOFF_CAP_SECONDS not found"
    assert sc.OVERLOAD_MAX_RETRIES == 10, "OVERLOAD_MAX_RETRIES must default to 10"
    assert sc.OVERLOAD_BACKOFF_BASE_SECONDS == 10, "OVERLOAD_BACKOFF_BASE_SECONDS must be 10"
    assert sc.OVERLOAD_BACKOFF_CAP_SECONDS == 300, "OVERLOAD_BACKOFF_CAP_SECONDS must be 300"


def test_run_skill_with_retry_overload_retries_then_succeeds():
    """A 529-failing-then-succeeding skill is retried and returns rc=0 with overload_retry_count."""
    h = ClaudeCodeHarness()
    call_kwargs: list = []
    ol_records: list = []

    def fake_run_skill(_h, _s, _i, _d, **kwargs):
        call_kwargs.append(kwargs.copy())
        if len(call_kwargs) == 1:
            return (1, {
                "overload_signal": {"status": 529, "source": "result_frame"},
                "session_id": "sess_overload_test",
            })
        return (0, {})

    with mock.patch.object(sc, "run_skill", side_effect=fake_run_skill), \
         mock.patch("time.sleep"), \
         mock.patch.object(sc.random, "randint", return_value=0):
        rc, record = sc.run_skill_with_retry(
            h, "test-skill", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=[],
            max_overload_retries=10,
            overload_retry_records=ol_records,
        )

    assert rc == 0, "Should succeed after retrying once"
    assert len(call_kwargs) == 2, "run_skill must be called twice (first + one retry)"
    assert call_kwargs[0].get("resume_session_id") is None, \
        "first attempt must be cold start"
    assert call_kwargs[1].get("resume_session_id") == "sess_overload_test", \
        "retry must resume from the first call's session_id"
    assert len(ol_records) == 1, "One overload_retry_record must be recorded"
    assert ol_records[0]["status"] == 529


def test_run_skill_with_retry_overload_backoff_exponential():
    """Overload backoff sleeps min(300, BASE * 2**attempt) + jitter (with jitter=0 stubbed)."""
    h = ClaudeCodeHarness()
    call_count = 0

    def fake_always_overload(_h, _s, _i, _d, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 6:
            return (1, {"overload_signal": {"status": 529, "source": "result_frame"}})
        return (0, {})

    sleep_calls: list = []
    with mock.patch.object(sc, "run_skill", side_effect=fake_always_overload), \
         mock.patch.object(sc.time, "sleep", side_effect=sleep_calls.append), \
         mock.patch.object(sc.random, "randint", return_value=0):
        rc, _ = sc.run_skill_with_retry(
            h, "test-skill", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=[],
            max_overload_retries=10,
            overload_retry_records=[],
        )

    assert rc == 0
    # Expected: BASE=10; attempts 0-4 = 10,20,40,80,160; attempt 5 = min(300,320)=300
    expected = [10.0, 20.0, 40.0, 80.0, 160.0, 300.0]
    assert sleep_calls == expected, (
        f"Backoff sleep sequence must be {expected} with zero jitter; got {sleep_calls!r}"
    )


def test_run_skill_with_retry_overload_backoff_capped():
    """Backoff does not exceed OVERLOAD_BACKOFF_CAP_SECONDS."""
    h = ClaudeCodeHarness()
    call_count = 0

    def fake_overload_then_ok(_h, _s, _i, _d, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 8:  # enough attempts to reach the cap
            return (1, {"overload_signal": {"status": 529, "source": "result_frame"}})
        return (0, {})

    sleep_calls: list = []
    with mock.patch.object(sc, "run_skill", side_effect=fake_overload_then_ok), \
         mock.patch.object(sc.time, "sleep", side_effect=sleep_calls.append), \
         mock.patch.object(sc.random, "randint", return_value=0):
        sc.run_skill_with_retry(
            h, "test-skill", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=[],
            max_overload_retries=10,
            overload_retry_records=[],
        )

    cap = sc.OVERLOAD_BACKOFF_CAP_SECONDS
    assert all(s <= cap for s in sleep_calls), (
        f"All backoff sleeps must be <= {cap}s (OVERLOAD_BACKOFF_CAP_SECONDS); "
        f"got max {max(sleep_calls)!r}"
    )


def test_run_skill_with_retry_overload_exhausted():
    """After max_overload_retries consecutive overloads, wrapper gives up with overload_aborted."""
    h = ClaudeCodeHarness()
    call_count = 0

    def fake_always_overload(_h, _s, _i, _d, **kwargs):
        nonlocal call_count
        call_count += 1
        return (1, {"overload_signal": {"status": 529, "source": "result_frame"}})

    with mock.patch.object(sc, "run_skill", side_effect=fake_always_overload), \
         mock.patch("time.sleep"), \
         mock.patch.object(sc.random, "randint", return_value=0):
        rc, record = sc.run_skill_with_retry(
            h, "test-skill", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=[],
            max_overload_retries=10,
            overload_retry_records=[],
        )

    assert rc != 0, "Must return non-zero after exhausting overload retries"
    assert record.get("overload_aborted") == "overload_retries_exhausted", (
        f"record['overload_aborted'] must be 'overload_retries_exhausted'; "
        f"got {record.get('overload_aborted')!r}"
    )
    # 1 original + 10 retries = 11 total calls
    assert call_count == 11, (
        f"run_skill must be called 1 + max_overload_retries = 11 times; got {call_count}"
    )


def test_run_skill_with_retry_ordinary_failure_passes_through():
    """A non-5xx, non-rate-limit failure passes through immediately with zero overload retries."""
    h = ClaudeCodeHarness()
    call_count = 0
    ol_records: list = []

    def fake_ordinary_failure(_h, _s, _i, _d, **kwargs):
        nonlocal call_count
        call_count += 1
        return (1, {})  # no overload_signal, no rate_limit_signal

    with mock.patch.object(sc, "run_skill", side_effect=fake_ordinary_failure), \
         mock.patch("time.sleep") as mock_sleep:
        rc, record = sc.run_skill_with_retry(
            h, "test-skill", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=[],
            max_overload_retries=10,
            overload_retry_records=ol_records,
        )

    assert rc != 0, "Ordinary failure must propagate non-zero exit"
    assert call_count == 1, "run_skill must be called exactly once (no retries)"
    mock_sleep.assert_not_called()
    assert len(ol_records) == 0, "No overload_retry_records for an ordinary failure"
    assert "overload_aborted" not in record


def test_run_skill_with_retry_rate_limit_still_works():
    """The rate-limit pause path is unchanged by the new overload retry path."""
    h = ClaudeCodeHarness()
    pause_records: list = []
    call_kwargs: list = []

    first = (1, {
        "session_id": "sess_rl_test",
        "rate_limit_signal": {"type": "max_usage", "status": "rejected"},
    })

    def fake(_h, _s, _i, _d, **kwargs):
        call_kwargs.append(kwargs.copy())
        if len(call_kwargs) == 1:
            return first
        return (0, {})

    with mock.patch.object(sc, "run_skill", side_effect=fake), \
         mock.patch("time.sleep"):
        rc, record = sc.run_skill_with_retry(
            h, "test-skill", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=pause_records,
            max_overload_retries=10,
            overload_retry_records=[],
        )

    assert rc == 0
    assert len(pause_records) == 1, "One rate-limit pause record must be appended"
    assert "rate_limit_aborted" not in record
    assert "overload_aborted" not in record


def test_run_skill_with_retry_overload_does_not_consume_pause_budget():
    """Overload retries must NOT decrement the rate-limit pause budget (max_pauses)."""
    h = ClaudeCodeHarness()
    pause_records: list = []
    call_count = 0

    def fake_overload_then_ok(_h, _s, _i, _d, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: overload
            return (1, {"overload_signal": {"status": 529, "source": "result_frame"}})
        # Second call: rate-limit
        if call_count == 2:
            return (1, {
                "session_id": "sess_rl",
                "rate_limit_signal": {"type": "max_usage", "status": "rejected"},
            })
        return (0, {})

    with mock.patch.object(sc, "run_skill", side_effect=fake_overload_then_ok), \
         mock.patch("time.sleep"), \
         mock.patch.object(sc.random, "randint", return_value=0):
        rc, record = sc.run_skill_with_retry(
            h, "test-skill", 0, None,
            on_rate_limit="pause",
            max_pause_seconds=3600,
            max_pauses=3,
            pause_records=pause_records,
            max_overload_retries=10,
            overload_retry_records=[],
        )

    assert rc == 0, "Must succeed after overload retry + rate-limit retry"
    # The overload retry must NOT have consumed any of the 3 rate-limit pause budget
    assert len(pause_records) == 1, (
        "Only the rate-limit pause should appear in pause_records; "
        "overload retries must not consume the pause budget"
    )
    assert "rate_limit_aborted" not in record


# ---------------------------------------------------------------------------
# 50.2 — CLI flag --max-overload-retries
# ---------------------------------------------------------------------------

def test_parse_args_max_overload_retries_default():
    """parse_args accepts --max-overload-retries; absent = None (resolved to default in main)."""
    args = sc.parse_args(["sst-dev-cycle"])
    # When not set, args.max_overload_retries should be None (default)
    assert hasattr(args, "max_overload_retries"), \
        "--max-overload-retries must be registered with parse_args"


def test_parse_args_max_overload_retries_explicit():
    """parse_args correctly reads --max-overload-retries N."""
    args = sc.parse_args(["sst-dev-cycle", "--max-overload-retries", "5"])
    assert args.max_overload_retries == 5, \
        "--max-overload-retries 5 must set args.max_overload_retries=5"


# ---------------------------------------------------------------------------
# 50.3 — Documentation
# ---------------------------------------------------------------------------

def test_readme_mentions_max_overload_retries():
    """README.md must document --max-overload-retries (new CLI flag)."""
    text = _README.read_text()
    assert "max-overload-retries" in text, (
        "README.md must list --max-overload-retries as a CLI flag; "
        "update the CLI flags or resilience section"
    )


def test_readme_resilience_distinguishes_overload_from_rate_limit():
    """README.md resilience section must distinguish overload-retry from rate-limit pause."""
    text = _README.read_text()
    # The key distinctions: overload retry is SEPARATE from rate-limit pause
    has_overload_section = (
        "overload" in text.lower()
        and "rate-limit" in text.lower()
        and ("5xx" in text or "529" in text or "overload" in text.lower())
    )
    assert has_overload_section, (
        "README.md must have content discussing overload retry as distinct from "
        "rate-limit pause (mention '5xx' / '529' / 'overload' alongside 'rate-limit')"
    )


def test_chain_driver_skill_md_mentions_overload_retry():
    """sst-chain-driver SKILL.md must document that overload retry happens inside skill-chain.py."""
    text = _CHAIN_DRIVER_SKILL.read_text()
    has_overload = (
        "overload" in text.lower()
        or "5xx" in text.lower()
        or "529" in text
    )
    assert has_overload, (
        "sst-chain-driver SKILL.md must document the overload retry layer "
        "(mention 'overload', '5xx', or '529')"
    )
