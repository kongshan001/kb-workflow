#!/usr/bin/env bash
# capability-detect.sh - detect host capabilities
# Outputs one line per capability in the format:
#   <name>: <status> [description]
#   status: on | off | n/a

set -euo pipefail

ok()    { printf '  %-20s %s\n' "$1" "✅ $2"; }
off()   { printf '  %-20s %s\n' "$1" "❌ $2"; }
na()    { printf '  %-20s %s\n' "$1" "— $2"; }
header(){ printf '\n'; }

# ---------- git (required) ----------
if command -v git >/dev/null 2>&1; then
  ok "git" "$(git --version | head -1)"
else
  off "git" "not installed (REQUIRED)"
fi

# ---------- bash (required) ----------
ok "bash" "$BASH_VERSION"

# ---------- Claude Code (assumed) ----------
if [[ -n "${CLAUDE_CODE:-}" ]] || [[ -d "$HOME/.claude" ]]; then
  ok "claude-code" "Claude Code environment detected"
else
  off "claude-code" "not detected (REQUIRED for Skill)"
fi

# ---------- MemPalace MCP ----------
# detect by checking if mcp_servers config references it
if [[ -f "$HOME/.claude.json" ]] && grep -q mempalace "$HOME/.claude.json" 2>/dev/null; then
  ok "mempalace" "MCP server registered"
elif [[ -f "$HOME/.claude/mcp_servers.json" ]] && grep -q mempalace "$HOME/.claude/mcp_servers.json" 2>/dev/null; then
  ok "mempalace" "MCP server registered"
else
  off "mempalace" "not registered (semantic search disabled; grep fallback)"
fi

# ---------- cc-connect ----------
if command -v cc-connect >/dev/null 2>&1; then
  ok "cc-connect" "$(cc-connect --version 2>/dev/null | head -1 || echo available)"
else
  off "cc-connect" "not installed (timed review disabled; on-demand only)"
fi

# ---------- python ----------
# v0.4.1 (issue #1 P1-④): check both `python3` and `python` — Windows typically
# only exposes `python` (no `python3`), old script hardcoded `python3`.
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
  ok "python3" "$(python3 --version 2>&1 | head -1)"
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
  ok "python"  "$(python --version 2>&1 | head -1) (Windows alias for python3)"
else
  PYTHON=""
  off "python3" "not installed (regen_palace.py will be skipped)"
fi

# ---------- network ----------
# v0.4.1 (issue #1 P1-④): use git ls-remote as primary — actual workflow
# needs git network anyway. curl probe was misleading (could pass while
# git was behind proxy, or vice versa).
if command -v git >/dev/null 2>&1; then
  if git ls-remote --heads --quiet https://github.com 2>/dev/null; then
    ok "network" "reachable (git ls-remote)"
  else
    off "network" "unreachable (update check disabled)"
  fi
elif command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 3 -o /dev/null https://github.com 2>/dev/null; then
    ok "network" "reachable (curl)"
  else
    off "network" "unreachable (update check disabled)"
  fi
else
  off "network" "curl not installed"
fi

# ---------- disk space ----------
local_kb="${KB_ROOT:-$HOME/.claude/kb}"
if [[ -d "$local_kb" ]]; then
  local_size=$(du -sh "$local_kb" 2>/dev/null | cut -f1 || echo "unknown")
  ok "kb_root" "$local_kb ($local_size)"
else
  na "kb_root" "$local_kb (not initialized)"
fi
