"""Tests for Phase 49: sst-tester wind-down directive false-claim fix + looped-standalone session contract.

49.1 — `WIND_DOWN_DIRECTIVE_TEMPLATE` in `bin/skill-chain.py` must NOT make
       an unconditional "the harness enforces a hard ceiling" claim that is
       false for standalone / Skill-tool invocations. Template must use
       conditional language (e.g. "if a hard ceiling is in force") while still
       naming both {hard} and {soft} turn counts and recommending the soft
       budget.

49.2 — `skills/framework/sst-tester/SKILL.md` looped-standalone section must
       explicitly document: (a) write each target's record to the out-of-tree
       state as soon as it is verdicted (not only at run end); (b) do not drain
       a multi-target range past the soft budget in one session; (c) the
       canonical drain is runner-looped (one separately-budgeted subprocess per
       target).
       The Operating Principles wind-down bullet must also acknowledge standalone
       invocations where the hard cap may not be in force.
       Version must be bumped to at least 1.5.0 to record the contract addition.
"""
import importlib.util
import re
from pathlib import Path

_REPO = Path(__file__).parent.parent
_SST_TESTER = _REPO / "skills/framework/sst-tester/SKILL.md"
_CHAIN_PATH = _REPO / "bin" / "skill-chain.py"

_sc_spec = importlib.util.spec_from_file_location("skill_chain", _CHAIN_PATH)
sc = importlib.util.module_from_spec(_sc_spec)
_sc_spec.loader.exec_module(sc)


def _tester_text() -> str:
    assert _SST_TESTER.exists(), f"{_SST_TESTER} must exist"
    return _SST_TESTER.read_text()


# ---------------------------------------------------------------------------
# 49.1 — WIND_DOWN_DIRECTIVE_TEMPLATE conditional language
# ---------------------------------------------------------------------------

def test_wind_down_template_no_unconditional_enforcement_claim():
    """Template must NOT claim the harness unconditionally enforces a cap.

    The old text "the harness enforces a hard ceiling of {hard} agent turns for
    this skill and will cut you off there" is false when the tester is launched
    standalone (Skill tool, manual invocation) where no --max-turns is in force.
    """
    tmpl = sc.WIND_DOWN_DIRECTIVE_TEMPLATE
    assert "the harness enforces a hard ceiling" not in tmpl.lower(), (
        "WIND_DOWN_DIRECTIVE_TEMPLATE must not make an unconditional enforcement "
        "claim; replace with conditional language (e.g. 'if a hard ceiling is in "
        "force it is {hard} turns'). Standalone/Skill-tool launches have no "
        "--max-turns, so the claim is false."
    )


def test_wind_down_template_conditional_cap_language():
    """Template must use conditional language when describing the hard cap.

    The cap description must be guarded so it is accurate both when --max-turns
    is enforced (chain runner) and when it is not (standalone, Skill tool).
    """
    tmpl = sc.WIND_DOWN_DIRECTIVE_TEMPLATE.lower()
    conditional_patterns = [
        r"\bif\b.*\bcap\b",
        r"\bif\b.*\bceiling\b",
        r"\bwhen.{0,30}cap\b",
        r"\bwhen.{0,30}ceiling\b",
        r"\bif.{0,30}in force\b",
    ]
    matched = any(re.search(p, tmpl) for p in conditional_patterns)
    assert matched, (
        "WIND_DOWN_DIRECTIVE_TEMPLATE must use conditional language about the hard "
        "cap (e.g. 'if a hard ceiling is in force it is {hard} turns') so the text "
        "is accurate when --max-turns is absent (standalone launches). None of the "
        f"expected patterns matched: {conditional_patterns!r}"
    )


def test_wind_down_template_retains_format_vars_and_soft_budget():
    """Template must still name both {hard} and {soft} and recommend the soft budget.

    The fix must not lose the self-pacing value: agents should still receive a
    concrete soft budget they can act on.  Additionally the {hard} count must
    now appear within a conditional context (not as an unconditional assertion),
    so this test fails until the fix is applied.
    """
    tmpl = sc.WIND_DOWN_DIRECTIVE_TEMPLATE
    assert "{hard}" in tmpl, "WIND_DOWN_DIRECTIVE_TEMPLATE must still contain {hard}"
    assert "{soft}" in tmpl, "WIND_DOWN_DIRECTIVE_TEMPLATE must still contain {soft}"
    # Soft-budget recommendation must survive the fix.
    assert re.search(r"(?i)(soft|working).{0,40}budget|budget.{0,40}(soft|working)", tmpl), (
        "WIND_DOWN_DIRECTIVE_TEMPLATE must still recommend honoring the soft budget "
        "(e.g. 'treat ~{soft} turns as your working budget')"
    )
    # {hard} must appear near conditional language — it must not appear in a
    # sentence that leads with "the harness enforces" (unconditional).
    idx = tmpl.find("{hard}")
    context = tmpl[max(0, idx - 80):idx + 20].lower()
    assert "enforces" not in context, (
        "WIND_DOWN_DIRECTIVE_TEMPLATE: {hard} must no longer appear in an unconditional "
        "'the harness enforces ...' sentence. Use conditional language around {hard} "
        "(e.g. 'if a hard ceiling is in force it is {hard} turns')."
    )


# ---------------------------------------------------------------------------
# 49.2 — sst-tester SKILL.md: wind-down principle + looped-standalone contract
# ---------------------------------------------------------------------------

def test_sst_tester_wind_down_principle_mentions_standalone():
    """Operating Principles wind-down bullet must acknowledge standalone launches.

    When the tester is invoked standalone (Skill tool, manual /sst-tester) the
    runner-injected directive may arrive without a real --max-turns behind it.
    The principle must tell the agent to honor the soft budget regardless.
    """
    text = _tester_text()
    # Locate the Wind down bullet — match on the bold heading text regardless of
    # trailing punctuation (the heading may end with '.' or ' — ...' etc.).
    m = re.search(r"Wind down before the turn cap.*?(?=\n-\s|\Z)", text, re.DOTALL)
    assert m, "Operating Principles 'Wind down before the turn cap' bullet not found"
    bullet = m.group(0)
    # Must mention standalone or self-pacing context
    has_standalone = any(
        kw in bullet.lower()
        for kw in ("standalone", "self-pac", "without a hard cut", "may not be in force",
                   "regardless", "whether or not")
    )
    assert has_standalone, (
        "The 'Wind down before the turn cap' bullet must acknowledge that when the "
        "tester is invoked standalone the hard cap may not be in force, and instruct "
        f"the agent to honor the soft budget regardless.\nBullet text: {bullet!r}"
    )


def test_sst_tester_looped_standalone_flush_per_target():
    """Looped standalone drain section must require per-target flush.

    Each target's verdict must be written to the out-of-tree state as soon as
    it is verdicted, not only at run end, so a compaction or chop cannot lose
    an in-flight verdict.
    """
    text = _tester_text()
    # Verify the section exists.
    assert re.search(r"#+\s+Looped standalone drain", text, re.IGNORECASE), (
        "Looped standalone drain section not found in sst-tester SKILL.md"
    )
    # Search the full SKILL.md for the flush requirement — the code block inside
    # the section contains `## Tester sweep targets` which breaks a section-
    # boundary regex, so we search the whole file for the distinctive phrase.
    has_flush = re.search(
        r"(as soon as.{0,60}verdit|write.{0,30}each target|"
        r"immediately.{0,60}(writ|flush)|flush.{0,60}per.target|"
        r"each target.{0,60}writ)",
        text,
        re.IGNORECASE,
    )
    assert has_flush, (
        "sst-tester SKILL.md must explicitly require per-target findings flush: "
        "write each target's verdict to the out-of-tree state as soon as it is "
        "verdicted, not only at run end."
    )


def test_sst_tester_looped_standalone_single_session_budget_limit():
    """Looped standalone drain section must prohibit draining past the soft budget in one session.

    A single agent session must not drain a multi-target range past the soft
    budget. Once the budget is approached, the agent must finish the current
    target and exit; the next invocation resumes from the queue cursor.
    """
    text = _tester_text()
    # Verify the section exists.
    assert re.search(r"#+\s+Looped standalone drain", text, re.IGNORECASE), (
        "Looped standalone drain section not found in sst-tester SKILL.md"
    )
    # Search full SKILL.md for the session-limit requirement (see flush test for
    # why we avoid a section-boundary regex).
    has_limit = re.search(
        r"(do not|must not|never).{0,80}(multi.target|range|multiple targets).{0,80}"
        r"(session|budget|ceiling|cap|compaction)",
        text,
        re.IGNORECASE,
    ) or re.search(
        r"(single.{0,20}session|one session).{0,80}(must not|do not|never).{0,80}"
        r"(multi.target|range|multiple targets)",
        text,
        re.IGNORECASE,
    )
    assert has_limit, (
        "sst-tester SKILL.md must state that a single agent session must NOT drain a "
        "multi-target range past the soft budget. Once the budget is approached, the "
        "agent finishes the current target and exits; the next invocation resumes from "
        "the queue cursor."
    )


def test_sst_tester_looped_standalone_canonical_runner_looped():
    """Looped standalone drain section must name runner-looped as the canonical approach.

    `bin/skill-chain.py <tester> --loop N` spawns a fresh, separately-budgeted
    tester per target. The section must explicitly use language such as
    "canonical", "separately-budgeted", or "prefer" to steer manual/Skill-tool
    invocations away from multi-target single sessions.  The existing "one target
    per iteration" wording does not convey the budget-isolation rationale, so
    this test will fail until the new language is added.
    """
    text = _tester_text()
    # Verify the section exists.
    assert re.search(r"#+\s+Looped standalone drain", text, re.IGNORECASE), (
        "Looped standalone drain section not found in sst-tester SKILL.md"
    )
    # Search full SKILL.md for explicit "canonical" or "separately-budgeted"
    # language (see flush test for why we avoid a section-boundary regex).
    has_canonical = re.search(
        r"(canonical|separately.budgeted|separately budgeted)",
        text,
        re.IGNORECASE,
    )
    assert has_canonical, (
        "sst-tester SKILL.md must explicitly name runner-looped as the 'canonical' "
        "approach or note it is 'separately-budgeted', steering manual runs toward one "
        "target per invocation. The existing 'one target per iteration' phrasing does "
        "not convey the budget-isolation rationale."
    )


def test_sst_tester_version_min():
    """sst-tester version must be bumped to at least 1.5.0 to record the contract addition."""
    text = _tester_text()
    m = re.search(r"^version:\s*([\d.]+)\s*$", text, re.MULTILINE)
    assert m, "version: field not found in sst-tester SKILL.md frontmatter"
    parts = [int(x) for x in m.group(1).split(".")]
    major, minor = parts[0], parts[1]
    assert (major, minor) >= (1, 5), (
        f"sst-tester version must be >= 1.5.0 to record the Phase 49 contract "
        f"addition (flush + session limit + conditional wind-down). Found: {m.group(1)!r}"
    )
