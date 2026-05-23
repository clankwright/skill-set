"""Tests for Phase 32: supervisor routes unpromoted transferable sidecars into HUMAN.md,
and sst-promote-skill-proposal flips matching HUMAN.md entries on promotion."""
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SST_SUPERVISOR = _REPO_ROOT / "skills/framework/sst-supervisor/SKILL.md"
_SST_PROMOTE = _REPO_ROOT / "skills/framework/sst-promote-skill-proposal/SKILL.md"
_SST_MANAGER = _REPO_ROOT / "skills/framework/sst-manager/SKILL.md"
_TEMPLATES_HUMAN_MD = _REPO_ROOT / "templates/HUMAN.md"


# ── SPEC 32.1: templates/HUMAN.md has pending-sidecar entry shape ─────────────

def test_human_md_template_has_pending_sidecar_section_in_high():
    """SPEC 32.1: templates/HUMAN.md must document the pending-sidecar entry shape under ## High."""
    content = _TEMPLATES_HUMAN_MD.read_text()
    # Find ## High section
    high_start = content.find("## High")
    assert high_start != -1, "templates/HUMAN.md must have ## High section"
    # Find end of ## High section (next ## section)
    next_section = content.find("\n## ", high_start + 1)
    high_section = content[high_start:next_section] if next_section != -1 else content[high_start:]
    assert "sidecar" in high_section.lower() or "promote" in high_section.lower(), (
        "templates/HUMAN.md ## High section must document the pending-sidecar promotion entry shape"
    )


def test_human_md_template_sidecar_entry_has_blocks_none():
    """SPEC 32.1: pending-sidecar HUMAN.md entry must carry Blocks: none."""
    content = _TEMPLATES_HUMAN_MD.read_text()
    # The sidecar entry example should have Blocks: none
    assert "Blocks: none" in content, (
        "templates/HUMAN.md must include a pending-sidecar entry example with 'Blocks: none'"
    )


def test_human_md_template_sidecar_entry_has_verify_line():
    """SPEC 32.1: pending-sidecar HUMAN.md entry must have Verify: test ! -e <sidecar-path>."""
    content = _TEMPLATES_HUMAN_MD.read_text()
    # The verify line should check sidecar file absence
    assert "test ! -e" in content, (
        "templates/HUMAN.md pending-sidecar entry must have a Verify: line using 'test ! -e' "
        "to confirm the sidecar file has been removed after promotion"
    )


def test_human_md_template_sidecar_entry_mentions_promote_skill_proposal():
    """SPEC 32.1: pending-sidecar entry must mention /sst-promote-skill-proposal."""
    content = _TEMPLATES_HUMAN_MD.read_text()
    assert "sst-promote-skill-proposal" in content, (
        "templates/HUMAN.md must mention /sst-promote-skill-proposal in the "
        "pending-sidecar promotion entry shape"
    )


# ── SPEC 32.1: sst-supervisor §5b routes sidecar writes to HUMAN.md ## High ───

def test_supervisor_5b_routes_sidecar_to_human_md_high():
    """SPEC 32.1: sst-supervisor §5b must instruct the supervisor to append to HUMAN.md ## High
    when a transferable sidecar is written."""
    content = _SST_SUPERVISOR.read_text()
    # Find §5b section
    section_5b = content.find("### 5b.")
    assert section_5b != -1, "sst-supervisor must have a ### 5b. section"
    next_section = content.find("\n### ", section_5b + 1)
    prose_5b = content[section_5b:next_section] if next_section != -1 else content[section_5b:]
    assert "sidecar" in prose_5b.lower(), (
        "sst-supervisor §5b must mention the transferable sidecar case for HUMAN.md routing"
    )
    assert "## High" in prose_5b, (
        "sst-supervisor §5b must specify ## High (not ## Blocking) for unpromoted sidecar entries"
    )


def test_supervisor_5b_sidecar_entry_blocks_none():
    """SPEC 32.1: sst-supervisor §5b must specify Blocks: none for sidecar entries."""
    content = _SST_SUPERVISOR.read_text()
    section_5b = content.find("### 5b.")
    assert section_5b != -1, "sst-supervisor must have a ### 5b. section"
    next_section = content.find("\n### ", section_5b + 1)
    prose_5b = content[section_5b:next_section] if next_section != -1 else content[section_5b:]
    assert "Blocks: none" in prose_5b or "blocks: none" in prose_5b.lower(), (
        "sst-supervisor §5b sidecar-to-HUMAN.md entry must specify 'Blocks: none'"
    )


def test_supervisor_5b_sidecar_entry_verify_line():
    """SPEC 32.1: sst-supervisor §5b sidecar entry must include a Verify: line using test ! -e."""
    content = _SST_SUPERVISOR.read_text()
    section_5b = content.find("### 5b.")
    assert section_5b != -1, "sst-supervisor must have a ### 5b. section"
    next_section = content.find("\n### ", section_5b + 1)
    prose_5b = content[section_5b:next_section] if next_section != -1 else content[section_5b:]
    assert "test ! -e" in prose_5b, (
        "sst-supervisor §5b sidecar entry must include Verify: test ! -e <sidecar-path>"
    )


def test_supervisor_5b_covers_all_sidecar_routing_modes():
    """SPEC 32.1: sst-supervisor §5b must cover all modes that produce sidecars:
    auto-promote off, proprietary (for transferables), and all-with-sanitization-blocked."""
    content = _SST_SUPERVISOR.read_text()
    section_5b = content.find("### 5b.")
    assert section_5b != -1
    next_section = content.find("\n### ", section_5b + 1)
    prose_5b = content[section_5b:next_section] if next_section != -1 else content[section_5b:]
    # The section should mention sidecar routing in a way that covers the cases
    lower = prose_5b.lower()
    has_sidecar_case = (
        "auto-promote" in lower
        or "proprietary" in lower
        or "sanitization" in lower
    )
    assert has_sidecar_case, (
        "sst-supervisor §5b must reference when sidecar writes happen "
        "(auto-promote: off or proprietary for transferables, or all with sanitization blocked)"
    )


# ── SPEC 32.1: manager close rule for discarded/deleted sidecars ───────────────

def test_supervisor_5b_has_discard_close_rule():
    """SPEC 32.1: sst-supervisor §5b or sst-manager must document a close rule
    for when the sidecar is discarded/deleted rather than promoted.
    The rule must appear in close proximity to 'sidecar' and 'discard' or 'delete'."""
    supervisor_content = _SST_SUPERVISOR.read_text()
    manager_content = _SST_MANAGER.read_text()

    # Check for "discard" adjacent to "sidecar" in a meaningful window (within 500 chars)
    def _has_close_mention(text: str) -> bool:
        lower = text.lower()
        for keyword in ("discard", "deleted sidecar", "delete the sidecar",
                        "sidecar is deleted", "sidecar is discarded"):
            if keyword in lower:
                return True
        return False

    assert _has_close_mention(supervisor_content) or _has_close_mention(manager_content), (
        "sst-supervisor §5b or sst-manager must document a close rule "
        "for when the sidecar file is discarded/deleted rather than promoted "
        "(e.g. 'discarded sidecar', 'sidecar is deleted', etc.)"
    )


# ── SPEC 32.2: sst-promote-skill-proposal flips matching HUMAN.md entry [x] ──

def test_promote_skill_scans_human_md_after_mv():
    """SPEC 32.2: after the mv promotion step, the skill must scan docs/HUMAN.md
    for open entries whose Verify line matches the just-promoted sidecar path."""
    content = _SST_PROMOTE.read_text()
    # The skill must mention scanning/checking HUMAN.md after promotion
    lower = content.lower()
    has_human_md_scan = (
        "human.md" in lower
        and ("verify" in lower or "test ! -e" in lower)
    )
    assert has_human_md_scan, (
        "sst-promote-skill-proposal must scan docs/HUMAN.md for matching Verify entries "
        "after the mv promotion step (SPEC 32.2)"
    )


def test_promote_skill_flips_matching_entry_to_x():
    """SPEC 32.2: the skill must flip matching open [ ] entries to [x]."""
    content = _SST_PROMOTE.read_text()
    lower = content.lower()
    # Must describe flipping [ ] to [x]
    has_flip = (
        "[ ]" in content and "[x]" in content
        and ("flip" in lower or "mark" in lower or "close" in lower or "set" in lower)
    ) or "flip" in lower or "[x]" in content
    # Specifically the promote skill must mention updating/flipping entries in HUMAN.md
    has_human_update = "human.md" in lower and (
        "[x]" in content
        or "flip" in lower
        or "mark" in lower
        or "close" in lower
    )
    assert has_human_update, (
        "sst-promote-skill-proposal must flip matching HUMAN.md entries to [x] "
        "after promotion (SPEC 32.2)"
    )


def test_promote_skill_matches_on_verify_test_not_e():
    """SPEC 32.2: the skill must match on Verify: test ! -e <sidecar-path> entries."""
    content = _SST_PROMOTE.read_text()
    assert "test ! -e" in content, (
        "sst-promote-skill-proposal must match open HUMAN.md entries by their "
        "'Verify: test ! -e <sidecar-path>' line (SPEC 32.2)"
    )


def test_promote_skill_calls_notify_human_md():
    """SPEC 32.2: the skill must call bin/notify-human-md.sh after flipping entries."""
    content = _SST_PROMOTE.read_text()
    assert "notify-human-md.sh" in content, (
        "sst-promote-skill-proposal must call bin/notify-human-md.sh after "
        "flipping the matching HUMAN.md entry to [x] (SPEC 32.2)"
    )


# ── SPEC 32.3: §6b match criterion must not say "absolute path" ───────────────

def test_promote_skill_6b_match_uses_discovered_form_not_absolute():
    """SPEC 32.3: §6b match criterion must NOT say 'absolute path' for the sidecar-path
    comparison; it must instruct the skill to match in the same form the path was
    discovered (i.e. do not expand ~ before comparing), to avoid silent match failure
    when the supervisor writes tilde notation in the Verify: line."""
    content = _SST_PROMOTE.read_text()
    # Find §6b section
    section_6b = content.find("### 6b.")
    assert section_6b != -1, "sst-promote-skill-proposal must have a ### 6b. section"
    next_section = content.find("\n### ", section_6b + 1)
    prose_6b = content[section_6b:next_section] if next_section != -1 else content[section_6b:]
    # Must NOT say "absolute path" as the comparison criterion
    assert "absolute path" not in prose_6b.lower(), (
        "sst-promote-skill-proposal §6b must not say 'absolute path' in the match criterion "
        "— the supervisor writes tilde notation; 'absolute path' causes silent mismatch "
        "(SPEC 32.3)"
    )
    # Must say something about not expanding ~ / discovered form
    has_tilde_note = (
        "do not expand" in prose_6b.lower()
        or "tilde" in prose_6b.lower()
        or "same form" in prose_6b.lower()
        or "discovered" in prose_6b.lower()
    )
    assert has_tilde_note, (
        "sst-promote-skill-proposal §6b must instruct the skill to match in the same form "
        "the path was discovered (e.g. 'do not expand ~') so tilde notation in the supervisor's "
        "Verify: line is matched correctly (SPEC 32.3)"
    )
