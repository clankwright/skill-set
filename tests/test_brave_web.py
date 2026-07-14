"""Tests for bin/brave-web.py — free-key-first Brave search + page fetch."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

_HELPER = Path(__file__).parent.parent / "bin" / "brave-web.py"
_spec = importlib.util.spec_from_file_location("brave_web", _HELPER)
bw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bw)


def _set_keys(monkeypatch, free=None, paid=None):
    for name, val in [
        ("BRAVE_SEARCH_API_KEY_FREE", free),
        ("BRAVE_SEARCH_API_KEY", paid),
        ("BRAVE_ENV_FILE", None),
    ]:
        if val is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, val)


class TestBraveApiKeys:
    def test_free_first_then_paid(self, monkeypatch):
        _set_keys(monkeypatch, free="F", paid="P")
        assert bw.brave_api_keys() == [("free", "F"), ("paid", "P")]

    def test_only_paid(self, monkeypatch):
        _set_keys(monkeypatch, free=None, paid="P")
        assert bw.brave_api_keys() == [("paid", "P")]

    def test_identical_keys_not_duplicated(self, monkeypatch):
        _set_keys(monkeypatch, free="X", paid="X")
        assert bw.brave_api_keys() == [("free", "X")]

    def test_neither(self, monkeypatch, tmp_path):
        _set_keys(monkeypatch)
        # Prevent base-dir brave.env from leaking into the test.
        monkeypatch.setattr(bw, "BASE_BRAVE_ENV", tmp_path / "missing.env")
        assert bw.brave_api_keys() == []

    def test_env_file_loads_when_keys_unset(self, monkeypatch, tmp_path):
        _set_keys(monkeypatch)
        env = tmp_path / "brave.env"
        env.write_text("BRAVE_SEARCH_API_KEY_FREE=FROMFILE\n", encoding="utf-8")
        monkeypatch.setenv("BRAVE_ENV_FILE", str(env))
        monkeypatch.setattr(bw, "BASE_BRAVE_ENV", tmp_path / "missing.env")
        assert bw.brave_api_keys() == [("free", "FROMFILE")]

    def test_free_in_env_merges_paid_from_file(self, monkeypatch, tmp_path):
        """Free already exported must not block paid from BRAVE_ENV_FILE (61.3)."""
        _set_keys(monkeypatch, free="F", paid=None)
        env = tmp_path / "brave.env"
        env.write_text("BRAVE_SEARCH_API_KEY=PAIDFILE\n", encoding="utf-8")
        monkeypatch.setenv("BRAVE_ENV_FILE", str(env))
        monkeypatch.setattr(bw, "BASE_BRAVE_ENV", tmp_path / "missing.env")
        assert bw.brave_api_keys() == [("free", "F"), ("paid", "PAIDFILE")]

    def test_paid_in_env_merges_free_from_file(self, monkeypatch, tmp_path):
        _set_keys(monkeypatch, free=None, paid="P")
        env = tmp_path / "brave.env"
        env.write_text("BRAVE_SEARCH_API_KEY_FREE=FREEFILE\n", encoding="utf-8")
        monkeypatch.setenv("BRAVE_ENV_FILE", str(env))
        monkeypatch.setattr(bw, "BASE_BRAVE_ENV", tmp_path / "missing.env")
        assert bw.brave_api_keys() == [("free", "FREEFILE"), ("paid", "P")]

    def test_env_key_not_overwritten_by_file(self, monkeypatch, tmp_path):
        _set_keys(monkeypatch, free="ENVFREE", paid=None)
        env = tmp_path / "brave.env"
        env.write_text(
            "BRAVE_SEARCH_API_KEY_FREE=FILEFREE\nBRAVE_SEARCH_API_KEY=FILEPAID\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("BRAVE_ENV_FILE", str(env))
        monkeypatch.setattr(bw, "BASE_BRAVE_ENV", tmp_path / "missing.env")
        assert bw.brave_api_keys() == [("free", "ENVFREE"), ("paid", "FILEPAID")]


class TestBraveSearchFallback:
    def test_uses_free_on_success(self, monkeypatch):
        _set_keys(monkeypatch, free="F", paid="P")
        seen = []

        def fake_get(url, headers, timeout=15.0):
            seen.append(headers["X-Subscription-Token"])
            return {"web": {"results": [
                {"title": "t", "url": "https://ex", "description": "d"},
            ]}}

        monkeypatch.setattr(bw, "_http_get_json", fake_get)
        out = bw.brave_search("q", count=5)
        assert seen == ["F"]
        assert out[0]["title"] == "t"

    def test_falls_through_to_paid_on_free_failure(self, monkeypatch):
        _set_keys(monkeypatch, free="F", paid="P")
        seen = []

        def fake_get(url, headers, timeout=15.0):
            tok = headers["X-Subscription-Token"]
            seen.append(tok)
            if tok == "F":
                raise RuntimeError("429 quota exceeded")
            return {"web": {"results": [
                {"title": "paid", "url": "https://ex", "description": "d"},
            ]}}

        monkeypatch.setattr(bw, "_http_get_json", fake_get)
        out = bw.brave_search("q")
        assert seen == ["F", "P"]
        assert out[0]["title"] == "paid"

    def test_empty_free_results_does_not_try_paid(self, monkeypatch):
        _set_keys(monkeypatch, free="F", paid="P")
        seen = []

        def fake_get(url, headers, timeout=15.0):
            seen.append(headers["X-Subscription-Token"])
            return {"web": {"results": []}}

        monkeypatch.setattr(bw, "_http_get_json", fake_get)
        assert bw.brave_search("q") == []
        assert seen == ["F"]

    def test_no_keys_exits(self, monkeypatch, tmp_path):
        _set_keys(monkeypatch)
        monkeypatch.setattr(bw, "BASE_BRAVE_ENV", tmp_path / "missing.env")
        with pytest.raises(SystemExit, match="no Brave API key"):
            bw.brave_search("q")


class TestFetchPage:
    def test_strips_html(self, monkeypatch):
        html = b"<html><head><script>x()</script></head><body><h1>Hi</h1><p>Body</p></body></html>"

        def fake_get(url, timeout=20.0):
            return html, "text/html; charset=utf-8"

        monkeypatch.setattr(bw, "_http_get_bytes", fake_get)
        text = bw.fetch_page("https://example.com/page")
        assert "Hi" in text
        assert "Body" in text
        assert "x()" not in text

    def test_rejects_non_http(self):
        with pytest.raises(SystemExit, match="http"):
            bw.fetch_page("file:///etc/passwd")

    def test_truncates(self, monkeypatch):
        monkeypatch.setattr(
            bw, "_http_get_bytes",
            lambda url, timeout=20.0: (b"x" * 5000, "text/plain"),
        )
        text = bw.fetch_page("https://example.com/a", max_chars=1000)
        assert "truncated at 1000" in text


class TestCli:
    def test_search_json(self, monkeypatch, capsys):
        _set_keys(monkeypatch, free="F", paid=None)
        monkeypatch.setattr(
            bw, "_http_get_json",
            lambda *a, **k: {"web": {"results": [
                {"title": "T", "url": "https://u", "description": "D"},
            ]}},
        )
        rc = bw.main(["search", "hello", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["results"][0]["title"] == "T"

    def test_fetch_cli(self, monkeypatch, capsys):
        monkeypatch.setattr(
            bw, "_http_get_bytes",
            lambda url, timeout=20.0: (b"<html><body>Hello world</body></html>",
                                       "text/html"),
        )
        rc = bw.main(["fetch", "https://example.com"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Hello world" in out
        assert "# Fetch:" in out
