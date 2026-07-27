#!/usr/bin/env bash
# install.sh - KB workflow one-click installer (v0.3.4 with --local / --global)
#
# Usage:
#   ./install.sh                              # interactive: choose global or project-local
#   ./install.sh --global                     # install to ~/.claude/skills/kb-workflow/ (default)
#   ./install.sh --local                      # install to ./.claude/skills/kb-workflow/ (project)
#   ./install.sh --local --kb-root <path>     # project-local with custom KB root
#   ./install.sh --global --uninstall         # uninstall (global mode by default)
#   ./install.sh /path/to/local/repo          # install from explicit source path
#
# Install scopes:
#   --global  (default): ~/.claude/skills/, ~/.local/bin/, ~/.claude/kb/
#                      KB travels across projects — knowledge persists between repos
#   --local            : ./.claude/skills/, ./bin/, ./.claude/kb/
#                      KB stays in project — isolated, can be gitignored
#
# Detection chain in bin/kb-workflow (v0.3.4 Windows-aware):
#   readlink → .installed_source → heuristic (../ from script dir)
#   → KB_ROOT auto-detect: KB_ROOT env > cwd .claude/kb/ > ~/.claude/kb/

set -euo pipefail

# ---------- helpers ----------
log() { printf '%b\n' "$*"; }
ok()  { log "  ✅ $*"; }
warn(){ log "  ⚠️  $*"; }
fail(){ log "  ❌ $*"; exit 1; }

# Try a symlink; fall back to copy if ln -sf fails (Windows Git Bash).
# Returns 0 either way; sets SYMLINK_OK=1 if real symlink was created.
#
# v0.4.1 hardening (from issue #1 user testing):
#  - same-source-dest → no-op (return 0) — covers --local from repo dir
#  - target exists check uses -e not -L — MSYS ln creates real dir for
#    directory sources (exit 0 but [[ -L ]] is false)
#  - cp fallback uses -rf to handle directory sources like config/
make_link() {
  local src="$1" dst="$2"
  # P2-⑥: same-source-dest → already installed, no-op
  local src_resolved dst_resolved
  src_resolved="$(cd "$(dirname "$src")" 2>/dev/null && pwd)/$(basename "$src")"
  dst_resolved="$(cd "$(dirname "$dst")" 2>/dev/null && pwd)/$(basename "$dst")"
  if [[ "$src_resolved" == "$dst_resolved" ]]; then
    SYMLINK_OK=1
    return 0
  fi
  if ln -sf "$src" "$dst" 2>/dev/null; then
    # P0-①: use -e (target exists) not -L (Windows ln -sf for dirs creates
    # real dir, exit 0, but [[ -L ]] is false → fallback to cp which fails)
    if [[ -e "$dst" ]]; then
      SYMLINK_OK=1
      return 0
    fi
  fi
  # P0-①: fallback copy — use -rf to handle directory sources
  if command -v cp >/dev/null 2>&1; then
    cp -rf "$src" "$dst" 2>/dev/null && SYMLINK_OK=0 && return 0
  fi
  return 1
}

# ---------- preflight ----------
command -v git   >/dev/null 2>&1 || fail "git is required but not installed"
command -v bash >/dev/null 2>&1 || fail "bash is required"

# ---------- 0. parse flags + pick install scope ----------
# Flag precedence:
#   --global / --system   : explicit global install (~/.claude/kb/)
#   --local / --project   : explicit project install (./.claude/kb/)
#   (none) + project ctx  : default to --local (safer; project-scoped)
#   (none) + no project   : default to --global (no project to scope to)
# TTY always shows the prompt — never silently pollute ~/.claude/
SCOPE=""
UNINSTALL=0
SOURCE_ARG=""
CUSTOM_KB_ROOT="${KB_ROOT:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --global|--system)  SCOPE="global"; shift ;;
    --local|--project)  SCOPE="local"; shift ;;
    --uninstall)        UNINSTALL=1; shift ;;
    --kb-root)          CUSTOM_KB_ROOT="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,28p' "$0"; exit 0 ;;
    --*) fail "unknown flag: $1" ;;
    *)  SOURCE_ARG="$1"; shift ;;
  esac
done

# Detect project context (cwd has any of these markers → assume inside a project)
is_project_context() {
  [[ -d ".git" ]] || [[ -f "package.json" ]] || [[ -f "pyproject.toml" ]] || \
  [[ -f "Cargo.toml" ]] || [[ -f "go.mod" ]] || [[ -f "pom.xml" ]] || \
  [[ -f "build.gradle" ]] || [[ -f "*.csproj" ]] || [[ -f "Gemfile" ]] || \
  [[ -f "go.sum" ]] || [[ -f "Cargo.lock" ]]
}

# Determine default scope (only when user didn't pass a flag)
if [[ -z "$SCOPE" ]]; then
  if is_project_context; then
    SCOPE="local"
    log "  💡 detected project context (.git / package.json / pyproject.toml / etc.)"
    log "     defaulting to --local (KB stays in project, can be gitignored)"
  else
    SCOPE="global"
    log "  💡 no project markers in cwd"
    log "     defaulting to --global (KB lives in ~/.claude/kb/)"
  fi
fi

# TTY always shows the prompt — no silent installs to system dir
if [[ -t 0 ]]; then
  log ""
  log "  Where should kb-workflow install?"
  log ""
  log "    [L]  Local    — \${PWD}/.claude/skills/kb-workflow/ + \${PWD}/.claude/kb/"
  log "             KB stays in this project (can be gitignored)"
  log "             ← recommended if you have a project here"
  log ""
  log "    [G]  Global   — ~/.claude/skills/kb-workflow/ + ~/.claude/kb/"
  log "             KB travels across all your projects"
  log "             ← only if you want cross-project knowledge"
  log ""
  read -r -p "  Choose [L/G, default=L if in project, G otherwise]: " choice
  if [[ -n "$choice" ]]; then
    case "${choice,,}" in
      l|local|project) SCOPE="local" ;;
      g|global|system) SCOPE="global" ;;
      *) warn "invalid choice '$choice' — using detected default: $SCOPE" ;;
    esac
  fi
fi

# ---------- compute install paths based on scope ----------
if [[ "$SCOPE" == "local" ]]; then
  PROJECT_ROOT="$(pwd)"
  KB_ROOT="${CUSTOM_KB_ROOT:-$PROJECT_ROOT/.claude/kb}"
  SKILL_DIR="$PROJECT_ROOT/.claude/skills/kb-workflow"
  LOCAL_BIN="$PROJECT_ROOT/bin"
  ok "scope: project-local (paths under $PROJECT_ROOT)"
else
  KB_ROOT="${CUSTOM_KB_ROOT:-$HOME/.claude/kb}"
  SKILL_DIR="$HOME/.claude/skills/kb-workflow"
  LOCAL_BIN="$HOME/.local/bin"
  ok "scope: global (paths under \$HOME)"
fi

# ---------- 1. detect source ----------
SOURCE_PATH=""
GITHUB_REPO="${KB_WORKFLOW_REPO:-https://github.com/kongshan001/kb-workflow.git}"
WORKFLOW_HOME="${KB_WORKFLOW_HOME:-$HOME/kb-workflow}"

if [[ -n "$SOURCE_ARG" ]]; then
  # explicit local path
  SOURCE_PATH="$(cd "$SOURCE_ARG" && pwd)"
  log "📦 Local install from: $SOURCE_PATH"
elif [[ -f "./SKILL.md" && -f "./bin/kb-workflow" ]]; then
  # running from inside the repo
  SOURCE_PATH="$(pwd)"
  log "📦 Local install from: $SOURCE_PATH"
else
  # clone from GitHub
  log "📥 Cloning from GitHub: $GITHUB_REPO"
  if [[ -d "$WORKFLOW_HOME" ]]; then
    log "   existing $WORKFLOW_HOME found, pulling latest"
    git -C "$WORKFLOW_HOME" pull --ff-only || warn "pull failed, using existing"
  else
    git clone --depth 1 "$GITHUB_REPO" "$WORKFLOW_HOME" \
      || fail "clone failed — set KB_WORKFLOW_REPO env or pass local path"
  fi
  SOURCE_PATH="$WORKFLOW_HOME"
fi

[[ -f "$SOURCE_PATH/SKILL.md" ]]         || fail "SKILL.md not found in $SOURCE_PATH"
[[ -x "$SOURCE_PATH/bin/kb-workflow" ]]  || fail "bin/kb-workflow not executable in $SOURCE_PATH"
ok "source ready: $SOURCE_PATH"

# v0.3.4: detect platform early and warn about Windows symlink limitations
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*)
    warn "Windows detected ($(uname -s))"
    warn "Git Bash on Windows may fall back from 'ln -sf' to file copy."
    warn "installer will use make_link() with cp fallback + .installed_source file"
    ;;
esac

# ---------- 1.5. uninstall mode ----------
if [[ $UNINSTALL -eq 1 ]]; then
  log ""
  log "🗑️  Uninstalling kb-workflow ($SCOPE)..."
  # remove skill symlinks (rm works on real files + symlinks + dangling links)
  rm -f "$SKILL_DIR/SKILL.md" "$SKILL_DIR/config" "$SKILL_DIR/CHANGELOG.md"
  rmdir "$SKILL_DIR" 2>/dev/null || true
  # remove CLI
  rm -f "$LOCAL_BIN/kb-workflow" "$LOCAL_BIN/.installed_source"
  rmdir "$LOCAL_BIN" 2>/dev/null || true
  ok "removed: skill, CLI, .installed_source"
  # KB_ROOT: keep by default unless --purge
  warn "KB kept at: $KB_ROOT (pass --purge to also remove)"
  exit 0
fi

# ---------- 2. create KB root ----------
mkdir -p "$KB_ROOT/entries" "$KB_ROOT/external"
ok "KB root: $KB_ROOT"

# ---------- 3. symlink CLI ----------
mkdir -p "$LOCAL_BIN"
make_link "$SOURCE_PATH/bin/kb-workflow" "$LOCAL_BIN/kb-workflow"
if [[ "${SYMLINK_OK:-0}" -eq 1 ]]; then
  ok "CLI: $LOCAL_BIN/kb-workflow → $SOURCE_PATH/bin/kb-workflow (symlink)"
else
  warn "CLI: $LOCAL_BIN/kb-workflow (copy — symlink unavailable, e.g. Windows Git Bash)"
fi

# v0.3.4 Windows fallback: write .installed_source so bin/kb-workflow can
# resolve WORKFLOW_HOME even when the CLI was copied instead of symlinked.
echo "$SOURCE_PATH" > "$LOCAL_BIN/.installed_source"
ok ".installed_source written: $SOURCE_PATH"

# ensure ~/.local/bin is on PATH (only for global install)
if [[ "$SCOPE" == "global" ]]; then
  case ":$PATH:" in
    *":$LOCAL_BIN:"*) ;;
    *) warn "$LOCAL_BIN not in PATH; add it to your shell rc" ;;
  esac
fi

# ---------- 4. symlink Skill ----------
mkdir -p "$HOME/.claude/skills" "$SKILL_DIR"
make_link "$SOURCE_PATH/SKILL.md"       "$SKILL_DIR/SKILL.md"
make_link "$SOURCE_PATH/config"         "$SKILL_DIR/config"
if [[ -f "$SOURCE_PATH/CHANGELOG.md" ]]; then
  make_link "$SOURCE_PATH/CHANGELOG.md"  "$SKILL_DIR/CHANGELOG.md"
fi
ok "Skill: $SKILL_DIR"

# ---------- 5. config.local.yaml ----------
if [[ ! -f "$KB_ROOT/config.local.yaml" ]]; then
  cat > "$KB_ROOT/config.local.yaml" <<EOF
# Generated by kb-workflow install on $(date +%Y-%m-%d)
# Override values from defaults.yaml. See SKILL.md for full list.

# kb_root: $KB_ROOT

# topics:
#   add: []       # extra topics to whitelist (merged with defaults)
#   remove: []    # topics to disable on this device
EOF
  ok "config.local.yaml created"
else
  ok "config.local.yaml exists, keeping"
fi

# ---------- 6. _state.md ----------
if [[ ! -f "$KB_ROOT/_state.md" ]]; then
  cat > "$KB_ROOT/_state.md" <<EOF
# KB Runtime State

> Assistant-owned. Harness 不读此文件，每次会话开场由 assistant 主动 Read 一次。

last_updated: $(date +%Y-%m-%d)
last_review: null
last_capture: null

---

## ⚠️ 待裁定
> 空

## 🟡 Tentative Open
> 空

## 最近 10 条收录
> 空

## 主题触发 (topic → palace room)
> see config/topics.yaml

## 统计
- entries/: 0
- external/: 0
- 待裁定: 0
- tentative open: 0
EOF
  ok "_state.md created"
else
  ok "_state.md exists, keeping"
fi

# ---------- 7. capability detection ----------
if [[ -x "$SOURCE_PATH/scripts/capability-detect.sh" ]]; then
  log ""
  log "🔍 Capability detection:"
  "$SOURCE_PATH/scripts/capability-detect.sh" | sed 's/^/  /'
fi

# ---------- 7.5. cron registration (D7) ----------
if command -v cc-connect >/dev/null 2>&1; then
  log ""
  log "⏰ Registering /kb-review weekly cron (Sunday 18:00, summary only)..."
  # idempotent: cc-connect cron add returns error if exists; we tolerate
  if cc-connect cron add \
      --cron "0 18 * * 0" \
      --prompt "/kb-review summary" \
      --desc "kb-workflow weekly summary" \
      2>/dev/null; then
    ok "cron registered (Sunday 18:00)"
  else
    ok "cron already registered (skipped)"
  fi
else
  warn "cc-connect not available; skip cron registration"
  warn "to enable later: cc-connect cron add --cron '0 18 * * 0' --prompt '/kb-review summary'"
fi

# ---------- 8. record installed source ----------
echo "$SOURCE_PATH" > "$KB_ROOT/.installed_source"

# ---------- 9. banner ----------
log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "✅ KB workflow installed"
log "   workflow: $SOURCE_PATH"
log "   kb_root:  $KB_ROOT"
log "   cli:      $LOCAL_BIN/kb-workflow"
log "   skill:    $SKILL_DIR"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log ""
log "Next:"
log "  kb-workflow status        # check current state"
log "  Start a new Claude session to load the Skill"
log "  /kb-review                # trigger a review (inside Claude)"
log ""
log "Weekly review (Sunday 18:00) is registered via cc-connect cron"
log "if available. Disable: cc-connect cron del <job-id>"
