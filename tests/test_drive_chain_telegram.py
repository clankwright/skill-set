"""Tests for Telegram env resolution chain (SPEC 34.6).

Originally tested bin/drive-chain.py; repointed to bin/skill-chain.py in Phase
42.5 (drive-chain.py reduced to a shim; _resolve_tg_env lives in skill-chain.py).
"""
import importlib.util
import tempfile
from pathlib import Path

_CHAIN_PATH = Path(__file__).parent.parent / "bin" / "skill-chain.py"
_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

_resolve_tg_env = sc._resolve_tg_env


def _write_env(path: Path, token: str, chat_id: str) -> None:
    path.write_text(f"TELEGRAM_BOT_TOKEN={token}\nTELEGRAM_CHAT_ID={chat_id}\n")


def test_base_dir_fallback_fires_when_no_arg_no_env():
    """When --telegram-env is absent and TELEGRAM_BOT_TOKEN is not in os_env,
    the base-dir telegram.env file should be sourced."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        _write_env(repo_root / "telegram.env", "base_token", "11111")
        result = _resolve_tg_env(None, {}, repo_root)
        assert result.get("TELEGRAM_BOT_TOKEN") == "base_token"
        assert result.get("TELEGRAM_CHAT_ID") == "11111"


def test_telegram_env_arg_beats_base_dir():
    """--telegram-env explicit path wins over the base-dir fallback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        _write_env(repo_root / "telegram.env", "base_token", "11111")
        explicit_env = Path(tmpdir) / "explicit.env"
        _write_env(explicit_env, "explicit_token", "22222")
        result = _resolve_tg_env(explicit_env, {}, repo_root)
        assert result.get("TELEGRAM_BOT_TOKEN") == "explicit_token"
        assert result.get("TELEGRAM_CHAT_ID") == "22222"


def test_caller_exported_bot_token_beats_base_dir():
    """Caller-exported TELEGRAM_BOT_TOKEN in os_env wins over the base-dir fallback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        _write_env(repo_root / "telegram.env", "base_token", "11111")
        os_env = {"TELEGRAM_BOT_TOKEN": "caller_token", "TELEGRAM_CHAT_ID": "33333"}
        result = _resolve_tg_env(None, os_env, repo_root)
        assert result.get("TELEGRAM_BOT_TOKEN") == "caller_token"
        assert result.get("TELEGRAM_CHAT_ID") == "33333"
