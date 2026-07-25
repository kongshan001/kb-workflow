# Changelog

All notable changes to kb-workflow are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

## [Unreleased]

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

[Unreleased]: https://github.com/kongshan001/kb-workflow/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/kongshan001/kb-workflow/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/kongshan001/kb-workflow/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/kongshan001/kb-workflow/releases/tag/v0.1.0
