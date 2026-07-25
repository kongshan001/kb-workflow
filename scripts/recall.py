#!/usr/bin/env python3
"""
recall.py - retrieve relevant KB content for a query

Searches entries/ and external/ for content matching the query.
Returns ranked snippets the assistant can use to answer.

Modes:
  --mode text   (default) keyword/embedding similarity
  --mode embed  semantic via ollama

Output: JSON with hits [{file, name, type, snippet, score}]
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

KB_ROOT = Path(os.environ.get("KB_ROOT", Path.home() / ".claude" / "kb"))
ENTRIES_DIR = KB_ROOT / "entries"
EXTERNAL_DIR = KB_ROOT / "external"


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


def collect_files():
    files = []
    for d in (ENTRIES_DIR, EXTERNAL_DIR):
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            if f.name.startswith("_"):
                continue
            files.append(f)
    return files


def extract_snippet(body: str, query: str, max_len: int = 300) -> str:
    """Find best matching snippet in body."""
    q = query.lower()
    body_lower = body.lower()
    # try to find query terms in body
    terms = [t for t in re.split(r"\s+", q) if len(t) > 1]
    best_pos = -1
    for term in terms:
        pos = body_lower.find(term.lower())
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
    if best_pos == -1:
        # no match, return first paragraph
        for line in body.splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                return s[:max_len]
        return body[:max_len]
    start = max(0, best_pos - 50)
    end = min(len(body), best_pos + max_len)
    snippet = body[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(body):
        snippet = snippet + "..."
    return snippet


def score_text(content: str, query: str) -> float:
    """Naive keyword-based relevance score."""
    body_lower = content.lower()
    q_lower = query.lower()
    terms = [t for t in re.split(r"\s+", q_lower) if len(t) > 1]
    if not terms:
        return 0.0
    score = 0.0
    for term in terms:
        # exact substring match
        score += body_lower.count(term.lower()) * 2
        # word boundary match
        if re.search(rf"\b{re.escape(term.lower())}\b", body_lower):
            score += 1
    return score


def embed_ollama(text: str, model: str, host: str = "http://localhost:11434") -> list[float]:
    req = urllib.request.Request(
        f"{host}/api/embeddings",
        data=json.dumps({"model": model, "prompt": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["embedding"]


def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** 0.5
    nb = sum(x*x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("query", help="search query")
    p.add_argument("--mode", choices=["text", "embed"], default="text")
    p.add_argument("--model", default="nomic-embed-text")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--kb-root", type=Path, default=None)
    args = p.parse_args()

    global KB_ROOT, ENTRIES_DIR, EXTERNAL_DIR
    if args.kb_root:
        KB_ROOT = args.kb_root
        ENTRIES_DIR = KB_ROOT / "entries"
        EXTERNAL_DIR = KB_ROOT / "external"

    files = collect_files()
    if not files:
        print("  ℹ️  no KB files to search")
        return 0

    hits = []
    if args.mode == "embed":
        try:
            qvec = embed_ollama(args.query, args.model)
        except Exception as e:
            print(f"  ❌ ollama embed failed: {e}", file=sys.stderr)
            return 1
        for f in files:
            content = f.read_text(encoding="utf-8", errors="ignore")
            meta, body = parse_frontmatter(content)
            text = (meta.get("description", "") + " " + body)[:1000]
            try:
                fvec = embed_ollama(text, args.model)
            except Exception:
                continue
            score = cosine(qvec, fvec)
            hits.append({
                "file": str(f),
                "name": f.stem,
                "type": meta.get("type", "external_article"),
                "description": meta.get("description", ""),
                "snippet": extract_snippet(body, args.query),
                "score": score,
            })
    else:
        # text mode: keyword scoring
        for f in files:
            content = f.read_text(encoding="utf-8", errors="ignore")
            meta, body = parse_frontmatter(content)
            score = score_text(content, args.query)
            hits.append({
                "file": str(f),
                "name": f.stem,
                "type": meta.get("type", "external_article"),
                "description": meta.get("description", ""),
                "snippet": extract_snippet(body, args.query),
                "score": score,
            })

    hits.sort(key=lambda h: h["score"], reverse=True)
    hits = hits[:args.limit]

    if not hits or hits[0]["score"] == 0:
        print(f"  ℹ️  no matches for: {args.query}")
        return 0

    print(f"  🔍 {len(hits)} hit(s) for: {args.query}\n")
    for i, h in enumerate(hits, 1):
        print(f"─── {i}. [{h['type']}] {h['name']} (score {h['score']:.2f}) ───")
        print(f"  {h['description']}")
        print(f"  📁 {h['file']}")
        print(f"  💬 {h['snippet']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
