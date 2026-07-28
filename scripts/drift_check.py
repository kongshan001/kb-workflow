#!/usr/bin/env python3
"""
drift_check.py - kb-workflow consistency drift detector (v0.3.1)

Used by /kb-evolve slash command (SKILL.md D11) to audit:
  - external/_index.md row count vs external/*.md file count
  - defaults.yaml entry_types vs schema/*.yaml field coverage
  - SKILL.md cross-references ("见 D5" etc.) resolve to real sections
  - CHANGELOG.md has [Unreleased] section

Outputs a gap report. Exit code:
  0 = all checks passed (no drift)
  1 = drift detected
  2 = script error (file missing, parse fail)

Usage:
  drift_check.py [--kb-root PATH] [--skill-root PATH] [--json]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_paths import ensure_utf8  # v0.4.4: UTF-8 stdout for Chinese-Windows

KB_ROOT = Path(os.environ.get("KB_ROOT", Path.home() / ".claude" / "kb"))
SKILL_ROOT = Path(os.environ.get(
    "KB_SKILL_ROOT",
    Path.home() / ".claude" / "skills" / "kb-workflow",
))


def check_index_drift(kb_root: Path) -> dict:
    """Check external/_index.md row count vs external/*.md file count."""
    external_dir = kb_root / "external"
    index_file = external_dir / "_index.md"
    result = {
        "name": "external/_index.md drift",
        "status": "ok",
        "files": 0,
        "rows": 0,
        "diff": [],
        "message": "",
    }
    if not external_dir.exists():
        result["status"] = "skip"
        result["message"] = "external/ dir does not exist"
        return result

    actual_files = sorted(
        f.name for f in external_dir.glob("*.md") if f.name != "_index.md"
    )
    result["files"] = len(actual_files)

    if not index_file.exists():
        result["status"] = "fail"
        result["message"] = "_index.md missing"
        result["diff"] = actual_files
        return result

    # Parse markdown table: count rows starting with `| <YYYY-MM-DD> |`
    rows = []
    for line in index_file.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", line)
        if m:
            rows.append((m.group(1), m.group(2).strip(), m.group(3).strip()))
    result["rows"] = len(rows)
    indexed_slugs = {r[2] for r in rows}

    # Diff: files not indexed, indexed entries without file
    file_slugs = set()
    for fname in actual_files:
        # strip YYYY-MM-DD[-_]<topic>[-_]<slug>.md prefix
        # v0.3.1: accept both `_` and `-` as separator (existing KB uses both)
        # v0.4.4: topic may contain '-' (e.g. llm-memory). Greedy first group
        # lands the LAST [-_] as the topic/slug split, so slug = group(2).
        # (was [^_-]+ which truncated llm-memory→llm and mis-parsed the slug,
        #  falsely reporting drift on every llm-* entry.)
        m = re.match(r"^\d{4}-\d{2}-\d{2}[-_](.+)[-_](.+)\.md$", fname)
        slug = m.group(2) if m else fname.replace(".md", "")
        file_slugs.add(slug)

    result["diff"] = sorted(file_slugs ^ indexed_slugs)
    if result["diff"]:
        result["status"] = "fail"
        result["message"] = (
            f"drift: {len(file_slugs - indexed_slugs)} files not in index, "
            f"{len(indexed_slugs - file_slugs)} index rows without file"
        )
    return result


def check_schema_coverage(skill_root: Path) -> dict:
    """Check defaults.yaml entry_types matches schema/*.yaml field lists."""
    result = {
        "name": "schema field coverage",
        "status": "ok",
        "covered": [],
        "missing": [],
    }
    defaults = skill_root / "config" / "defaults.yaml"
    schema_dir = skill_root / "config" / "schema"
    if not defaults.exists() or not schema_dir.exists():
        result["status"] = "skip"
        return result

    # Light parse: extract entry_types.<type>.fields lists
    txt = defaults.read_text(encoding="utf-8")
    entry_types_block = re.search(
        r"entry_types:\s*\n((?:\s{4}\w+:\s*\n(?:\s{6}\w+:.*\n)*)+)",
        txt,
    )
    if not entry_types_block:
        return result

    type_to_fields = {}
    current_type = None
    for line in entry_types_block.group(1).splitlines():
        m_type = re.match(r"^\s{4}(\w+):\s*$", line)
        m_field = re.match(r"^\s{6}-?\s*(\w+)\s*$", line)
        if m_type:
            current_type = m_type.group(1)
            type_to_fields[current_type] = []
        elif m_field and current_type:
            type_to_fields[current_type].append(m_field.group(1))

    # Check each schema file
    for schema_file in schema_dir.glob("*.yaml"):
        schema_txt = schema_file.read_text(encoding="utf-8")
        # Find `metadata:` block fields
        meta_block = re.search(
            r"metadata:\s*\n((?:\s{2}\w+:.*\n)+)",
            schema_txt,
        )
        if not meta_block:
            continue
        schema_fields = set()
        for line in meta_block.group(1).splitlines():
            m = re.match(r"^\s{2}(\w+):", line)
            if m:
                schema_fields.add(m.group(1))

        # Cross-ref with entry_types that share name prefix (e.g., fact <-> fact.yaml)
        type_name = schema_file.stem  # e.g., "fact", "external_article"
        if type_name in type_to_fields:
            declared = set(type_to_fields[type_name])
            schema_only = schema_fields - declared
            declared_only = declared - schema_fields
            if schema_only or declared_only:
                result["status"] = "warn"
                result.setdefault("mismatches", []).append({
                    "type": type_name,
                    "schema_only": sorted(schema_only),
                    "defaults_only": sorted(declared_only),
                })
            result["covered"].append(type_name)

    return result


def check_section_refs(skill_root: Path) -> dict:
    """Check SKILL.md '见 D#' references resolve to real ## D# sections."""
    result = {
        "name": "SKILL.md section refs",
        "status": "ok",
        "referenced": [],
        "missing_sections": [],
    }
    skill_md = skill_root / "SKILL.md"
    if not skill_md.exists():
        result["status"] = "skip"
        return result
    txt = skill_md.read_text(encoding="utf-8")

    # Find all "D#" references like  "见 D5"  "D9"  "(D11)"  "D10"
    refs = set(re.findall(r"\bD(\d{1,2})\b", txt))
    actual_sections = set(re.findall(r"^##\s+D(\d{1,2})\s", txt, re.MULTILINE))

    result["referenced"] = sorted(refs)
    missing = refs - actual_sections
    if missing:
        result["status"] = "fail"
        result["missing_sections"] = sorted(missing)
    return result


def check_changelog(skill_root: Path) -> dict:
    """Check CHANGELOG.md has [Unreleased] section with at least one entry."""
    result = {
        "name": "CHANGELOG.md [Unreleased]",
        "status": "ok",
        "has_unreleased": False,
        "added": 0,
        "fixed": 0,
        "tested": 0,
    }
    cl = skill_root / "CHANGELOG.md"
    if not cl.exists():
        result["status"] = "skip"
        return result
    txt = cl.read_text(encoding="utf-8")

    if "## [Unreleased]" not in txt:
        result["status"] = "warn"
        result["message"] = "no [Unreleased] section"
        return result

    result["has_unreleased"] = True
    # Count entries per category inside [Unreleased]
    unreleased = txt.split("## [Unreleased]", 1)[1]
    next_section = re.search(r"^##\s+\[", unreleased, re.MULTILINE)
    if next_section:
        unreleased = unreleased[:next_section.start()]

    result["added"] = len(re.findall(r"^### Added\b", unreleased, re.MULTILINE))
    result["fixed"] = len(re.findall(r"^### Fixed\b", unreleased, re.MULTILINE))
    result["tested"] = len(re.findall(r"^### Tested\b", unreleased, re.MULTILINE))

    if result["added"] + result["fixed"] == 0:
        result["status"] = "warn"
        result["message"] = "[Unreleased] has no Added/Fixed entries"
    return result


def main():
    ensure_utf8()
    parser = argparse.ArgumentParser(description="kb-workflow consistency drift detector")
    parser.add_argument("--kb-root", default=KB_ROOT, help="KB root directory")
    parser.add_argument("--skill-root", default=SKILL_ROOT, help="skill install root")
    parser.add_argument("--json", action="store_true", help="output JSON instead of text report")
    args = parser.parse_args()

    kb_root = Path(args.kb_root)
    skill_root = Path(args.skill_root)

    checks = [
        check_index_drift(kb_root),
        check_schema_coverage(skill_root),
        check_section_refs(skill_root),
        check_changelog(skill_root),
    ]

    overall_fail = any(c.get("status") in ("fail", "warn") for c in checks)

    if args.json:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    else:
        print("=== /kb-evolve drift_check report ===")
        for c in checks:
            status_icon = {
                "ok": "✅", "warn": "🟡", "fail": "❌", "skip": "⚪",
            }.get(c["status"], "?")
            print(f"\n[{c['status'].upper():4}] {c['name']}  {status_icon}")
            for k, v in c.items():
                if k in ("name", "status"):
                    continue
                if isinstance(v, list) and not v:
                    continue
                print(f"    {k}: {v}")

        print("\n" + ("=" * 40))
        if overall_fail:
            print("RESULT: drift detected — see [FAIL]/[WARN] above")
        else:
            print("RESULT: all checks passed")

    sys.exit(1 if overall_fail else 0)


if __name__ == "__main__":
    main()