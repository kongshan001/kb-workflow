#!/usr/bin/env bash
# check-staleness.sh - check if workflow is behind remote
# Exits 0 if up-to-date or check skipped
# Prints "behind" to stdout if local is behind remote

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
if [[ -L "$SCRIPT_PATH" ]]; then
  REAL_SCRIPT="$(readlink -f "$SCRIPT_PATH" 2>/dev/null || readlink "$SCRIPT_PATH")"
else
  REAL_SCRIPT="$SCRIPT_PATH"
fi
WORKFLOW_HOME="$(cd "$(dirname "$REAL_SCRIPT")/.." && pwd)"

if [[ ! -d "$WORKFLOW_HOME/.git" ]]; then
  exit 0
fi

# need network + upstream
if ! git -C "$WORKFLOW_HOME" fetch --quiet 2>/dev/null; then
  exit 0
fi

local_commit=$(git -C "$WORKFLOW_HOME" rev-parse HEAD 2>/dev/null || echo "")
remote_branch=$(git -C "$WORKFLOW_HOME" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || echo "")
if [[ -z "$remote_branch" ]]; then
  exit 0
fi
remote_commit=$(git -C "$WORKFLOW_HOME" rev-parse "$remote_branch" 2>/dev/null || echo "")

if [[ -z "$local_commit" || -z "$remote_commit" || "$local_commit" == "$remote_commit" ]]; then
  exit 0
fi

echo "behind"
