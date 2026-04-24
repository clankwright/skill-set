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

    n_total = len(skill_targets) + len(chain_targets)
    if total_errors:
        print(f"\n{total_errors} validation error(s) across {n_total} file(s)", file=sys.stderr)
        return 2
    print(f"validated {len(skill_targets)} skill(s) + {len(chain_targets)} chain(s): all clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
