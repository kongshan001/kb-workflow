#!/usr/bin/env python3
"""
regen_palace.py - rebuild MemPalace index from external/*.md

Walks KB_ROOT/external/ and creates/updates MemPalace drawers for each article.
This is a fallback/index-regeneration script; the canonical source is the file.

Requires: mempalace MCP available (graceful skip otherwise)
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

KB_ROOT = Path(os.environ.get("KB_ROOT", Path.home() / ".claude" / "kb"))
EXTERNAL_DIR = KB_ROOT / "external"


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML-ish frontmatter, return (meta, body)."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm_text, body = parts[1], parts[2].lstrip("\n")
    meta = {}
    current_key = None
    current_list = None
    for line in fm_text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip())
            continue
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2)
            current_key = key
            if val == "":
                # could be list
                current_list = []
                meta[key] = current_list
            else:
                current_list = None
                meta[key] = val.strip().strip('"').strip("'")
    return meta, body


def has_mempalace() -> bool:
    """Probe whether mempalace MCP is reachable."""
    # In Claude Code session the assistant can call mempalace tools directly.
    # Here we just check if the config file references it.
    claude_json = Path.home() / ".claude.json"
    if claude_json.exists() and "mempalace" in claude_json.read_text(errors="ignore"):
        return True
    return False


def build_palace_payload(meta: dict, body: str, file_path: Path) -> dict:
    """Construct the MemPalace drawer payload from a parsed article."""
    topic = meta.get("topic", "uncategorized")
    # support multi-topic via comma
    if isinstance(topic, str) and "," in topic:
        topics = [t.strip() for t in topic.split(",")]
    else:
        topics = [topic] if isinstance(topic, str) else ["uncategorized"]

    # first paragraph = summary heuristic
    body_lines = [l for l in body.splitlines() if l.strip()]
    summary = ""
    for line in body_lines:
        if line.startswith("#"):
            continue
        summary = line[:200]
        break

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


def main():
    if not EXTERNAL_DIR.exists():
        print(f"  ⚠️  {EXTERNAL_DIR} not found, nothing to do")
        return 0

    if not has_mempalace():
        print("  ⚠️  mempalace MCP not available — skipping (regen when reachable)")
        # still list what would be mirrored
        files = sorted(EXTERNAL_DIR.glob("*.md"))
        if files:
            print(f"  ℹ️  Would mirror {len(files)} article(s):")
            for f in files:
                print(f"     - {f.name}")
        return 0

    # In a real session, assistant would call mempalace_add_drawer for each
    # Here we just print the planned operations
    files = sorted(EXTERNAL_DIR.glob("*.md"))
    print(f"  🔄 Would mirror {len(files)} article(s) to MemPalace:")
    for f in files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        meta, body = parse_frontmatter(content)
        payload = build_palace_payload(meta, body, f)
        print(f"     - {f.name}")
        for room in payload["rooms"]:
            print(f"        → {room}")
    print("  ℹ️  In a Claude session, the assistant will call mempalace_add_drawer for each.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
