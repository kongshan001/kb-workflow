#!/usr/bin/env python3
"""
recall.py - retrieve relevant KB content for a query

Searches entries/ and external/ for content matching the query.
Returns ranked snippets the assistant can use to answer.

Modes:
  --mode text   (default) keyword/embedding similarity
  --mode embed  semantic via ollama

Output: JSON with hits [{file, name, type, snippet, score}]

v0.3.3: uses shared frontmatter.py (yaml.safe_load if available, else
handrolled fallback). Replaces inline parse_frontmatter.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from frontmatter import parse_string as parse_frontmatter, backend as fm_backend
from kb_paths import resolve_paths  # SSOT for KB path resolution (v0.4.0)

_PATHS = resolve_paths()
KB_ROOT = _PATHS["KB_ROOT"]
ENTRIES_DIR = KB_ROOT / "entries"
EXTERNAL_DIR = KB_ROOT / "external"


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


def find_section_heading(body: str, pos: int) -> str:
    """Find the nearest preceding ## heading above position `pos`.

    Used as a citation anchor — tells the assistant "this match is in section X".
    """
    if pos < 0:
        return ""
    # scan backwards from pos to find last ## heading
    head = body[:pos]
    headings = re.findall(r"^(#{1,3})\s+(.+)$", head, re.MULTILINE)
    if not headings:
        return ""
    # last heading wins
    _, title = headings[-1]
    return title.strip()


def extract_snippet(body: str, query: str, max_len: int = 400) -> str:
    """Find best matching snippet in body, anchored to query term occurrence.

    v0.3.4 upgrade:
    - anchors to first query term match (was: first paragraph if no match)
    - preserves nearest preceding ## heading as citation context
    - returns ~max_len chars centered on match (was: max_len from start)
    - returns (snippet, anchor) — caller can combine as needed
    """
    q = query.lower()
    body_lower = body.lower()
    terms = [t for t in re.split(r"\s+", q) if len(t) > 1]

    # find best matching position (earliest query term occurrence)
    best_pos = -1
    best_term = ""
    for term in terms:
        pos = body_lower.find(term.lower())
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
            best_term = term

    if best_pos == -1:
        # no match — return first non-heading paragraph
        for line in body.splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                return "", s[:max_len]
        return "", body[:max_len]

    # context window centered on match
    start = max(0, best_pos - 80)
    end = min(len(body), best_pos + max_len)
    snippet = body[start:end].strip()
    if start > 0:
        # find a good cut point (newline)
        cut = snippet.find("\n\n")
        if cut > 0 and cut < 80:
            snippet = snippet[cut + 2:].lstrip()
        snippet = "..." + snippet
    if end < len(body):
        snippet = snippet.rstrip() + "..."

    anchor = find_section_heading(body, best_pos)
    return anchor, snippet


def score_text(content: str, query: str) -> float:
    """Naive keyword-based relevance score."""


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


def get_topic(meta: dict) -> str:
    """Extract topic from frontmatter. Handles nested metadata.topic (external_article)."""
    if "topic" in meta:
        return meta["topic"]
    if "metadata" in meta and isinstance(meta["metadata"], dict):
        return meta["metadata"].get("topic", "")
    return ""


def _build_hit(file_path, meta, body, score, anchor, snippet, query):
    """Build a single hit dict with full citation metadata (v0.3.4)."""
    metadata = meta.get("metadata", {}) if isinstance(meta.get("metadata"), dict) else {}
    last_seen = metadata.get("last_seen") or meta.get("last_seen") or ""
    # coerce date to ISO string (last_seen can be date object via PyYAML)
    if hasattr(last_seen, "isoformat"):
        last_seen = last_seen.isoformat()
    return {
        "file": str(file_path),
        "name": file_path.stem,
        "type": meta.get("type", "external_article"),
        "description": meta.get("description", ""),
        "topic": get_topic(meta) or "",
        "source_url": metadata.get("source_url", "") or meta.get("source_url", ""),
        "last_seen": last_seen,
        "section_anchor": anchor or "",
        "snippet": snippet,
        "score": score,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("query", help="search query")
    p.add_argument("--mode", choices=["text", "embed"], default="text")
    p.add_argument("--model", default="nomic-embed-text")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--kb-root", type=Path, default=None)
    p.add_argument("--topic", default=None, help="v0.3.3: filter by topic (e.g. llm-memory, rag, ml)")
    p.add_argument("--format", choices=["text", "json"], default="text",
                   help="v0.3.4: text (human) or json (machine — for assistant synthesis)")
    args = p.parse_args()

    global KB_ROOT, ENTRIES_DIR, EXTERNAL_DIR
    if args.kb_root:
        KB_ROOT = args.kb_root
        ENTRIES_DIR = KB_ROOT / "entries"
        EXTERNAL_DIR = KB_ROOT / "external"

    files = collect_files()
    if not files:
        if args.format == "json":
            print(json.dumps({"query": args.query, "hits": []}, ensure_ascii=False, indent=2))
        else:
            print("  ℹ️  no KB files to search")
        return 0

    # v0.3.3: topic filter — preload frontmatter for all files
    topic_filtered = False
    if args.topic:
        topic_filtered = True
        filtered = []
        for f in files:
            content = f.read_text(encoding="utf-8", errors="ignore")
            meta, _ = parse_frontmatter(content)
            t = get_topic(meta)
            if t == args.topic:
                filtered.append(f)
            elif t == "" and f.parent.name == "entries":
                # entries/ items have no topic field — exclude when --topic is set
                pass
            # else: skip (topic mismatch)
        files = filtered
        if not files:
            if args.format == "json":
                print(json.dumps({"query": args.query, "topic": args.topic, "hits": []},
                                 ensure_ascii=False, indent=2))
            else:
                print(f"  ℹ️  no files match topic={args.topic!r}")
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
            anchor, snippet = extract_snippet(body, args.query)
            hits.append(_build_hit(f, meta, body, score, anchor, snippet, args.query))
    else:
        # text mode: keyword scoring
        for f in files:
            content = f.read_text(encoding="utf-8", errors="ignore")
            meta, body = parse_frontmatter(content)
            score = score_text(content, args.query)
            anchor, snippet = extract_snippet(body, args.query)
            hits.append(_build_hit(f, meta, body, score, anchor, snippet, args.query))

    hits.sort(key=lambda h: h["score"], reverse=True)
    hits = hits[:args.limit]

    if not hits or hits[0]["score"] == 0:
        if args.format == "json":
            print(json.dumps({"query": args.query, "hits": []}, ensure_ascii=False, indent=2))
        else:
            print(f"  ℹ️  no matches for: {args.query}")
        return 0

    if args.format == "json":
        # machine-readable: query + per-hit citation metadata + snippet
        out = {
            "query": args.query,
            "topic": args.topic if topic_filtered else None,
            "mode": args.mode,
            "total_hits": len(hits),
            "hits": [
                {
                    "rank": i + 1,
                    "name": h["name"],
                    "type": h["type"],
                    "score": round(h["score"], 2),
                    "topic": h["topic"],
                    "source_url": h["source_url"],
                    "file": h["file"],
                    "last_seen": h["last_seen"],
                    "section_anchor": h["section_anchor"],
                    "snippet": h["snippet"],
                }
                for i, h in enumerate(hits)
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    filter_label = f" [topic={args.topic}]" if topic_filtered else ""
    print(f"  🔍 {len(hits)} hit(s) for: {args.query}{filter_label}\n")
    for i, h in enumerate(hits, 1):
        meta_line = f"  topic: {h['topic'] or '?'}"
        if h["source_url"]:
            meta_line += f"  src: {h['source_url']}"
        print(f"─── {i}. [{h['type']}] {h['name']} (score {h['score']:.2f}) ───")
        print(f"  {h['description']}")
        if h["section_anchor"]:
            print(f"  § section: {h['section_anchor']}")
        print(meta_line)
        print(f"  📁 {h['file']}")
        print(f"  💬 {h['snippet']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
