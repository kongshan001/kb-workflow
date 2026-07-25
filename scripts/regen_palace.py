#!/usr/bin/env python3
"""
regen_palace.py - mirror external/ articles to MemPalace

In a Claude session, the assistant calls `mempalace_add_drawer` for each new
external article. This script:
  1. Walks external/*.md
  2. Parses frontmatter
  3. Outputs a plan that the assistant can execute
  4. OR: if mempalace CLI is available, calls it directly

Requirements:
  - KB_ROOT/external/ with article .md files
  - Optional: mempalace CLI in PATH (currently no such CLI — assistant does
    the actual mirror via MCP tools in-session)
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime, timezone

KB_ROOT = Path(os.environ.get("KB_ROOT", Path.home() / ".claude" / "kb"))
EXTERNAL_DIR = KB_ROOT / "external"


def parse_frontmatter(content: str):
    """
    Minimal YAML-ish frontmatter parser handling nested `metadata:` blocks.
    Returns (flat_meta_dict, body_str). Nested fields are flattened (e.g.
    `metadata.topic` becomes `meta['topic']`).
    """
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm_text, body = parts[1].strip(), parts[2].lstrip("\n")
    meta = {}
    current_parent = None      # current top-level key
    current_list_key = None    # current list being collected
    for line in fm_text.splitlines():
        if not line.strip():
            continue
        # nested list item
        m_list = re.match(r"^\s+-\s+(.*)$", line)
        if m_list and current_list_key is not None:
            meta[current_list_key].append(m_list.group(1).strip())
            continue
        # nested key: value (indented, under current_parent or current_list_key)
        m_nested = re.match(r"^\s+(\w+):\s*(.*)$", line)
        if m_nested and current_parent is not None:
            key, val = m_nested.group(1), m_nested.group(2)
            if val == "":
                # nested list start
                meta[key] = []
                current_list_key = key
                current_parent = None
            else:
                v = val.strip().strip('"').strip("'")
                meta[key] = v
                current_list_key = None
            continue
        # top-level key: value
        m_top = re.match(r"^(\w+):\s*(.*)$", line)
        if m_top:
            key, val = m_top.group(1), m_top.group(2)
            if val == "":
                # top-level nested block (e.g. `metadata:`)
                meta[key] = {}
                current_parent = key
                current_list_key = None
            else:
                v = val.strip().strip('"').strip("'")
                meta[key] = v
                current_parent = None
                current_list_key = None
    return meta, body


def first_paragraph(body: str) -> str:
    """Get first non-heading paragraph as summary."""
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("---"):
            continue
        return s[:200]
    return ""


def build_payload(meta: dict, body: str, file_path: Path) -> dict:
    topic = meta.get("topic", "uncategorized")
    if isinstance(topic, str) and "," in topic:
        topics = [t.strip() for t in topic.split(",")]
    else:
        topics = [topic]
    summary = first_paragraph(body)
    return {
        "wing": "kb_external",
        "rooms": [f"kb_external/{t}" for t in topics],
        "content": (
            f"摘要: {summary}\n"
            f"key_points: {meta.get('key_points', [])}\n"
            f"原文: {file_path}\n"
            f"ingested: {meta.get('ingested_at', 'unknown')}"
        ),
        "source_file": str(file_path),
    }


def has_mempalace_mcp() -> bool:
    """Probe whether mempalace MCP is registered."""
    claude_json = Path.home() / ".claude.json"
    if claude_json.exists() and "mempalace" in claude_json.read_text(errors="ignore"):
        return True
    return False


def main():
    if not EXTERNAL_DIR.exists():
        print(f"  ⚠️  {EXTERNAL_DIR} not found, nothing to do")
        return 0

    files = sorted(EXTERNAL_DIR.glob("*.md"))
    # skip index file
    files = [f for f in files if not f.name.startswith("_")]

    if not files:
        print("  ℹ️  no external articles to mirror")
        return 0

    if has_mempalace_mcp():
        print(f"  🔄 mempalace MCP detected — would mirror {len(files)} article(s):")
    else:
        print(f"  ⚠️  mempalace MCP not available — dry-run for {len(files)} article(s):")

    for f in files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        meta, body = parse_frontmatter(content)
        payload = build_payload(meta, body, f)
        print(f"     - {f.name}")
        print(f"        source_url: {meta.get('source_url', '?')}")
        for room in payload["rooms"]:
            print(f"        → room: {room}")
        print(f"        summary: {payload['content'].splitlines()[0]}")

    print()
    print("  In a Claude session, the assistant calls mempalace_add_drawer for each.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
