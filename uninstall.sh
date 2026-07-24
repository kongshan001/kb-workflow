#!/usr/bin/env bash
# uninstall.sh - clean removal of KB workflow
#
# By default keeps ~/.claude/kb/ (your data). Use --purge to remove it too.

set -euo pipefail

KB_ROOT="${KB_ROOT:-$HOME/.claude/kb}"
LOCAL_BIN="$HOME/.local/bin"
SKILL_DIR="$HOME/.claude/skills/kb-workflow"
WORKFLOW_HOME="${KB_WORKFLOW_HOME:-$HOME/kb-workflow}"

PURGE=false
[[ "${1:-}" == "--purge" ]] && PURGE=true

log() { printf '%b\n' "$*"; }
ok()  { log "  ✅ $*"; }
warn(){ log "  ⚠️  $*"; }

log "⚠️  Will remove:"
[[ -L "$LOCAL_BIN/kb-workflow" ]] && log "   - $LOCAL_BIN/kb-workflow (CLI symlink)"
[[ -d "$SKILL_DIR" ]]            && log "   - $SKILL_DIR (Skill)"
[[ -d "$WORKFLOW_HOME" && "$WORKFLOW_HOME" != "$KB_ROOT" ]] && log "   - $WORKFLOW_HOME (workflow source)"

if $PURGE; then
  log "   - $KB_ROOT (KB data — PURGE mode)"
else
  log ""
  log "📦 Your KB data in $KB_ROOT will be kept."
  log "   Use --purge to remove it too."
fi

log ""
read -r -p "Continue? [y/N] " ans
[[ "$ans" =~ ^[Yy]$ ]] || { log "Cancelled"; exit 0; }

[[ -L "$LOCAL_BIN/kb-workflow" ]] && rm "$LOCAL_BIN/kb-workflow" && ok "CLI removed"
[[ -d "$SKILL_DIR" ]]            && rm -rf "$SKILL_DIR"      && ok "Skill removed"
if [[ -d "$WORKFLOW_HOME" && "$WORKFLOW_HOME" != "$KB_ROOT" ]]; then
  rm -rf "$WORKFLOW_HOME" && ok "workflow source removed"
fi

if $PURGE; then
  rm -rf "$KB_ROOT" && ok "KB data purged"
else
  ok "KB data preserved at $KB_ROOT"
fi

log ""
log "✅ Uninstall complete"
