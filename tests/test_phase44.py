"""Tests for Phase 44.1 + 44.2: the standalone terminal-invocable tester mode.

44.1 — `skills/framework/sst-tester/SKILL.md` documents an OPTIONAL standalone
       mode (distinct from the in-chain mode) triggered by `--phase <id>` and/or
       `--todos <ref...>`: mode dispatch (D1), scope resolution (D2),
       iterate-all/collect-all (D3), the standalone artifact/findings location
       (D4), and that standalone stays read-only / out-of-tree / full-teardown.
       Version bumped past the 1.0.0 initial author. No port literal / project noun.
44.2 — phase/todo scope resolution is documented with an example for each input,
       and a tests/ test derives the surface set from a sample SPEC phase + a
       sample `## Just shipped` todo list using the documented D2 rules.

The resolution helpers below ARE the documented D2 algorithm in executable form;
the test asserts they yield the right surface set from the fixtures so the prose
rule is pinned to a concrete, checkable behavior (mirrors the 41.2 fixture pattern).
"""
import re
from pathlib import Path

_REPO = Path(__file__).parent.parent
_SST_TESTER = _REPO / "skills/framework/sst-tester/SKILL.md"
_PHASE_FIXTURE = _REPO / "tests/fixtures/sample-phase-spec.md"
_TODOS_FIXTURE = _REPO / "tests/fixtures/sample-just-shipped.md"

# Front-end path predicate (D2 default allowlist; a wrapper may extend it).
_FE_EXTS = {".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".html", ".css", ".scss"}
_PATH_RE = re.compile(r"`([^`]+)`")


def _tester_text() -> str:
    assert _SST_TESTER.exists(), f"{_SST_TESTER} must exist"
    return _SST_TESTER.read_text()


def _frontmatter(text: str) -> dict:
    assert text.startswith("---\n"), "SKILL.md must open with a --- frontmatter fence"
    end = text.index("\n---", 4)
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([a-z][a-z0-9-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


# ---------------------------------------------------------------------------
# D2 resolution, executable form (what the test "derives")
# ---------------------------------------------------------------------------

def _cited_paths(item_text: str) -> list:
    """Backtick-quoted tokens that look like file paths."""
    out = []
    for tok in _PATH_RE.findall(item_text):
        tok = tok.strip()
        if "/" in tok and "." in Path(tok).name:
            out.append(tok)
    return out


def _is_front_end(path: str) -> bool:
    return Path(path).suffix.lower() in _FE_EXTS


def _front_end_surfaces(item_text: str) -> list:
    return [p for p in _cited_paths(item_text) if _is_front_end(p)]


def resolve_phase_surfaces(spec_text: str, phase_id: str) -> dict:
    """`--phase <id>` -> {spec_item_id: [front-end surface paths]} for every
    `- [x]` item under `### Phase <id>` that touches a front-end path. Open
    `- [ ]` items and non-front-end items are excluded."""
    lines = spec_text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"^###\s+Phase\s+{re.escape(phase_id)}\b", ln):
            start = i
            break
    if start is None:
        return {}
    surfaces = {}
    for ln in lines[start + 1:]:
        if re.match(r"^###?\s+", ln):  # next phase/section header ends the block
            break
        m = re.match(r"^- \[x\]\s+(\S+)", ln)
        if not m:
            continue
        item_id = m.group(1)
        fe = _front_end_surfaces(ln)
        if fe:
            surfaces[item_id] = fe
    return surfaces


def resolve_todo_surfaces(todo_text: str, refs: list) -> dict:
    """`--todos <ref...>` -> {ref: [front-end surface paths]} for each ref that
    matches a `## Just shipped` entry (by leading id token or case-insensitive
    substring) and whose entry touches a front-end path."""
    entries = [ln for ln in todo_text.splitlines() if ln.startswith("- ")]
    out = {}
    for ref in refs:
        matched = None
        for e in entries:
            body = e[2:].strip()
            lead = body.split()[0] if body else ""
            if lead == ref or ref.lower() in body.lower():
                matched = e
                break
        if matched is None:
            continue
        fe = _front_end_surfaces(matched)
        if fe:
            out[ref] = fe
    return out


# ---------------------------------------------------------------------------
# 44.2: scope resolution derives the right surface set from the fixtures
# ---------------------------------------------------------------------------

def test_phase_fixture_resolves_only_closed_front_end_items():
    surfaces = resolve_phase_surfaces(_PHASE_FIXTURE.read_text(), "7")
    # 7.1 (checkout.tsx + CartSummary.tsx) and 7.2 (LeadForm.jsx) are closed + front-end.
    assert set(surfaces.keys()) == {"7.1", "7.2"}, surfaces
    assert any(p.endswith("checkout.tsx") for p in surfaces["7.1"])
    assert any(p.endswith("CartSummary.tsx") for p in surfaces["7.1"])
    assert surfaces["7.2"] == ["web/src/components/LeadForm.jsx"]


def test_phase_fixture_excludes_backend_docs_and_open_items():
    surfaces = resolve_phase_surfaces(_PHASE_FIXTURE.read_text(), "7")
    assert "7.3" not in surfaces, "backend-only item must not resolve to a surface"
    assert "7.4" not in surfaces, "docs-only item must not resolve to a surface"
    assert "7.5" not in surfaces, "still-open [ ] item must be excluded from the sweep"


def test_phase_resolution_unknown_phase_is_empty():
    assert resolve_phase_surfaces(_PHASE_FIXTURE.read_text(), "99") == {}


def test_todos_fixture_resolves_by_id_and_substring():
    todo = _TODOS_FIXTURE.read_text()
    # 7.2 by leading id token; "settings" substring matches the 6.9 entry.
    surfaces = resolve_todo_surfaces(todo, ["7.2", "settings"])
    assert surfaces["7.2"] == ["web/src/components/LeadForm.jsx"]
    assert surfaces["settings"] == ["web/src/routes/settings.tsx"]


def test_todos_fixture_excludes_backend_entry():
    todo = _TODOS_FIXTURE.read_text()
    # 7.3 matches a real entry but it touches only api/*.py -> no surface.
    surfaces = resolve_todo_surfaces(todo, ["7.3"])
    assert "7.3" not in surfaces


def test_todos_unmatched_ref_is_dropped():
    surfaces = resolve_todo_surfaces(_TODOS_FIXTURE.read_text(), ["9.9"])
    assert surfaces == {}


def test_front_end_predicate_extension_set():
    assert _is_front_end("web/src/routes/checkout.tsx")
    assert _is_front_end("a/b/widget.vue")
    assert not _is_front_end("api/webhooks/stripe.py")
    assert not _is_front_end("docs/STOREFRONT.md")


# ---------------------------------------------------------------------------
# 44.1: SKILL.md documents the standalone mode
# ---------------------------------------------------------------------------

def test_version_bumped_past_initial_author():
    fm = _frontmatter(_tester_text())
    assert fm.get("version") != "1.0.0", "version must be bumped for the standalone-mode addition"
    # still a 3-part semver, minor bumped to >= 1.1.0
    parts = fm["version"].split(".")
    assert len(parts) == 3 and parts[0] == "1" and int(parts[1]) >= 1, fm.get("version")


def test_documents_standalone_arg_surface():
    text = _tester_text()
    assert "--phase" in text, "must document the --phase <id> arg"
    assert "--todos" in text, "must document the --todos <ref...> arg"


def test_documents_mode_dispatch_d1():
    """D1: detect in-chain vs standalone from args (no scope args -> in-chain)."""
    text = _tester_text().lower()
    assert "standalone" in text, "must name the standalone mode"
    assert "in-chain" in text or "in chain" in text, "must contrast with the in-chain mode"


def test_documents_scope_resolution_d2():
    text = _tester_text()
    low = text.lower()
    # phase -> closed [x] items touching a front-end surface
    assert "[x]" in text and "front-end" in low, "must document [x]-item + front-end resolution"
    # todos -> Just shipped entries
    assert "just shipped" in low, "must resolve --todos against the Just shipped entries"


def test_documents_iterate_all_collect_all_d3():
    low = _tester_text().lower()
    assert "iterate-all" in low or "iterate all" in low or "every resolved surface" in low
    assert "does not stop at the first failure" in low or "accumulat" in low


def test_documents_standalone_output_location_d4():
    text = _tester_text()
    # standalone writes findings to the out-of-tree state dir, not a chain run-log dir
    assert "~/.claude/state/sst-tester/" in text, "standalone findings go to the out-of-tree state dir"
    assert "tester-findings" in text


def test_standalone_preserves_readonly_outoftree_teardown_guarantees():
    low = _tester_text().lower()
    assert "read-only" in low
    assert "out-of-tree" in low or "out of tree" in low
    assert "teardown" in low


def test_no_port_literal_or_project_noun():
    """Transferable hygiene: no concrete port and no project-specific noun."""
    text = _tester_text()
    assert not re.search(r"localhost:\d{2,5}", text), "no concrete port:literal"
    assert not re.search(r":\d{4}\b", text), "no bare 4-digit port literal"
    for noun in ("claim_management", "dahrouge", "botlab", "ssp-cm"):
        assert noun.lower() not in text.lower(), f"transferable must not name {noun}"
