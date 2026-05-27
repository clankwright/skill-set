#!/usr/bin/env python3
"""validate-frontmatter.py — validate the YAML frontmatter of every SKILL.md.

Walks `skills/**/SKILL.md` recursively (or paths passed on the command line),
parses the top YAML frontmatter (the block between two `---` lines at the
very top of the file), and validates it against `schema/skill-set.schema.json`.

Also enforces a structural rule the JSON schema can't easily express:
the `name:` field must equal the parent folder name (the folder directly
containing SKILL.md — categories above that are ignored).

Usage:
    bin/validate-frontmatter.py                 # validate all skills/**/SKILL.md
    bin/validate-frontmatter.py path/to/SKILL.md ...

Exit codes:
    0 — all valid
    2 — at least one violation (each printed to stderr)
    1 — usage / dep error
"""

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("validate-frontmatter requires PyYAML (`pip install pyyaml`)", file=sys.stderr)
    sys.exit(1)

try:
    import jsonschema
except ImportError:
    print("validate-frontmatter requires jsonschema (`pip install jsonschema`)", file=sys.stderr)
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "skill-set.schema.json"
CHAIN_SCHEMA_PATH = REPO_ROOT / "schema" / "skill-chain.schema.json"
SKILLS_DIR = REPO_ROOT / "skills"
CHAINS_DIR = REPO_ROOT / "chains"
SPEC_DEFAULT_PATH = REPO_ROOT / "docs" / "SPEC.md"
TODO_DEFAULT_PATH = REPO_ROOT / "docs" / "TODO.md"

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def extract_frontmatter(text: str) -> tuple[dict | None, str | None]:
    """Returns (frontmatter_dict_or_None, error_message_or_None)."""
    m = FRONTMATTER_RE.search(text)
    if not m:
        return None, "no YAML frontmatter (must start with `---\\n...\\n---`)"
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return None, f"invalid YAML in frontmatter: {e}"
    if not isinstance(data, dict):
        return None, "frontmatter is not a YAML mapping"
    return data, None


def validate_one(path: Path, schema: dict) -> list[str]:
    """Returns a list of error messages (empty if valid)."""
    errors: list[str] = []
    if not path.exists():
        return [f"{path}: file does not exist"]

    text = path.read_text(encoding="utf-8")
    fm, err = extract_frontmatter(text)
    if err is not None:
        return [f"{path}: {err}"]
    assert fm is not None  # err is None implies fm is set

    # Schema check (auto-detect draft from the schema's $schema field).
    ValidatorClass = jsonschema.validators.validator_for(schema)
    validator = ValidatorClass(schema)
    for err in sorted(validator.iter_errors(fm), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{path}: frontmatter @ {loc}: {err.message}")

    # Folder-name == name field.
    expected_name = path.parent.name
    actual_name = fm.get("name")
    if actual_name and actual_name != expected_name:
        errors.append(
            f"{path}: frontmatter `name: {actual_name!r}` does not match folder name "
            f"{expected_name!r} (folder name is the canonical identifier)"
        )

    # Proprietary distinct-name rule: a proprietary skill (one that declares
    # `transferable:`) MUST have a `name:` different from its transferable.
    # Both install under the same harness skills directory, so identical names
    # would collide and install/remove would silently clobber proprietary work.
    # Convention: transferables use prefix `sst-`, proprietary counterparts use
    # `ssp-` (see docs/SPEC.md Skill-set concept).
    transferable = fm.get("transferable")
    if transferable and actual_name and actual_name == transferable:
        suggested = (
            transferable.replace("sst-", "ssp-", 1)
            if transferable.startswith("sst-")
            else f"ssp-{transferable}"
        )
        errors.append(
            f"{path}: proprietary `name: {actual_name!r}` must differ from "
            f"`transferable: {transferable!r}` (use `{suggested}`; "
            f"identical names collide at the harness skills dir)"
        )

    # sst- prefix rule for transferables in this repo's canonical skills/ tree.
    # Proprietary skills (declaring `transferable:`) are exempt because they
    # follow the ssp-/<project>- prefix conventions. Skills validated outside
    # SKILLS_DIR (e.g. a consuming project's own SKILL.md) are also exempt.
    try:
        in_repo_skills = path.resolve().is_relative_to(SKILLS_DIR)
    except AttributeError:
        in_repo_skills = str(path.resolve()).startswith(str(SKILLS_DIR) + "/")
    if in_repo_skills and actual_name and not transferable and not actual_name.startswith("sst-"):
        errors.append(
            f"{path}: transferable skill in this repo MUST use `sst-` prefix "
            f"(got `name: {actual_name!r}`); see docs/SPEC.md 'Skill-set' section"
        )

    return errors


def validate_chain(path: Path, schema: dict) -> list[str]:
    """Validate a chain YAML file against schema/skill-chain.schema.json."""
    errors: list[str] = []
    if not path.exists():
        return [f"{path}: file does not exist"]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return [f"{path}: invalid YAML: {e}"]
    if not isinstance(data, dict):
        return [f"{path}: chain root must be a mapping"]

    ValidatorClass = jsonschema.validators.validator_for(schema)
    validator = ValidatorClass(schema)
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{path}: chain @ {loc}: {err.message}")

    expected_name = path.stem  # filename without .yaml
    actual_name = data.get("name")
    if actual_name and actual_name != expected_name:
        errors.append(
            f"{path}: chain `name: {actual_name!r}` does not match file basename "
            f"{expected_name!r}"
        )
    return errors


SPEC_PATH = REPO_ROOT / "docs" / "SPEC.md"  # legacy alias used by validate_spec_ids
_SPEC_BULLET_ID_RE = re.compile(r"^- \[[ xX]\] (\d+)\.(\d+[a-z]*)[\s:]")
_SPEC_CHECKBOX_RE = re.compile(r"^- \[[ xX]\] ")
_PHASE_HEADER_RE = re.compile(r"^### Phase (\d+)")


def validate_spec_ids(spec_path: Path = SPEC_PATH) -> list[str]:
    """Check SPEC.md: sub-item IDs must be unique within each phase block,
    and every checkbox bullet must carry a stable ID.

    Gaps (void IDs from removed/closed items) are valid and not flagged.
    """
    if not spec_path.exists():
        return []
    errors: list[str] = []
    current_phase: int | None = None
    seen: dict[int, set[str]] = {}
    for lineno, line in enumerate(spec_path.read_text(encoding="utf-8").splitlines(), 1):
        phase_m = _PHASE_HEADER_RE.match(line)
        if phase_m:
            current_phase = int(phase_m.group(1))
            seen.setdefault(current_phase, set())
            continue
        if current_phase is None:
            continue
        id_m = _SPEC_BULLET_ID_RE.match(line)
        if not id_m:
            if _SPEC_CHECKBOX_RE.match(line):
                errors.append(
                    f"{spec_path}:{lineno}: checkbox bullet missing sub-item ID "
                    f"(expected `- [ ] <phase>.<n> ...` or `- [x] <phase>.<n> ...`)"
                )
            continue
        item_phase = int(id_m.group(1))
        item_id = f"{id_m.group(1)}.{id_m.group(2)}"
        if item_phase != current_phase:
            errors.append(
                f"{spec_path}:{lineno}: ID {item_id!r} is under Phase {current_phase} "
                f"header but references Phase {item_phase}"
            )
        if item_id in seen.get(current_phase, set()):
            errors.append(
                f"{spec_path}:{lineno}: duplicate sub-item ID {item_id!r} "
                f"within Phase {current_phase}"
            )
        else:
            seen.setdefault(current_phase, set()).add(item_id)
    return errors


# ---- HUMAN.md validation (Phase 31.9) ----------------------------------------
# Validates docs/HUMAN.md when present. Checks: canonical five-section order,
# H-ID format, open items carry Blocks:, Verify: lines are single commands.
# Absence of the file is not an error (optional per-project doc).

_HUMAN_SECTIONS = ["## Blocking", "## High", "## Medium", "## Low", "## Done"]
# Broad match: any checkbox bullet starting with H (captures raw token for ID check).
_HUMAN_ITEM_BROAD_RE = re.compile(r"^- \[([ xX])\] (H\S+)")
_HUMAN_ID_RE = re.compile(r"^H\d+\.\d+[a-z]*$")
_HUMAN_SECTION_RE = re.compile(r"^## (.+)$")
_HUMAN_VERIFY_RE = re.compile(r"^\s{2,}Verify:\s*(.+)$")
_HUMAN_BLOCKS_RE = re.compile(r"^\s{2,}Blocks:\s*\S")


def validate_human_md(path: Path) -> list[str]:
    """Validate docs/HUMAN.md when present. Returns a list of error strings."""
    if not path.exists():
        return []

    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 1. Canonical five sections must all be present in order.
    found_sections: list[str] = []
    for line in lines:
        m = _HUMAN_SECTION_RE.match(line.rstrip())
        if m:
            header = f"## {m.group(1)}"
            if header in _HUMAN_SECTIONS and header not in found_sections:
                found_sections.append(header)

    for section in _HUMAN_SECTIONS:
        if section not in found_sections:
            errors.append(
                f"{path}: missing required section {section!r}"
            )

    # Check canonical order: each found section's index in _HUMAN_SECTIONS must
    # be strictly increasing compared to the one before it.
    prev_idx = -1
    for section in found_sections:
        idx = _HUMAN_SECTIONS.index(section)
        if idx <= prev_idx:
            errors.append(
                f"{path}: section {section!r} is out of canonical order "
                f"(expected order: {', '.join(_HUMAN_SECTIONS)})"
            )
        prev_idx = idx

    # 2. Per-item checks.
    current_item_id: str | None = None
    item_lineno: int = 0
    item_has_blocks: bool = False
    open_items: list[tuple[int, str]] = []  # (lineno, H-ID) for open items

    def _flush_item() -> None:
        if current_item_id is not None and not item_has_blocks:
            # Only open items require Blocks:
            if any(h_id == current_item_id for _, h_id in open_items):
                errors.append(
                    f"{path}:{item_lineno}: open item {current_item_id!r} "
                    f"is missing required 'Blocks:' line"
                )

    for lineno, line in enumerate(lines, 1):
        item_m = _HUMAN_ITEM_BROAD_RE.match(line)
        if item_m:
            _flush_item()
            state = item_m.group(1)
            h_id = item_m.group(2)
            # Validate H-ID format.
            if not _HUMAN_ID_RE.match(h_id):
                errors.append(
                    f"{path}:{lineno}: invalid H-ID format {h_id!r} "
                    f"(expected H<phase>.<n>, e.g. H3.1)"
                )
            current_item_id = h_id
            current_item_is_open = (state == " ")
            item_lineno = lineno
            item_has_blocks = False
            if current_item_is_open:
                open_items.append((lineno, h_id))
            continue

        if current_item_id is not None:
            if _HUMAN_BLOCKS_RE.match(line):
                item_has_blocks = True
            elif _HUMAN_VERIFY_RE.match(line):
                verify_body = _HUMAN_VERIFY_RE.match(line).group(1).strip()
                if "\n" in verify_body:
                    errors.append(
                        f"{path}:{lineno}: Verify: line must be a single command "
                        f"(no embedded newlines)"
                    )
            # A new ## heading or a blank non-indented line ends the item block.
            elif line and not line.startswith(" ") and not line.startswith("\t"):
                _flush_item()
                current_item_id = None
                item_has_blocks = False

    _flush_item()
    return errors


# ---- validate_spec_item_quality (Phase 38.2) --------------------------------
# Rejects open-ended / unbounded bullets in SPEC.md (open - [ ] items) and
# in the ## Next up section of TODO.md.  A bullet is flagged when its task text
# contains a "standing-activity" marker word (not inside backticks or quotes)
# AND does NOT name a concrete target (file path, backtick-quoted symbol, or
# a <phase>.<n> reference).

# Denylist: words that mark a standing activity rather than a finite deliverable.
_OPEN_ENDED_WORDS: frozenset[str] = frozenset({
    "iterative", "iteratively",
    "ongoing",
    "polish", "polishing",
    "cleanup",
    "housekeeping",
    "miscellaneous", "misc",
    "various",
    "general",
    "improve", "improvement", "improvements", "improving",
    "refactor", "refactoring",
    "maintenance",
})

_NEXT_UP_HEADER_RE = re.compile(r"^## Next up", re.IGNORECASE)
_ANY_SECTION_RE = re.compile(r"^## ")
_BULLET_START_RE = re.compile(r"^- ")


def _strip_quoted_spans(text: str) -> str:
    """Remove backtick, double-quote, and single-quote spans from *text*."""
    text = re.sub(r'`[^`\n]*`', "", text)
    text = re.sub(r'"[^"\n]*"', "", text)
    text = re.sub(r"'[^'\n]*'", "", text)
    return text


def _has_open_ended_word(task_text: str) -> bool:
    """True if *task_text* contains a denylist word not inside backticks/quotes."""
    clean = _strip_quoted_spans(task_text)
    for word in _OPEN_ENDED_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", clean, re.IGNORECASE):
            return True
    return False


def _has_concrete_target(task_text: str) -> bool:
    """True if *task_text* names a concrete target.

    Concrete targets are:
    - Any content inside backticks (symbol, path, command).
    - A slash-delimited file path (e.g. ``bin/validate-frontmatter.py``).
    - A filename with a recognised extension (e.g. ``manager-bot.py``).
    - A phase sub-item reference of the form N.n[letter] (e.g. ``38.2``, ``37.1a``).
    """
    # Backtick-quoted content: symbol or path.
    if re.search(r"`[^`\n]+`", task_text):
        return True
    # Slash-delimited path (at least one slash between word characters).
    if re.search(r"\b\w[\w.\-]*/[\w./\-]+", task_text):
        return True
    # Bare filename with a common tech extension.
    if re.search(
        r"\b[\w\-]+\.(?:py|sh|yaml|yml|json|md|js|ts|html|css|service|toml|cfg|ini|txt)\b",
        task_text,
    ):
        return True
    # Phase/sub-item reference like 38.2 or 37.1a (two or more digits.one-or-more-digits).
    if re.search(r"\b\d{2,}\.\d+[a-z]*\b", task_text):
        return True
    return False


def _extract_task_text_spec(line: str) -> str:
    """Strip the ``- [ ] <id> [difficulty] `` prefix from a SPEC.md bullet line."""
    text = re.sub(r"^- \[ \]\s*", "", line)
    text = re.sub(r"^\d+\.\d+[a-z]*\s*", "", text)   # phase sub-item ID
    text = re.sub(r"^\[[a-z\-]+\]\s*", "", text)      # difficulty bracket [medium] etc
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)    # strip bold markers
    return text


def _extract_task_text_todo(line: str) -> str:
    """Strip the ``- [difficulty] <id>`` prefix and trailing ``— reason:`` from TODO bullet."""
    text = re.sub(r"^- \[[^\]]*\]\s*", "", line)      # remove - [medium] / - [x] etc
    text = re.sub(r"^- ", "", text)                    # remove bare - prefix if no brackets
    text = re.sub(r"^\d+\.\d+[a-z]*\s*", "", text)    # phase sub-item ID
    # Strip trailing reason/source annotation: "— reason: ..." or "- reason: ..."
    text = re.sub(r"\s*[—\-]\s*(?:reason|source)\s*:.*$", "", text, flags=re.IGNORECASE)
    return text


def validate_spec_item_quality(
    spec_path: "Path | None" = None,
    todo_path: "Path | None" = None,
) -> list[str]:
    """Fail on open-ended / unbounded items in SPEC.md and TODO.md.

    Checks:
    - Every open ``- [ ]`` checkbox in *spec_path* (SPEC.md).
    - Every bullet in the ``## Next up`` section of *todo_path* (TODO.md).

    A bullet is flagged when its task-description span contains a
    standing-activity marker word (not inside backticks/quotes) AND does not
    name a concrete target (file path, backtick-quoted symbol, or
    ``<phase>.<n>`` reference).
    """
    if spec_path is None:
        spec_path = SPEC_DEFAULT_PATH
    if todo_path is None:
        todo_path = TODO_DEFAULT_PATH

    errors: list[str] = []

    # --- SPEC.md: open - [ ] items only ---
    if spec_path.exists():
        for lineno, line in enumerate(
            spec_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not re.match(r"^- \[ \]", line):
                continue
            task_text = _extract_task_text_spec(line)
            if _has_open_ended_word(task_text) and not _has_concrete_target(task_text):
                id_m = re.search(r"\b(\d+\.\d+[a-z]*)\b", line)
                item_ref = id_m.group(1) if id_m else f"line {lineno}"
                errors.append(
                    f"{spec_path}:{lineno}: item {item_ref!r} uses an open-ended "
                    f"marker without a concrete target (file path, backtick-quoted "
                    f"symbol, or phase ref)"
                )

    # --- TODO.md: bullets in the ## Next up section ---
    if todo_path.exists():
        in_next_up = False
        for lineno, line in enumerate(
            todo_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if _NEXT_UP_HEADER_RE.match(line):
                in_next_up = True
                continue
            if in_next_up and _ANY_SECTION_RE.match(line):
                in_next_up = False
                continue
            if not in_next_up or not _BULLET_START_RE.match(line):
                continue
            task_text = _extract_task_text_todo(line)
            if _has_open_ended_word(task_text) and not _has_concrete_target(task_text):
                errors.append(
                    f"{todo_path}:{lineno}: Next-up item uses an open-ended marker "
                    f"without a concrete target (file path, backtick-quoted symbol, "
                    f"or phase ref)"
                )

    return errors


def main() -> int:
    if not SCHEMA_PATH.exists():
        print(f"schema not found: {SCHEMA_PATH}", file=sys.stderr)
        return 1
    skill_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    chain_schema = (
        json.loads(CHAIN_SCHEMA_PATH.read_text(encoding="utf-8"))
        if CHAIN_SCHEMA_PATH.exists()
        else None
    )

    skill_targets: list[Path] = []
    chain_targets: list[Path] = []
    if len(sys.argv) > 1:
        for a in sys.argv[1:]:
            p = Path(a)
            if p.suffix == ".yaml":
                chain_targets.append(p)
            else:
                skill_targets.append(p)
    else:
        if SKILLS_DIR.is_dir():
            skill_targets = sorted(SKILLS_DIR.glob("**/SKILL.md"))
        if CHAINS_DIR.is_dir():
            chain_targets = sorted(CHAINS_DIR.glob("*.yaml"))

    if not skill_targets and not chain_targets:
        print("no SKILL.md or chain files to validate", file=sys.stderr)
        return 0

    total_errors = 0
    for path in skill_targets:
        for e in validate_one(path, skill_schema):
            print(e, file=sys.stderr)
            total_errors += 1
    if chain_schema is not None:
        for path in chain_targets:
            for e in validate_chain(path, chain_schema):
                print(e, file=sys.stderr)
                total_errors += 1

    for e in validate_spec_ids():
        print(e, file=sys.stderr)
        total_errors += 1

    human_md_path = REPO_ROOT / "docs" / "HUMAN.md"
    for e in validate_human_md(human_md_path):
        print(e, file=sys.stderr)
        total_errors += 1

    for e in validate_spec_item_quality():
        print(e, file=sys.stderr)
        total_errors += 1

    n_total = len(skill_targets) + len(chain_targets)
    if total_errors:
        print(f"\n{total_errors} validation error(s) across {n_total} file(s)", file=sys.stderr)
        return 2
    print(f"validated {len(skill_targets)} skill(s) + {len(chain_targets)} chain(s): all clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
