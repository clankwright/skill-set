"""Phase 65: cumulative run totals in top-level MANIFEST + stdout summary."""
import importlib.util
from pathlib import Path

_CHAIN_PATH = Path(__file__).parent.parent / "bin" / "skill-chain.py"
_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)


def _skill(
    *,
    duration_ms=0,
    num_turns=0,
    total_cost_usd=0.0,
    model_usage=None,
):
    return {
        "duration_ms": duration_ms,
        "num_turns": num_turns,
        "total_cost_usd": total_cost_usd,
        "model_usage": model_usage or {},
    }


def test_compute_run_totals_flat_skills():
    skills = [
        _skill(
            duration_ms=1000,
            num_turns=10,
            total_cost_usd=1.25,
            model_usage={
                "cursor-grok-4.5-high": {
                    "inputTokens": 100,
                    "outputTokens": 50,
                    "cacheReadInputTokens": 1000,
                    "cacheCreationInputTokens": 20,
                }
            },
        ),
        _skill(
            duration_ms=2500,
            num_turns=5,
            total_cost_usd=0.75,
            model_usage={
                "cursor-grok-4.5-medium": {
                    "inputTokens": 200,
                    "outputTokens": 80,
                    "cacheReadInputTokens": 500,
                    "cacheCreationInputTokens": 10,
                }
            },
        ),
        _skill(),  # empty / missing fields
    ]
    totals = sc._compute_run_totals(skills=skills)
    assert totals["iterations"] == 1
    assert totals["skills"] == 3
    assert totals["duration_ms"] == 3500
    assert totals["num_turns"] == 15
    assert totals["input_tokens"] == 300
    assert totals["output_tokens"] == 130
    assert totals["cache_read_tokens"] == 1500
    assert totals["cache_write_tokens"] == 30
    assert totals["total_cost_usd"] == 2.0


def test_compute_run_totals_multi_iter_matches_sum_of_skill_records():
    """Acceptance: multi-iter MANIFEST totals match sum of skill records."""
    iterations = [
        {
            "skills": [
                _skill(
                    duration_ms=597410,
                    num_turns=50,
                    total_cost_usd=2.4395194,
                    model_usage={
                        "claude-haiku": {
                            "inputTokens": 472,
                            "outputTokens": 18,
                            "cacheReadInputTokens": 0,
                            "cacheCreationInputTokens": 0,
                        },
                        "claude-sonnet": {
                            "inputTokens": 49,
                            "outputTokens": 33084,
                            "cacheReadInputTokens": 4929618,
                            "cacheCreationInputTokens": 123644,
                        },
                    },
                ),
                _skill(
                    duration_ms=100000,
                    num_turns=20,
                    total_cost_usd=0.5,
                    model_usage={
                        "claude-opus": {
                            "inputTokens": 10,
                            "outputTokens": 100,
                            "cacheReadInputTokens": 1000,
                            "cacheCreationInputTokens": 50,
                        }
                    },
                ),
            ]
        },
        {
            "skills": [
                _skill(
                    duration_ms=200000,
                    num_turns=30,
                    total_cost_usd=1.0,
                    model_usage={
                        "cursor-grok-4.5-high": {
                            "inputTokens": 1000,
                            "outputTokens": 200,
                            "cacheReadInputTokens": 5000,
                            "cacheCreationInputTokens": 100,
                        }
                    },
                ),
            ]
        },
    ]
    totals = sc._compute_run_totals(iterations=iterations)

    # Hand-sum of every skill record (the acceptance criterion).
    expect_ms = 597410 + 100000 + 200000
    expect_turns = 50 + 20 + 30
    expect_cost = round(2.4395194 + 0.5 + 1.0, 6)
    expect_in = 472 + 49 + 10 + 1000
    expect_out = 18 + 33084 + 100 + 200
    expect_cr = 0 + 4929618 + 1000 + 5000
    expect_cw = 0 + 123644 + 50 + 100

    assert totals["iterations"] == 2
    assert totals["skills"] == 3
    assert totals["duration_ms"] == expect_ms
    assert totals["num_turns"] == expect_turns
    assert totals["input_tokens"] == expect_in
    assert totals["output_tokens"] == expect_out
    assert totals["cache_read_tokens"] == expect_cr
    assert totals["cache_write_tokens"] == expect_cw
    assert totals["total_cost_usd"] == expect_cost

    # Cross-check against summing _iteration_cost (cost axis only).
    assert abs(
        totals["total_cost_usd"]
        - round(sum(sc._iteration_cost(it) for it in iterations), 6)
    ) < 1e-9


def test_compute_run_totals_empty():
    assert sc._compute_run_totals(iterations=[]) == {
        "iterations": 0,
        "skills": 0,
        "duration_ms": 0,
        "num_turns": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "total_cost_usd": 0.0,
    }
    assert sc._compute_run_totals(skills=[])["iterations"] == 0


def test_format_run_totals_line_shape():
    totals = {
        "iterations": 2,
        "skills": 6,
        "duration_ms": 1234500,
        "num_turns": 180,
        "input_tokens": 1234567,
        "output_tokens": 89012,
        "cache_read_tokens": 5000000,
        "cache_write_tokens": 100000,
        "total_cost_usd": 12.3456,
    }
    line = sc._format_run_totals_line(totals)
    assert line.startswith("[totals] ")
    assert "2 iters" in line
    assert "6 skills" in line
    assert "1234.5s" in line
    assert "180 turns" in line
    assert "1,234,567 in" in line
    assert "89,012 out" in line
    assert "5,000,000 cache-read" in line
    assert "100,000 cache-write" in line
    assert "$12.3456" in line

    labeled = sc._format_run_totals_line(totals, label="totals after iter 3")
    assert labeled.startswith("[totals after iter 3] ")
