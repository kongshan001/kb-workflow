# kb-workflow Architecture

> Technical overview of the `kb-workflow` skill — what it does, what it
> runs on, and (just as importantly) what it deliberately does NOT use.

Last verified: 2026-07-27 · version: v0.3.3+

## TL;DR

A KB management skill for Claude Code, implemented as **shell + Python
stdlib + PyYAML + (optional) ollama + MemPalace MCP**, with **all data as
plain markdown in git-friendly files**. No database, no web server, no
LLM API, no Docker, no npm/pip dependency graph.

---

## 1. Languages & Runtimes

| Layer | Tech | Min version |
|---|---|---|
| Skill orchestration (`install.sh`, `bin/kb-workflow`) | bash | 3.2+ (POSIX + `[[ ]]` arrays) |
| Scripts (`recall.py`, `drift_check.py`, `forget.py`, `frontmatter.py`, etc.) | Python | 3.10+ (uses PEP 585 `list[float]`) |
| Config + schemas | YAML | 1.1+ |
| Docs + KB entries | Markdown | — |

**Target shells**: macOS/Linux bash, Git Bash on Windows (MINGW/MSYS/CYGWIN),
WSL. Windows-native cmd/PowerShell requires `KB_ROOT` env override (no `$HOME`).

## 2. Core Libraries

### Runtime dependencies

| Library | Version | Purpose |
|---|---|---|
| [PyYAML](https://pypi.org/project/PyYAML/) | 6.0.3 | `yaml.safe_load` for frontmatter (with handrolled fallback when unavailable) |
| Python `pathlib`, `argparse`, `subprocess`, `re`, `json`, `urllib.request` | stdlib | files, CLI, regex, HTTP |
| Python `datetime` | stdlib | `last_seen` date field |
| Python `ast`, `tokenize` | stdlib | syntax check during refactors |
| `os.environ` | stdlib | env var priority chain |

### Optional dependencies

| Tool | Required for | Fallback |
|---|---|---|
| `ollama` + `nomic-embed-text` model | `--mode embed` semantic recall | text-mode BM25 still works |
| `gh` CLI (authenticated) | GitHub URL capture (`/kb-save-article`) | falls back to fact entry with URL only |
| `git` | `install.sh` clone + `bin/kb-workflow update` | install requires git |
| `cc-connect` | Sunday 18:00 `/kb-review` cron | notification skipped silently |
| `cp` (POSIX) | Windows fallback when `ln -sf` fails | `install.sh` warns |

## 3. Storage Format

### Directory layout (`~/.claude/kb/` or `$KB_ROOT` / `$KB_HOME` override)

```
kb/
├── _state.md                       # assistant-maintained state
├── config.local.yaml               # user overrides
├── entries/                          # 4 types
│   ├── fact-slug.md
│   ├── preference-slug.md
│   ├── decision-slug.md
│   └── tentative-slug.md
└── external/
    ├── YYYY-MM-DD[-_]<topic>[-_]<slug>.md    # both `-` and `_` separators accepted
    └── _index.md                             # auto-maintained index
```

### Entry frontmatter (YAML)

```yaml
---
name: 2026-07-26-ml-modelfw-demo
description: ...
metadata:
  type: external_article
  source_url: https://github.com/...
  ingested_at: 2026-07-26
  last_seen: 2026-07-26
  content_sha: <git blob sha>
  topic: ml
  key_points:
    - ...
  linked_entries: []
  status: forgotten              # optional, set by /kb-forget soft-delete
  forgotten_at: 2026-07-27      # optional
---
# body...
```

### Schema sources

| File | Role |
|---|---|
| `config/schema/fact.yaml` | fact entry template |
| `config/schema/preference.yaml` | preference entry template |
| `config/schema/decision.yaml` | decision entry template |
| `config/schema/tentative.yaml` | tentative entry template |
| `config/schema/external_article.yaml` | external article template |
| `config/defaults.yaml` | runtime defaults (capture mode, ticket format, paths) |
| `config/heuristics.yaml` | `/kb-capture` type-detection rules (priority-based, URL rule removed v0.3.0) |
| `config/topics.yaml` | 14-topic whitelist |

## 4. External Integrations

| Integration | Purpose | Notes |
|---|---|---|
| `mcp__mempalace__mempalace_search` | Semantic search across mirrored KB | KB → palace via `regen_palace.py --apply` |
| `gh` CLI | GitHub URL capture (`gh repo view`, `gh api`, `gh repo clone`) | Requires `gh auth login` |
| `ollama` + `nomic-embed-text` | Semantic recall (`--mode embed`) | Local HTTP service |
| `cc-connect` | Sunday 18:00 cron for `/kb-review` summary | Optional |
| `codegraph` MCP (mentioned in tools) | Code structure exploration | **Not indexed for kb-workflow-dev**; requires `codegraph init` |
| `context7` MCP (mentioned in tools) | Live library docs | Disconnected in current session |

## 5. Trigger Sources

### Slash commands (11)

```
/kb-capture <text>             # structured entry (entries/)
/kb-save-article <url|text>    # raw article (external/, fetches + indexes)
/kb-capture-force <type> <t>  # skip heuristic
/kb-recall <query>             # search with --topic / --format json / --mode
/kb-forget <slug>              # soft-delete (rename + status=forgotten)
/kb-review                     # weekly review trigger
/kb-status                     # current state summary
/kb-evolve                     # D10 self-audit (drift_check.py)
/kb-workflow {status,update,uninstall,install,doctor,version}
```

### Natural phrases (D1 routing)

| Phrase | Maps to |
|---|---|
| `收录 X` | `/kb-save-article X` (URL/path/text auto-detect) |
| `记下 / 记住 / 记一下 X` | `/kb-capture X` |
| `别 / 不要 / 以后都 X` | `/kb-capture X` (preference) |
| `我决定 / 我们敲定 X` | `/kb-capture X` (decision) |
| `想试试 / 也许 X` | `/kb-capture X` (tentative) |
| `查一下 / KB 里有没有 X` | `/kb-recall X` |

### Cron

`cc-connect cron add` registers weekly Sunday 18:00 `/kb-review summary` (idempotent, skipped silently if already exists).

## 6. Distribution

```
install.sh
  ├── source: GitHub clone (kongshan001/kb-workflow) OR local path
  ├── mode:   --global (default, ~/.claude/) | --local ($PWD/.claude/) | --system (= --global)
  ├── detect: project context (.git / package.json / pyproject.toml) → default scope suggestion
  └── prompts: TTY always asks [L/G]; non-TTY defaults based on context

POSIX install:
  ln -sf source target   → real symlink
  write .installed_source with absolute path

Windows Git Bash install:
  ln -sf may silently fall back to file copy
  → bin/kb-workflow resolves WORKFLOW_HOME via fallback chain (v0.3.4):
    1. readlink -f
    2. .installed_source file
    3. heuristic (../ from script dir)

PATH resolution chain in bin/kb-workflow:
  KB_HOME env (single-root, XDG-style)
    > KB_ROOT env
      > walk-up discovery from SCRIPT_DIR
        > $HOME/.claude/kb/  (fallback)
  Per-path overrides (KB_STATE_FILE / KB_CONFIG_FILE / KB_INDEX_FILE) win over derived defaults
```

### `kb-workflow doctor` (v0.3.4)

Diagnostic command that prints:
- Platform info (uname, $HOME, $USERPROFILE on Windows)
- Resolved paths for all env vars (`← env` annotation when overridden)
- Health checks (writable? missing?)
- Exit code 1 if issues found (CI-friendly)

## 7. Recall Mechanism (v0.3.4)

```
/kb-recall "query" [--topic T] [--format json|text] [--mode text|embed] [--limit N]
```

### Pipeline

```
1. topic filter (optional)
   - if --topic T: keep only entries where metadata.topic == T
   - entries/ items have no topic → excluded when --topic is set

2. score (per file)
   - text-mode (default): BM25-like
     score += body_lower.count(term) × 2        # substring density
     score += 1 if \b<term>\b matches           # word-boundary bonus
   - embed-mode: ollama cosine similarity

3. extract_snippet (v0.3.4 upgrade)
   - finds first query term occurrence
   - returns ±400 chars window centered on match
   - finds nearest preceding ## heading → section_anchor
   - trims at paragraph boundary when extracting from start

4. build hit (v0.3.4)
   {
     file, name, type, description,
     topic, source_url, last_seen,
     section_anchor, snippet,
     score
   }

5. output
   - text (default): emoji-formatted, human-readable
   - json: structured, machine-readable, includes all citation fields
```

### JSON fields (for Claude synthesis)

- `name` / `file` — KB entry identification
- `topic` / `source_url` — provenance + clickable verification
- `last_seen` — freshness check (e.g., is this entry stale?)
- `section_anchor` — which `##` heading the match is in
- `snippet` — query-term-anchored context window
- `score` — relevance

**Claude synthesis pattern**: read JSON → cite each `[name § section_anchor]` →
on user question "how do you know?", give `source_url` for verification.

## 8. KB ↔ MemPalace Sync

```
KB external/ entries (markdown with frontmatter)
  ↓ regen_palace.py --apply (manual or cron'd)
MemPalace drawers (per topic: kb_external/<topic>)
  ↓ mempalace_search (semantic)
```

**Current status**: not auto-triggered. Run `regen_palace.py --apply` after
batch updates, or wire into `install.sh` / cron.

Topic mapping: `metadata.topic` → `kb_external/<topic>/` room.

## 9. Deliberately NOT Used

These were considered and rejected — staying explicit helps future contributors:

| Technology | Why excluded |
|---|---|
| Database (SQLite/Postgres) | KB is plain markdown, git-friendly, human-readable |
| Web framework (FastAPI/Flask) | Skill runs in Claude Code MCP context, no HTTP needed |
| Docker | Skill is bash + Python, runs natively on any Unix-like |
| TypeScript / Node.js | Zero JS in entire project (skill metadata is YAML) |
| Direct LLM API (Anthropic SDK) | Claude Code is the inference layer; skill is data layer |
| Vector DB (chromadb/qdrant) | KB not vectorized — recall is BM25 + optional ollama embed |
| OAuth / auth | Skill runs in local user context, no server exposed |
| Test framework (pytest/...) | **Critical gap**: no tests/, no CI (tracked as v0.4.x) |

## 10. File Inventory

```
skill repo (v0.3.3+ tagged):
├── bin/kb-workflow              # bash CLI (~200 lines, 6 subcommands)
├── install.sh                   # bash installer (~200 lines, --local/--global)
├── scripts/
│   ├── recall.py                # Python, ~320 lines, --format json + --topic
│   ├── drift_check.py           # Python, ~270 lines, 4-check auditor
│   ├── forget.py                # Python, ~250 lines, D12 soft-delete
│   ├── frontmatter.py           # Python, ~130 lines, shared YAML parser
│   ├── dedup.py                 # Python, ~190 lines, semantic dedup
│   ├── regen_palace.py          # Python, ~180 lines, KB → palace mirror
│   └── capability-detect.sh     # bash, ~60 lines
├── config/
│   ├── defaults.yaml            # ~200 lines, runtime defaults
│   ├── heuristics.yaml          # ~60 lines (URL rule removed v0.3.0)
│   ├── topics.yaml              # ~50 lines, 14 topics
│   └── schema/                  # 4 schema templates
├── SKILL.md                     # ~600 lines, 12 D sections (D1-D12)
├── USER_GUIDE.md                # ~330 lines, user-facing
├── CHANGELOG.md                 # ~250 lines, [Unreleased] + history
├── ARCHITECTURE.md              # this file
├── README.md
└── .gitignore                   # excludes __pycache__, venv/, IDE files
```

## 11. Conventions

### Branch & release

- Main branch: `main`
- Release tags: `vX.Y.Z` (e.g., v0.1.1, v0.2.0, v0.2.1, v0.2.2, v0.3.3)
- Active dev: `[Unreleased]` section in CHANGELOG.md
- `bin/kb-workflow VERSION` is the source of truth (must match CHANGELOG top release)

### Commit style

```
<type>(scope): <subject>

[body with bullet points]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat` / `fix` / `docs` / `chore` / `refactor`. Scopes: `install` / `rec` / `frontmatter` / `palace` / `schema` / `config` / `docs`.

### Code style

- **Python**: PEP 8, type hints preferred, no classes unless needed (scripts are functional)
- **Bash**: `set -euo pipefail`, `[[ ]]` not `[ ]`, quoted vars, `local` in functions
- **YAML**: 2-space indent, no tabs, `#` comments explain non-obvious choices

## 12. Known Gaps (tracked for v0.4.x)

From independent production-readiness assessment + user feedback:

| Priority | Issue | Status |
|---|---|---|
| Critical | No tests/, no CI, no `pyproject.toml` | Open |
| Critical | KB index file write not atomic (TOCTOU race) | Open |
| High | `bin/kb-workflow update` doesn't compare semver | Open |
| High | Python 3.10+ requirement not documented in install preflight | Open |
| High | D6 sensitive_data escalation is purely advisory | Open |
| Medium | `recall.py` text-mode scoring doesn't filter by `expires_at` or `confidence` | Open |
| Medium | `dedup.py` is O(N²) pairwise | Open |
| Medium | No structured logging (`logging` module) | Open |
| Low | `README.md` still mentions "静默收录" (stale, contradicts active-first) | Open |
| Low | `USER_GUIDE.md` default-topic-count text says 10 (actual: 14) | Open |

---

## See Also

- `SKILL.md` — behavior contract (D1-D12)
- `USER_GUIDE.md` — end-user handbook
- `CHANGELOG.md` — version history + D10 evolution log
- `config/defaults.yaml` — runtime defaults reference