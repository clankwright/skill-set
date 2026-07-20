"""Phase 68 tests: the run/iteration log dirs reach every skill IN ITS PROMPT,
and the executor runs under the chain runner's rate-limit pause-and-resume.

68.1 — run_iteration injects `[log-dir]` / `[iter-dir]` / `[iteration]` into
every skill invocation via extra_prompt. The startup print went to the
runner's own stdout, which no skill subprocess can see; three consecutive
supervisor escalations traced run-dir misresolution to that gap.

68.2 — `--skill-args` passthrough (single-skill runs) so argument-taking
skills (sst-executor) run under skill-chain.py instead of a bare
`claude --print` that dies on a session limit. manager-bot.py's
spawn_executor and sst-supervisor §5c both spawn through the wrapper.

68.3 — sst-executor archives its queue file at close-out, never before
execution (the early move falsely reported a dead batch as processed).
"""
import importlib.util
import re
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).parent.parent
_CHAIN_PATH = _REPO / "bin" / "skill-chain.py"
_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

_MANAGER_BOT = (_REPO / "bin" / "manager-bot.py").read_text()
_EXECUTOR = (_REPO / "skills" / "framework" / "sst-executor" / "SKILL.md").read_text()
_SUPERVISOR = (_REPO / "skills" / "framework" / "sst-supervisor" / "SKILL.md").read_text()

_ROUTE_RECORD = {
    "difficulty": "medium",
    "model_floor": "sonnet",
    "effort_floor": "high",
    "item_model": "sonnet",
    "item_effort": "high",
    "effective_model": "sonnet",
    "effective_effort": "high",
}


def _ver(text: str) -> tuple:
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "SKILL.md must carry a SemVer version"
    return tuple(int(g) for g in m.groups())


def _run_iteration_capture(tmp_path, iter_log_dir, iteration, total, **kwargs):
    """Run run_iteration with a fake skill runner; return captured kwargs per call."""
    captured: list[dict] = []

    def fake_rswr(_harness, skill_name, _idx, _log_dir, **kw):
        captured.append({"skill": skill_name, **kw})
        return (0, {})

    with mock.patch.object(sc, "run_skill_with_retry", side_effect=fake_rswr), \
         mock.patch.object(sc, "_resolve_iter_difficulty",
                           return_value=("medium", "todo-next-up")), \
         mock.patch.object(sc, "_resolve_skill_route",
                           return_value=("sonnet", "high", dict(_ROUTE_RECORD))), \
         mock.patch.object(sc, "_git_sha", return_value="abc1234"), \
         mock.patch.object(sc, "_incomplete_cycle_detected", return_value=False):
        rc, _ = sc.run_iteration(
            sc.ClaudeCodeHarness(),
            ["sst-dev-cycle", "sst-dev-review"],
            iter_log_dir,
            None,
            iteration,
            total,
            str(tmp_path),
            **kwargs,
        )
    assert rc == 0
    return captured


def test_looped_iteration_prompt_carries_both_dirs(tmp_path):
    """68.1: looped shape (iter_NN subdir) — [log-dir] is the run dir,
    [iter-dir] the iteration subdir, and every skill in the iter gets it."""
    run_dir = tmp_path / ".skill-runs" / "2026-07-20T00-00-00Z_chain"
    iter_dir = run_dir / "iter_04"
    captured = _run_iteration_capture(tmp_path, iter_dir, 4, 4)
    assert len(captured) == 2
    for call in captured:
        ep = call["extra_prompt"]
        assert f"[log-dir] {run_dir}" in ep
        assert f"[iter-dir] {iter_dir}" in ep
        assert "[iteration] 4/4" in ep
        assert "never create" in ep


def test_flat_iteration_prompt_dirs_identical(tmp_path):
    """68.1: non-looped shape — [log-dir] and [iter-dir] are the same dir."""
    run_dir = tmp_path / ".skill-runs" / "2026-07-20T00-00-00Z_chain"
    captured = _run_iteration_capture(tmp_path, run_dir, 1, 1)
    ep = captured[0]["extra_prompt"]
    assert f"[log-dir] {run_dir}" in ep
    assert f"[iter-dir] {run_dir}" in ep


def test_no_log_dir_no_context_block(tmp_path):
    """68.1: --no-log runs (iter_log_dir=None) inject no phantom paths."""
    captured = _run_iteration_capture(tmp_path, None, 1, 1)
    assert captured[0]["extra_prompt"] == ""


def test_skill_args_reach_prompt(tmp_path):
    """68.2: skill_args ride into the prompt even with no log dir."""
    captured = _run_iteration_capture(
        tmp_path, None, 1, 1,
        skill_args="--process-command /tmp/q.json",
    )
    ep = captured[0]["extra_prompt"]
    assert "exactly these arguments: --process-command /tmp/q.json" in ep


def test_parse_args_accepts_skill_args():
    """68.2: --skill-args parses and defaults to None."""
    args = sc.parse_args(["sst-executor", "--skill-args", "--process-command /x.json"])
    assert args.skill_args == "--process-command /x.json"
    assert sc.parse_args(["sst-executor"]).skill_args is None


def test_manager_bot_spawns_executor_via_skill_chain():
    """68.2: spawn_executor builds a skill-chain.py command with --skill-args
    and rate-limit pause, not a bare `claude --print`."""
    fn = _MANAGER_BOT.split("def spawn_executor", 1)[1].split("\ndef ", 1)[0]
    assert "skill-chain.py" in fn
    assert "--skill-args" in fn
    assert '"--on-rate-limit", "pause"' in fn
    assert "CLAUDE_BIN" not in fn, "executor spawn must not use a bare claude --print"


def test_supervisor_dispatch_uses_wrapper():
    """68.2: sst-supervisor §5c spawns the executor through skill-chain.py,
    detached, with pause-and-resume; no bare claude --print spawn remains."""
    assert _ver(_SUPERVISOR) >= (2, 10, 0)
    assert re.search(
        r"skill-chain\.py sst-executor.*--skill-args", _SUPERVISOR, re.DOTALL)
    assert "--on-rate-limit pause" in _SUPERVISOR
    assert not re.search(
        r'claude --print[^\n]*process-supervisor-request', _SUPERVISOR), \
        "supervisor must not prescribe a bare claude --print executor spawn"


def test_executor_archives_at_close_not_before():
    """68.3: sst-executor keeps the queue file in place until close-out in
    both modes; the early 'then move it to processed/' ordering is gone."""
    assert _ver(_EXECUTOR) >= (1, 1, 0)
    assert "stays IN PLACE until §A3" in _EXECUTOR
    assert "IN PLACE until §B3" in _EXECUTOR
    # Both close-out sections perform the move.
    assert _EXECUTOR.count("Move the queue file to `processed/<basename>` NOW") == 2
    # The old early-move phrasing must not survive in Mode B.
    assert "source the Telegram env, then move it to `processed/" not in _EXECUTOR
