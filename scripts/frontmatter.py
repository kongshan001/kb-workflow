#!/usr/bin/env python3
"""
frontmatter.py - shared frontmatter parser (v0.3.3)

Single source of truth for parsing YAML frontmatter in KB entries.
Replaces hand-rolled parsers in recall.py / dedup.py / regen_palace.py / drift_check.py.

Strategy:
  1. Try yaml.safe_load (PyYAML) if available — proper YAML spec compliance
  2. Fall back to consolidated hand-rolled parser — handles the 90% case
     (top-level keys + nested `metadata:` block + simple lists)

Usage:
  from frontmatter import parse_file, parse_string

  meta, body = parse_file(Path("entries/fact-foo.md"))
  meta, body = parse_string(content)
"""

from pathlib import Path
from typing import Tuple, Dict, Any

try:
    import yaml  # PyYAML — proper YAML parsing
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def _parse_handrolled(content: str) -> Tuple[Dict[str, Any], str]:
    """Consolidated hand-rolled frontmatter parser.

    Handles:
      - top-level keys (name: foo / confidence: low)
      - nested `metadata:` block (indented 2 spaces)
      - list items under any key (`  - item`)
      - quoted strings ('...' or "...")
      - null values
    Returns: (meta_dict, body_str)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm_text = parts[1]
    body = parts[2].lstrip("\n")

    meta: Dict[str, Any] = {}
    current_parent = None
    current_list_key = None

    for line in fm_text.splitlines():
        if not line.strip():
            continue

        # List item: "  - value" (under current_list_key)
        m_list = re.match(r"^\s{2,}-\s+(.*)$", line)
        if m_list and current_list_key is not None:
            val = m_list.group(1).strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            meta[current_list_key].append(val)
            continue

        # Nested key under metadata: "  key: value"
        m_nested = re.match(r"^\s{2}(\w[\w-]*):\s*(.*)$", line)
        if m_nested and current_parent is not None:
            key, val = m_nested.group(1), m_nested.group(2)
            if val == "":
                # nested dict marker (rare)
                if isinstance(meta.get(current_parent), dict):
                    meta[current_parent][key] = {}
                current_list_key = None
            else:
                val = val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                elif val.lower() in ("null", "~", ""):
                    val = None
                elif val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                if isinstance(meta.get(current_parent), dict):
                    meta[current_parent][key] = val
                else:
                    meta[key] = val
            continue

        # Top-level key: "key: value" or "key:" (dict marker)
        m_top = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if m_top:
            key, val = m_top.group(1), m_top.group(2)
            if val == "":
                meta[key] = {}
                current_parent = key
                current_list_key = None
            else:
                val = val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                elif val.lower() in ("null", "~", ""):
                    val = None
                elif val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                meta[key] = val
                current_parent = None
                current_list_key = key
                # Detect list-marker: only if this top-level key's value is a list,
                # handled by next iteration's m_list match
            continue

    return meta, body


def _parse_yaml(content: str) -> Tuple[Dict[str, Any], str]:
    """PyYAML-based parser. Handles full YAML spec.

    On YAML error (e.g., unquoted CJK + ':' in description), falls back to
    handrolled parser and emits a stderr warning. This avoids silent data loss
    when the handrolled parser was the only one that could read the file.
    """
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm_text = parts[1]
    body = parts[2].lstrip("\n")
    try:
        meta = yaml.safe_load(fm_text) or {}
        if not isinstance(meta, dict):
            # YAML returned a non-dict (e.g., a bare string) — fall back
            import sys as _sys
            print(f"  ⚠️  frontmatter.py: yaml.safe_load returned {type(meta).__name__}, falling back", file=_sys.stderr)
            meta = _parse_handrolled(content)[0]
    except yaml.YAMLError as e:
        import sys as _sys
        print(f"  ⚠️  frontmatter.py: yaml.safe_load failed ({e.problem_mark}), falling back to handrolled", file=_sys.stderr)
        return _parse_handrolled(content)
    return meta, body


def parse_string(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse frontmatter from a string. Returns (meta, body)."""
    if _HAS_YAML:
        return _parse_yaml(content)
    return _parse_handrolled(content)


def parse_file(path: Path) -> Tuple[Dict[str, Any], str]:
    """Parse frontmatter from a file. Returns (meta, body)."""
    content = path.read_text(encoding="utf-8", errors="ignore")
    return parse_string(content)


# On import, lazily import re (only needed by handrolled parser)
import re  # noqa: E402


def backend() -> str:
    """Return which backend is active ('yaml' or 'handrolled')."""
    return "yaml" if _HAS_YAML else "handrolled"