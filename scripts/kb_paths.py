#!/usr/bin/env python3
"""
kb_paths.py - single source of truth for KB path resolution (v0.4.0)

ALL Python scripts (recall.py / forget.py / drift_check.py / regen_palace.py)
must import from here instead of duplicating KB_ROOT detection logic.

Bash scripts (bin/kb-workflow / install.sh) maintain their own equivalent
in shell. They MUST stay in sync — if you change the resolution chain
below, mirror the change in bin/kb-workflow lines 19-46.

Resolution chain (per-path env > KB_HOME > walk-up > default):

  KB_ROOT          — KB data dir override (highest priority)
  KB_HOME           — single-root env var (XDG-style)
  KB_STATE_FILE     — override _state.md path
  KB_CONFIG_FILE    — override config.local.yaml path
  KB_INDEX_FILE     — override external/_index.md path
  KB_WORKFLOW_HOME  — skill source dir (where SKILL.md lives)

  → if KB_STATE_FILE is set, KB_ROOT = dirname(KB_STATE_FILE)
  → if KB_CONFIG_FILE is set, KB_ROOT = dirname(KB_CONFIG_FILE)
  → if KB_INDEX_FILE is set, KB_ROOT = dirname(KB_INDEX_FILE)/external
  → if KB_HOME is set, KB_ROOT = KB_HOME
  → if KB_ROOT is set, use it
  → walk-up from cwd looking for .claude/kb/
  → walk-up from script_dir looking for .claude/kb/
  → $HOME/.claude/kb/  (POSIX) / $USERPROFILE\\.claude\\kb (Windows)

CLI:
  python3 kb_paths.py [--json] [--kb-root PATH] [--validate]

Examples:
  python3 kb_paths.py --validate       # check KB structure
  python3 kb_paths.py --json          # machine-readable for SKILL.md
  KB_ROOT=/x python3 kb_paths.py      # override + resolve
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional


def _walk_up(start: Path, target: str = ".claude/kb", stop_at: Optional[Path] = None) -> Optional[Path]:
    """Walk up from start looking for `target` directory.

    Stops when stop_at is reached (inclusive) or filesystem root.
    Returns the parent directory containing target/ if found, else None.
    """
    cur = start.resolve() if start.exists() else start
    stop_resolved = stop_at.resolve() if stop_at and stop_at.exists() else None

    while True:
        candidate = cur / target
        if candidate.is_dir():
            return cur
        if stop_resolved and cur == stop_resolved:
            return None
        parent = cur.parent
        if parent == cur:  # filesystem root
            return None
        cur = parent


def _user_home() -> Path:
    """Cross-platform home directory (Windows: USERPROFILE/HOMEDRIVE+HOMEPATH; POSIX: HOME)."""
    return Path.home()


def resolve_paths(
    *,
    kb_root: Optional[Path] = None,
    kb_home: Optional[str] = None,
    kb_state_file: Optional[str] = None,
    kb_config_file: Optional[str] = None,
    kb_index_file: Optional[str] = None,
    cwd: Optional[Path] = None,
    script_dir: Optional[Path] = None,
    home: Optional[Path] = None,
) -> dict:
    """Resolve all KB paths per the documented priority chain.

    Returns dict with: KB_ROOT, KB_STATE_FILE, KB_CONFIG_FILE, KB_INDEX_FILE,
    source (which rule fired), kb_home (single-root env if any).

    Override parameters take priority over env vars; env vars take priority
    over derived defaults.
    """
    cwd = cwd or Path.cwd()
    home = home or _user_home()
    script_dir = script_dir or Path(__file__).resolve().parent

    # Read env (allow override params to win)
    env = {
        "KB_ROOT": kb_root is None and os.environ.get("KB_ROOT"),
        "KB_HOME": kb_home is None and os.environ.get("KB_HOME"),
        "KB_STATE_FILE": kb_state_file is None and os.environ.get("KB_STATE_FILE"),
        "KB_CONFIG_FILE": kb_config_file is None and os.environ.get("KB_CONFIG_FILE"),
        "KB_INDEX_FILE": kb_index_file is None and os.environ.get("KB_INDEX_FILE"),
    }
    p = {
        "KB_ROOT": Path(kb_root) if kb_root else (Path(env["KB_ROOT"]) if env["KB_ROOT"] else None),
        "KB_STATE_FILE": Path(kb_state_file) if kb_state_file else (Path(env["KB_STATE_FILE"]) if env["KB_STATE_FILE"] else None),
        "KB_CONFIG_FILE": Path(kb_config_file) if kb_config_file else (Path(env["KB_CONFIG_FILE"]) if env["KB_CONFIG_FILE"] else None),
        "KB_INDEX_FILE": Path(kb_index_file) if kb_index_file else (Path(env["KB_INDEX_FILE"]) if env["KB_INDEX_FILE"] else None),
    }

    source = None

    # Rule 0: derive KB_ROOT from per-file overrides
    if p["KB_ROOT"] is None:
        if p["KB_STATE_FILE"] is not None:
            p["KB_ROOT"] = p["KB_STATE_FILE"].parent
            source = "derived from KB_STATE_FILE"
        elif p["KB_CONFIG_FILE"] is not None:
            p["KB_ROOT"] = p["KB_CONFIG_FILE"].parent
            source = "derived from KB_CONFIG_FILE"
        elif p["KB_INDEX_FILE"] is not None:
            # KB_INDEX_FILE = KB_ROOT/external/_index.md
            if p["KB_INDEX_FILE"].name == "_index.md":
                p["KB_ROOT"] = p["KB_INDEX_FILE"].parent.parent
                source = "derived from KB_INDEX_FILE"

    # Rule 1: KB_HOME env var (single-root)
    if p["KB_ROOT"] is None and env["KB_HOME"]:
        p["KB_ROOT"] = Path(env["KB_HOME"])
        source = "KB_HOME env"

    # Rule 2: KB_ROOT env var
    if p["KB_ROOT"] is None and p["KB_ROOT"] is None and p.get("KB_ROOT") is None and env["KB_ROOT"]:
        p["KB_ROOT"] = Path(env["KB_ROOT"])
        source = "KB_ROOT env"

    # Rule 3: walk-up from cwd
    if p["KB_ROOT"] is None:
        found = _walk_up(cwd)
        if found:
            p["KB_ROOT"] = found / ".claude/kb"
            source = "walk-up from cwd"

    # Rule 4: walk-up from script dir
    if p["KB_ROOT"] is None:
        found = _walk_up(script_dir, stop_at=home)
        if found:
            p["KB_ROOT"] = found / ".claude/kb"
            source = "walk-up from script_dir"

    # Rule 5: global default
    if p["KB_ROOT"] is None:
        p["KB_ROOT"] = home / ".claude/kb"
        source = "global default"

    # Derive per-file paths from KB_ROOT if not overridden
    if p["KB_STATE_FILE"] is None:
        p["KB_STATE_FILE"] = p["KB_ROOT"] / "_state.md"
    if p["KB_CONFIG_FILE"] is None:
        p["KB_CONFIG_FILE"] = p["KB_ROOT"] / "config.local.yaml"
    if p["KB_INDEX_FILE"] is None:
        p["KB_INDEX_FILE"] = p["KB_ROOT"] / "external" / "_index.md"

    return {
        **p,
        "source": source,
    }


def validate_structure(kb_root: Path) -> dict:
    """Check KB structure completeness. Returns health report."""
    report = {
        "kb_root": str(kb_root),
        "checks": [],
        "healthy": True,
    }
    # required directories
    for sub in ("entries", "external"):
        p = kb_root / sub
        if p.is_dir():
            ok = os.access(p, os.W_OK)
            report["checks"].append({
                "path": str(p), "status": "ok" if ok else "unwritable",
            })
            if not ok:
                report["healthy"] = False
        else:
            report["checks"].append({"path": str(p), "status": "missing"})
            report["healthy"] = False
    # required files
    for fname in ("_state.md", "config.local.yaml"):
        p = kb_root / fname
        if p.is_file():
            report["checks"].append({"path": str(p), "status": "ok"})
        else:
            report["checks"].append({"path": str(p), "status": "missing"})
            report["healthy"] = False
    p = kb_root / "external" / "_index.md"
    if p.is_file():
        report["checks"].append({"path": str(p), "status": "ok"})
    else:
        report["checks"].append({"path": str(p), "status": "missing"})
        report["healthy"] = False
    return report


def main():
    import argparse
    p = argparse.ArgumentParser(description="kb-workflow KB path resolver (SSOT)")
    p.add_argument("--json", action="store_true", help="output JSON for machine parsing")
    p.add_argument("--validate", action="store_true", help="also check structure completeness")
    p.add_argument("--kb-root", help="override KB_ROOT")
    args = p.parse_args()

    resolved = resolve_paths(
        kb_root=Path(args.kb_root) if args.kb_root else None,
    )

    if args.validate:
        report = validate_structure(resolved["KB_ROOT"])
        out = {"paths": resolved, "structure": report}
    else:
        out = resolved

    if args.json:
        # str-only output for JSON
        print(json.dumps({k: str(v) if isinstance(v, Path) else v
                          for k, v in out.items()}, ensure_ascii=False, indent=2))
    else:
        print("=== kb-workflow resolved paths ===")
        print(f"KB_ROOT:       {resolved['KB_ROOT']}    [{resolved['source']}]")
        print(f"KB_STATE_FILE: {resolved['KB_STATE_FILE']}")
        print(f"KB_CONFIG_FILE:{resolved['KB_CONFIG_FILE']}")
        print(f"KB_INDEX_FILE: {resolved['KB_INDEX_FILE']}")
        if args.validate and "structure" in out:
            print()
            print("=== structure health ===")
            for c in out["structure"]["checks"]:
                icon = "✅" if c["status"] == "ok" else ("⚠️ " if c["status"] == "unwritable" else "❌")
                print(f"  {icon} {c['status']:11} {c['path']}")
            print()
            print(f"overall: {'healthy' if out['structure']['healthy'] else 'NEEDS BOOTSTRAP'}")
            sys.exit(0 if out["structure"]["healthy"] else 1)


if __name__ == "__main__":
    main()