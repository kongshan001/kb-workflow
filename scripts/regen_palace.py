#!/usr/bin/env python3
"""
regen_palace.py - mirror external/ articles to MemPalace

Two modes:

1) --plan  (default, safe):
   Print the MemPalace operations that would be performed, as a
   shell-callable transcript the assistant can copy / execute.

2) --apply (real):
   Actually invoke the mempalace_add_drawer tool via a sidecar
   `mempalace` CLI if available, OR emit the exact tool-call payload
   the assistant should make.

The canonical path: this script is run by the assistant in a Claude
session, where `mempalace_add_drawer` is available as a real MCP tool.
In that context, the script outputs the JSON payloads and the
assistant invokes the tool for each.

Standalone use (no Claude session): the script falls back to a sidecar
`mempalace` CLI if installed; otherwise it just plans.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from frontmatter import parse_string as parse_frontmatter

KB_ROOT = Path(os.environ.get("KB_ROOT", Path.home() / ".claude" / "kb"))
EXTERNAL_DIR = KB_ROOT / "external"


def first_paragraph(body: str) -> str:
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
        topics = [topic] if isinstance(topic, str) else ["uncategorized"]
    summary = first_paragraph(body)
    return {
        "wing": "kb_external",
        "room": f"kb_external/{topics[0]}",  # primary room
        "content": (
            f"摘要: {summary}\n"
            f"key_points: {meta.get('key_points', [])}\n"
            f"原文: {file_path}\n"
            f"ingested: {meta.get('ingested_at', 'unknown')}"
        ),
        "source_file": str(file_path),
        "all_topics": topics,
    }


def cmd_plan(apply: bool):
    """Print the list of MemPalace operations."""
    if not EXTERNAL_DIR.exists():
        print(f"  ⚠️  {EXTERNAL_DIR} not found, nothing to do")
        return 0

    files = sorted([f for f in EXTERNAL_DIR.glob("*.md") if not f.name.startswith("_")])
    if not files:
        print("  ℹ️  no external articles to mirror")
        return 0

    mode = "APPLY" if apply else "PLAN"
    print(f"  [{mode}] {len(files)} article(s) → MemPalace\n")

    payloads = []
    for f in files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        meta, body = parse_frontmatter(content)
        payload = build_payload(meta, body, f)
        payloads.append(payload)

        print(f"── {f.name} ──")
        print(f"  source_url:  {meta.get('source_url', '?')}")
        print(f"  topic(s):    {payload['all_topics']}")
        print(f"  room:        {payload['room']}")
        print(f"  summary:     {payload['content'].splitlines()[0]}")
        print()

    if apply:
        # Emit JSON payloads the assistant / sidecar can act on
        out_path = KB_ROOT / ".palace-apply.json"
        out_path.write_text(json.dumps(payloads, ensure_ascii=False, indent=2))
        print(f"  💾 wrote apply manifest → {out_path}")
        print()
        print("  To complete mirroring, run in a Claude session:")
        print("    /kb-workflow palace-apply")
        print("  Or with sidecar (if installed):")
        print("    mempalace apply < .palace-apply.json")
    else:
        # Emit JSON payloads for the assistant to invoke tools from
        out_path = KB_ROOT / ".palace-plan.json"
        out_path.write_text(json.dumps(payloads, ensure_ascii=False, indent=2))
        print(f"  💾 wrote plan manifest → {out_path}")
        print()
        print("  To apply, run:")
        print("    regen_palace.py --apply")

    return 0


def main():
    p = argparse.ArgumentParser(description="Mirror external/ articles to MemPalace")
    p.add_argument("--apply", action="store_true",
                   help="Generate apply manifest (vs default plan manifest)")
    p.add_argument("--kb-root", type=Path, default=None,
                   help="Override KB_ROOT (default: $KB_ROOT or ~/.claude/kb)")
    args = p.parse_args()

    global KB_ROOT, EXTERNAL_DIR
    if args.kb_root:
        KB_ROOT = args.kb_root
        EXTERNAL_DIR = KB_ROOT / "external"

    return cmd_plan(apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
