#!/usr/bin/env python3
"""
forget.py - soft-delete / hard-delete / restore KB entries (v0.3.3)

Implements SKILL.md D12 /kb-forget slash command:
  - default: soft delete (rename to <slug>.deleted.<timestamp> + status: forgotten
    + forgotten_at: YYYY-MM-DD)
  - --hard: physical removal (rm)
  - --restore: undo a soft delete (rename back + strip status fields)
  - _index.md row sync (remove on delete / re-add on restore)
  - _state.md marker via recording the operation

Usage:
  forget.py <slug>                  # soft delete (default)
  forget.py --hard <slug>           # hard delete (irreversible)
  forget.py --restore <slug>        # restore a soft-deleted entry
  forget.py --list-deleted          # list currently soft-deleted entries
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_paths import resolve_paths, ensure_utf8  # SSOT for KB path resolution (v0.4.0)

_PATHS = resolve_paths()
KB_ROOT = _PATHS["KB_ROOT"]
ENTRIES_DIR = KB_ROOT / "entries"
EXTERNAL_DIR = KB_ROOT / "external"
INDEX_FILE = _PATHS["KB_INDEX_FILE"]


def parse_index_row(line: str):
    """Parse _index.md table row. Returns (ingested, topic, slug, source_url) or None."""
    m = re.match(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), m.group(4).strip()
    return None


def find_entry(slug: str):
    """Find an entry by slug across entries/ and external/. Returns (path, source) or None."""
    # entries/ uses flat slug (no date prefix): fact-xxx, decision-xxx, etc.
    for f in ENTRIES_DIR.glob(f"*{slug}*"):
        if f.stem == slug or slug in f.stem:
            return f, "entries"

    # external/ uses YYYY-MM-DD_<topic>_<slug>.md or with `-` separator
    for f in EXTERNAL_DIR.glob("*.md"):
        if f.name == "_index.md":
            continue
        # extract slug from filename (handle both `-` and `_` separators)
        # v0.4.4: topic may contain '-' (e.g. llm-memory) — greedy first group,
        # slug is group(2) after the LAST separator.
        m = re.match(r"^\d{4}-\d{2}-\d{2}[-_](.+)[-_](.+)\.md$", f.name)
        if m and m.group(2) == slug:
            return f, "external"
        if f.stem == slug:
            return f, "external"
    return None


def find_deleted(slug: str):
    """Find a soft-deleted entry by slug. Returns (path, original_name) or None."""
    for f in ENTRIES_DIR.glob(f"*{slug}*.deleted.*"):
        return f, f.name.replace(".deleted.", " ").split(" ")[0]
    for f in EXTERNAL_DIR.glob(f"*{slug}*.deleted.*"):
        m = re.match(r"^(.+)\.deleted\.\d{8}$", f.name)
        if m:
            return f, m.group(1)
    return None


def soft_delete(path: Path) -> Path:
    """Rename to <name>.deleted.<YYYYMMDD> + add frontmatter status."""
    timestamp = date.today().strftime("%Y%m%d")
    new_name = f"{path.name}.deleted.{timestamp}"
    new_path = path.parent / new_name

    if new_path.exists():
        # collision: append counter
        i = 1
        while True:
            new_path = path.parent / f"{path.name}.deleted.{timestamp}.{i}"
            if not new_path.exists():
                break
            i += 1

    # Read + add status field, then write to new path
    content = path.read_text(encoding="utf-8")
    new_content = add_forgotten_status(content)
    new_path.write_text(new_content, encoding="utf-8")
    path.unlink()
    return new_path


def add_forgotten_status(content: str) -> str:
    """Add status: forgotten and forgotten_at: YYYY-MM-DD to frontmatter."""
    today = date.today().isoformat()
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    fm_text = parts[1]
    body = parts[2]

    # Check if status already set
    if re.search(r"^\s*status:\s*forgotten", fm_text, re.MULTILINE):
        return content  # already soft-deleted

    # Inject status + forgotten_at into metadata or top-level
    if re.search(r"^\s*metadata:\s*$", fm_text, re.MULTILINE):
        # external_article style: has metadata block
        new_fm = re.sub(
            r"(metadata:\s*\n)",
            rf"\1  status: forgotten\n  forgotten_at: {today}\n",
            fm_text,
            count=1,
        )
    else:
        # top-level style
        new_fm = fm_text + f"\nstatus: forgotten\nforgotten_at: {today}\n"

    return f"---{new_fm}---{body}"


def remove_forgotten_status(content: str) -> str:
    """Strip status: forgotten and forgotten_at fields (for --restore)."""
    content = re.sub(r"^\s*status:\s*forgotten\s*\n", "", content, flags=re.MULTILINE)
    content = re.sub(r"^\s*forgotten_at:\s*\d{4}-\d{2}-\d{2}\s*\n", "", content, flags=re.MULTILINE)
    return content


def sync_index_remove(slug: str):
    """Remove row from _index.md if present."""
    if not INDEX_FILE.exists():
        return
    lines = INDEX_FILE.read_text(encoding="utf-8").splitlines()
    new_lines = [l for l in lines if not (parse_index_row(l) and parse_index_row(l)[2] == slug)]
    INDEX_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def sync_index_restore(ingested: str, topic: str, slug: str, source_url: str):
    """Re-add row to _index.md after restore."""
    if not INDEX_FILE.exists():
        INDEX_FILE.write_text(
            "# External Articles Index\n\n"
            "> 自动维护。每次 `/kb-save-article` 后由 assistant 追加一行。\n\n"
            "| ingested | topic | slug | source_url |\n|---|---|---|---|\n",
            encoding="utf-8",
        )
    lines = INDEX_FILE.read_text(encoding="utf-8").splitlines()
    new_row = f"| {ingested} | {topic} | {slug} | {source_url} |"
    # Append before any existing trailing blank lines
    while lines and not lines[-1].strip():
        lines.pop()
    lines.append("")
    lines.append(new_row)
    INDEX_FILE.write_text("\n".join(lines), encoding="utf-8")


def main():
    ensure_utf8()
    p = argparse.ArgumentParser(description="kb-workflow /kb-forget: soft/hard delete + restore")
    p.add_argument("slug", nargs="?", help="entry slug to forget/restore")
    p.add_argument("--hard", action="store_true", help="irreversible physical rm")
    p.add_argument("--restore", action="store_true", help="restore a soft-deleted entry")
    p.add_argument("--list-deleted", action="store_true", help="list currently soft-deleted entries")
    p.add_argument("--kb-root", type=Path, default=None)
    args = p.parse_args()

    global KB_ROOT, ENTRIES_DIR, EXTERNAL_DIR, INDEX_FILE
    if args.kb_root:
        KB_ROOT = args.kb_root
        ENTRIES_DIR = KB_ROOT / "entries"
        EXTERNAL_DIR = KB_ROOT / "external"
        INDEX_FILE = EXTERNAL_DIR / "_index.md"

    if args.list_deleted:
        deleted = list(ENTRIES_DIR.glob("*.deleted.*")) + list(EXTERNAL_DIR.glob("*.deleted.*"))
        if not deleted:
            print("  ℹ️  no soft-deleted entries")
            return 0
        print(f"  🗑️  {len(deleted)} soft-deleted entries:")
        for f in sorted(deleted):
            print(f"    {f.relative_to(KB_ROOT)}")
        return 0

    if not args.slug:
        print("  ❌ slug required (or use --list-deleted)", file=sys.stderr)
        return 2

    # Restore path
    if args.restore:
        deleted = find_deleted(args.slug)
        if not deleted:
            print(f"  ❌ no soft-deleted entry found for slug={args.slug!r}")
            return 1
        path, original_name = deleted
        original_path = path.parent / original_name

        content = path.read_text(encoding="utf-8")
        restored = remove_forgotten_status(content)
        original_path.write_text(restored, encoding="utf-8")
        path.unlink()

        # Re-add to index if was external
        if path.parent == EXTERNAL_DIR:
            # Try to extract metadata for re-add
            m = re.search(r"ingested_at:\s*(\d{4}-\d{2}-\d{2})", restored)
            ingested = m.group(1) if m else date.today().isoformat()
            m = re.search(r"topic:\s*(\S+)", restored)
            topic = m.group(1) if m else "?"
            m = re.search(r"source_url:\s*(\S+)", restored)
            source_url = m.group(1) if m else "?"
            sync_index_restore(ingested, topic, args.slug, source_url)

        print(f"  ↻  restored: {original_path.relative_to(KB_ROOT)}")
        return 0

    # Forget path (default or --hard)
    found = find_entry(args.slug)
    if not found:
        print(f"  ❌ no entry found for slug={args.slug!r}")
        return 1

    path, source = found

    if args.hard:
        path.unlink()
        if source == "external":
            sync_index_remove(args.slug)
        print(f"  ✗  hard-deleted: {path.name}")
        return 0

    # Soft delete
    new_path = soft_delete(path)
    if source == "external":
        sync_index_remove(args.slug)
    print(f"  ✗  soft-deleted: {new_path.name}")
    print(f"     (rename + status: forgotten + forgotten_at; --restore to undo)")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)