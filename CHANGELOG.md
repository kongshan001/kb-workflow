# Changelog

All notable changes to kb-workflow are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

## [Unreleased]

### Added
- **Natural language trigger "收录" + variants** (记下/记住/保存/存这个) added to defaults.yaml
  - User can now say "收录 <url|path|text>" to trigger capture
  - URL pattern → /kb-save-article flow
  - File path pattern → Read tool + /kb-capture flow
  - Plain text → /kb-capture flow with heuristic
- **`scripts/recall.py`** — explicit recall (诉求 2)
  - Text mode: keyword scoring (default)
  - Embed mode: ollama nomic-embed-text cosine
  - Returns ranked hits with file/snippet/score
  - Test results: query "RAG 引擎" → RAGFlow article (52.0); query "shader 性能" → Spector.js pref + 2 decisions; embed "如何优化 Three.js shader" → 0.74/0.65/0.62
- `/kb-recall <query>` slash command (replaces /kb-search in new code, /kb-search still works as alias)
- 6-scenario behavior contract covering both user requirements end-to-end

### Tested
- recall.py text mode: 3 queries verified to surface relevant entries
- recall.py embed mode: 1 query verified, returns semantically related content
- File path detection in natural language triggers (regex `^/[\\w/.-]+\\.[a-z]+$` etc.)
- URL pattern detection in natural language triggers

## [0.2.1] - 2026-07-25

### Added
- `regen_palace.py --plan` / `--apply` modes — generates structured JSON manifest
  that the assistant can iterate to call `mempalace_add_drawer` for real mirroring
  (was: dry-run only, "would mirror")
- `scripts/dedup.py` — semantic deduplication via ollama embeddings
  (default: nomic-embed-text). Pairs above threshold get flagged
  with options A/B/C/D (delete/refine/keep)
- `install.sh`: registers weekly Sunday 18:00 /kb-review summary cron
  via cc-connect (idempotent, graceful skip if cc-connect unavailable)
- Fresh install verification: install.sh works in isolated HOME + KB_ROOT env
- `specs/kb-workflow/plan.md` updated to v0.2.0 (D1 active-first, D2 external/,
  D4 trigger scope, D6 no_capture_intent, D8 external/ read, W2 slash set)
- 5-scenario behavior contract documented

### Fixed
- `regen_palace.py` now uses HTTP API for ollama (CLI subcommand missing
  in some ollama versions)

### Tested
- `dedup.py` on existing 6 entries: found 0.909 conflict (verified
  manual D5 detection) and 0.716 related pair (fact + decision on
  same topic — different perspectives, valid to keep both)

## [0.2.0] - 2026-07-25

### ⚠️ BREAKING CHANGES

**Polarity flip: default is now NO auto-store.**

- v0.1.x: assistant silently captured any input that matched heuristics
- v0.2.0: assistant does NOT auto-store. User must explicitly invoke:
  - `/kb-capture <text>` — for structured entries
  - `/kb-save-article <url or text>` — for raw external content
  - Natural phrases: "记住 X" / "别 X" / "以后 X" / "我决定 X"
- Assistant MAY offer (one-line prompt) when it sees something worth saving,
  but only if user didn't already invoke capture

### Added
- New slash command: `/kb-save-article` — proper external content flow
- New slash command: `/kb-capture-force <type> <text>` — skip heuristics
- `config/schema/external_article.yaml` — schema template for external articles
- `external/_index.md` — auto-maintained index of articles
- `config/defaults.yaml`: `capture.default_mode: active` + `capture.explicit_triggers`
- Assistant can suggest (one-line prompt) instead of silently storing
- D6 escalation: new trigger `no_capture_intent`

### Fixed
- `regen_palace.py`: now correctly parses nested `metadata:` frontmatter
  (previously missed `source_url`, `topic`, `key_points`, etc.)
- `kb-workflow status`: `external/` count now excludes `_index.md`
- Ticket format: now prefixes with `/kb-capture →` and `/kb-save-article →`
  for clarity of which command triggered the capture

### Changed
- Heuristics only run after explicit `/kb-capture` (was: every input)
- `external/` is now a first-class storage target (was: empty placeholder)
- Ticket format updated to reflect active-first model
- SKILL.md: behavior contract section explicitly states active-first

### Migration Notes from v0.1.x
- Existing entries (captured under v0.1.x auto-store) are preserved as-is
- New entries follow v0.2.0 active-first rules
- If you want to backfill an entry to the new model: delete + re-`/kb-capture`

## [0.1.2] - 2026-07-25

### Added
- USER_GUIDE.md — 14-section end-user handbook
  - 5-minute quick start
  - Daily usage (silent capture, tickets, slash commands)
  - 4-class entry schema with real examples
  - 5-red-light escalation rules
  - Cross-device workflow
  - Customization via config.local.yaml
  - Troubleshooting FAQ
  - Cheat sheet + recommended rhythm

## [0.1.1] - 2026-07-24

### Fixed
- `kb-workflow status`: precise entry counts by parsing frontmatter `type:` field
  (previously used grep heuristics that over-counted placeholder lines)
- `kb-workflow status`: now shows breakdown `fact=N preference=N decision=N tentative=N`
- Conflict / tentative counts: now parsed from `_state.md` section structure
  using `awk`, not blind grep

### Changed
- Version bumped to 0.1.1-dev
- README polished: real demo data, status output sample, known limitations section

## [0.1.0] - 2026-07-24

### Added
- Initial release
- 4-class schema: fact / preference / decision / tentative
- Heuristic auto-classification with audit trail
- Dedup / conflict / refine / update handling
- 5-red-light escalation rules
- Hybrid review (on-demand / cron / threshold)
- Layered recall (MEMORY.md untouched, _state.md on session start)
- One-click CLI: install / update / status / uninstall
- Capability detection with graceful degradation
- 10-topic starter whitelist
- Sample tested end-to-end on demo1 project

[Unreleased]: https://github.com/kongshan001/kb-workflow/compare/v0.2.2...HEAD
[0.2.0]: https://github.com/kongshan001/kb-workflow/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/kongshan001/kb-workflow/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/kongshan001/kb-workflow/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/kongshan001/kb-workflow/releases/tag/v0.1.0
