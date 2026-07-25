#!/usr/bin/env python3
"""
dedup.py - semantic deduplication using local embeddings

Uses ollama (nomic-embed-text by default) to embed all entry contents,
computes pairwise cosine similarity, and reports pairs above the
similarity threshold.

Usage:
  dedup.py [--threshold 0.9] [--model nomic-embed-text]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

KB_ROOT = Path(os.environ.get("KB_ROOT", Path.home() / ".claude" / "kb"))
ENTRIES_DIR = KB_ROOT / "entries"


def parse_frontmatter(content: str):
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm_text, body = parts[1].strip(), parts[2].lstrip("\n")
    meta = {}
    current_parent = None
    current_list_key = None
    for line in fm_text.splitlines():
        if not line.strip():
            continue
        m_list = re.match(r"^\s+-\s+(.*)$", line)
        if m_list and current_list_key is not None:
            meta[current_list_key].append(m_list.group(1).strip())
            continue
        m_nested = re.match(r"^\s+(\w+):\s*(.*)$", line)
        if m_nested and current_parent is not None:
            key, val = m_nested.group(1), m_nested.group(2)
            if val == "":
                meta[key] = []
                current_list_key = key
                current_parent = None
            else:
                meta[key] = val.strip().strip('"').strip("'")
                current_list_key = None
            continue
        m_top = re.match(r"^(\w+):\s*(.*)$", line)
        if m_top:
            key, val = m_top.group(1), m_top.group(2)
            if val == "":
                meta[key] = {}
                current_parent = key
                current_list_key = None
            else:
                meta[key] = val.strip().strip('"').strip("'")
                current_parent = None
                current_list_key = None
    return meta, body


def load_entries():
    if not ENTRIES_DIR.exists():
        return []
    out = []
    for f in sorted(ENTRIES_DIR.glob("*.md")):
        content = f.read_text(encoding="utf-8", errors="ignore")
        meta, body = parse_frontmatter(content)
        # use first non-empty non-heading line as embed text
        embed_text = ""
        for line in body.splitlines():
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("**"):
                continue
            embed_text = s[:500]
            break
        if not embed_text:
            embed_text = meta.get("description", f.stem)
        out.append({
            "file": f,
            "name": f.stem,
            "type": meta.get("type", "?"),
            "description": meta.get("description", ""),
            "embed_text": embed_text,
        })
    return out


def embed_ollama(text: str, model: str, host: str = "http://localhost:11434") -> list[float]:
    """Call ollama embeddings via HTTP API (works on all ollama versions)."""
    import urllib.request
    import urllib.error
    req = urllib.request.Request(
        f"{host}/api/embeddings",
        data=json.dumps({"model": model, "prompt": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise RuntimeError(f"ollama HTTP API unreachable at {host}: {e}")
    if "embedding" not in data:
        raise RuntimeError(f"ollama response missing 'embedding': {data}")
    return data["embedding"]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** 0.5
    nb = sum(x*x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=float, default=0.9,
                   help="Cosine similarity above which to flag as duplicate")
    p.add_argument("--model", default="nomic-embed-text",
                   help="ollama embedding model")
    p.add_argument("--dry-run", action="store_true",
                   help="Compute embeddings but don't flag")
    args = p.parse_args()

    entries = load_entries()
    if not entries:
        print("  ℹ️  no entries to dedup")
        return 0

    print(f"  📐 Embedding {len(entries)} entries via ollama:{args.model} ...")
    for e in entries:
        try:
            e["embedding"] = embed_ollama(e["embed_text"], args.model)
        except Exception as ex:
            print(f"  ❌ failed to embed {e['name']}: {ex}")
            return 1
    print(f"  ✅ embeddings ready\n")

    # pairwise
    pairs = []
    for i in range(len(entries)):
        for j in range(i+1, len(entries)):
            sim = cosine(entries[i]["embedding"], entries[j]["embedding"])
            if sim >= args.threshold:
                pairs.append((sim, entries[i], entries[j]))

    if not pairs:
        print(f"  ✅ no duplicates found (threshold={args.threshold})")
        return 0

    pairs.sort(reverse=True)
    print(f"  ⚠️  found {len(pairs)} duplicate pair(s) (≥{args.threshold})\n")
    for sim, a, b in pairs:
        print(f"─── similarity {sim:.3f} ───")
        print(f"  A: {a['name']}  [{a['type']}]")
        print(f"     {a['description']}")
        print(f"  B: {b['name']}  [{b['type']}]")
        print(f"     {b['description']}")
        print()
        print(f"  建议:")
        print(f"    A) 删 A（更新 B 的 content）")
        print(f"    B) 删 B（更新 A 的 content）")
        print(f"    C) 都保留（如果是不同场景）")
        print(f"    D) 把 A 转成 B 的细化（refines 链）")
        print()

    if not args.dry_run:
        out_path = KB_ROOT / ".dedup-report.json"
        out_path.write_text(json.dumps([
            {
                "similarity": sim,
                "a": a["name"],
                "b": b["name"],
                "a_type": a["type"],
                "b_type": b["type"],
                "a_desc": a["description"],
                "b_desc": b["description"],
            }
            for sim, a, b in pairs
        ], ensure_ascii=False, indent=2))
        print(f"  💾 report → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
