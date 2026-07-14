#!/usr/bin/env python3
"""Brave web search + page fetch — Cursor-harness WebSearch/WebFetch substitutes.

Usage:
  bin/brave-web.py search "<query>" [--count N]
  bin/brave-web.py fetch "<url>" [--max-chars N]

Under `--harness cursor`, CursorHarness injects a prompt directive telling the
agent to Shell-invoke this helper instead of Claude Code's native WebSearch /
WebFetch. Claude Code keeps its native tools; this CLI is unused there.

Credential resolution (keys always free-first when both are set):
  1. BRAVE_SEARCH_API_KEY_FREE / BRAVE_SEARCH_API_KEY already in the environment
  2. BRAVE_ENV_FILE pointing at a .env — fills only *missing* keys (merge)
  3. ~/Dev/skill-set/brave.env (base-dir fallback; gitignored; same merge)

Free key is tried first; paid key only when the request itself fails (429 /
auth / timeout / 5xx). A 2xx with empty results does NOT fall through — that
avoids burning paid quota on legitimately-empty queries.

Stdlib only (urllib + html.parser). Exit 0 on success; non-zero on failure
with a short stderr message. stdout is markdown-ish text for the agent.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
DEFAULT_COUNT = 8
DEFAULT_MAX_CHARS = 12000
REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_BRAVE_ENV = REPO_ROOT / "brave.env"
USER_AGENT = "skill-set-brave-web/1.0 (+https://github.com/)"


def _load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ when the key is not already set."""
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


def _resolve_credentials() -> None:
    """Fill *missing* Brave keys from env-file fallbacks (merge, don't short-circuit).

    A free key already in the environment must not block loading a paid key from
    BRAVE_ENV_FILE / brave.env — otherwise free→paid 429 fallback never sees paid.
    `_load_dotenv` only sets keys not already present, so re-running is safe.
    """
    free = os.environ.get("BRAVE_SEARCH_API_KEY_FREE", "").strip()
    paid = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if free and paid:
        return
    env_file = os.environ.get("BRAVE_ENV_FILE", "").strip()
    if env_file:
        _load_dotenv(Path(env_file).expanduser())
        free = os.environ.get("BRAVE_SEARCH_API_KEY_FREE", "").strip()
        paid = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
        if free and paid:
            return
    _load_dotenv(BASE_BRAVE_ENV)


def brave_api_keys() -> list[tuple[str, str]]:
    """Ordered (label, key) pairs: free first, then paid (if distinct)."""
    _resolve_credentials()
    free = os.environ.get("BRAVE_SEARCH_API_KEY_FREE", "").strip()
    paid = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    keys: list[tuple[str, str]] = []
    if free:
        keys.append(("free", free))
    if paid and paid != free:
        keys.append(("paid", paid))
    return keys


def _http_get_json(url: str, headers: dict[str, str], timeout: float = 15.0) -> dict:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8", errors="replace"))


def _http_get_bytes(url: str, timeout: float = 20.0) -> tuple[bytes, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type", "") or ""
        return resp.read(), ctype


def brave_search(query: str, count: int = DEFAULT_COUNT) -> list[dict]:
    """Search Brave; free key first, paid only on request failure."""
    keys = brave_api_keys()
    if not keys:
        raise SystemExit(
            "no Brave API key configured "
            "(set BRAVE_SEARCH_API_KEY_FREE and/or BRAVE_SEARCH_API_KEY, "
            "or BRAVE_ENV_FILE / ~/Dev/skill-set/brave.env)"
        )
    count = max(1, min(int(count), 20))
    params = urllib.parse.urlencode({"q": query, "count": count})
    url = f"{BRAVE_SEARCH_URL}?{params}"
    errors: list[str] = []
    for label, key in keys:
        try:
            data = _http_get_json(
                url,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                    "X-Subscription-Token": key,
                },
            )
            results = []
            for item in (data.get("web") or {}).get("results") or []:
                results.append({
                    "title": item.get("title") or "",
                    "url": item.get("url") or "",
                    "description": item.get("description") or "",
                })
                if len(results) >= count:
                    break
            return results
        except Exception as exc:  # noqa: BLE001 — fall through to next key
            errors.append(f"{label}: {exc}")
            continue
    raise SystemExit(
        "Brave search failed on all keys: " + "; ".join(errors)
    )


class _TextExtractor(HTMLParser):
    """Minimal HTML → visible text (drops script/style/noscript)."""

    _SKIP = {"script", "style", "noscript", "svg", "iframe"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag.lower() in self._SKIP:
            self._skip_depth += 1
        elif tag.lower() in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag.lower() in ("p", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        raw = " ".join(self._chunks)
        raw = html_lib.unescape(raw)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def fetch_page(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Fetch a URL and return readable text (HTML stripped when applicable)."""
    if not url.startswith(("http://", "https://")):
        raise SystemExit(f"fetch url must be http(s): {url!r}")
    max_chars = max(500, min(int(max_chars), 200_000))
    try:
        body, ctype = _http_get_bytes(url)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"fetch HTTP {exc.code}: {exc.reason}") from exc
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"fetch failed: {exc}") from exc

    # Decode
    charset = "utf-8"
    m = re.search(r"charset=([\w-]+)", ctype, re.I)
    if m:
        charset = m.group(1)
    text = body.decode(charset, errors="replace")

    if "html" in ctype.lower() or text.lstrip()[:100].lower().startswith(
        ("<!doctype html", "<html")
    ):
        parser = _TextExtractor()
        try:
            parser.feed(text)
            parser.close()
            text = parser.text()
        except Exception:  # noqa: BLE001 — fall back to raw
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[truncated at {max_chars} chars]"
    return text


def _cmd_search(args: argparse.Namespace) -> int:
    results = brave_search(args.query, count=args.count)
    # Machine-friendly JSON on --json; default markdown for agent readability.
    if args.json:
        print(json.dumps({"query": args.query, "results": results}, indent=2))
        return 0
    print(f"# Brave search: {args.query}")
    print(f"# results: {len(results)}")
    print()
    if not results:
        print("(no results)")
        return 0
    for i, r in enumerate(results, 1):
        print(f"## {i}. {r['title']}")
        print(f"- url: {r['url']}")
        if r["description"]:
            print(f"- {r['description']}")
        print()
    return 0


def _cmd_fetch(args: argparse.Namespace) -> int:
    text = fetch_page(args.url, max_chars=args.max_chars)
    print(f"# Fetch: {args.url}")
    print()
    print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brave-web.py",
        description="Brave Search + page fetch (Cursor harness WebSearch/WebFetch substitutes)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="Web search via Brave Search API")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--count", type=int, default=DEFAULT_COUNT)
    p_search.add_argument(
        "--json", action="store_true", help="Emit JSON instead of markdown"
    )
    p_search.set_defaults(func=_cmd_search)

    p_fetch = sub.add_parser("fetch", help="Fetch a URL as readable text")
    p_fetch.add_argument("url", help="http(s) URL to fetch")
    p_fetch.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    p_fetch.set_defaults(func=_cmd_fetch)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
