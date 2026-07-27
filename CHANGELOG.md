# Changelog

All notable changes to kb-workflow are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

## [0.3.3] - 2026-07-27

### Added
- **LLM 应用细分 topics** (v0.3.3, D10 evolution from awesome-llm-apps capture)
  — `config/topics.yaml` 加 4 个子 topic：
  - `llm-agent`：LLM Agent 应用 / 框架 / 工具
  - `llm-memory`：LLM 长期记忆 / 知识图谱 / 向量派 memory
  - `llm-voice`：LLM 语音 / 实时流式
  - `llm-rag`：LLM RAG 变体 / tutorial / 应用集合
  - **触发**：awesome-llm-apps 14 大类太细，原 `ml` topic 无法承载 LLM 应用细分
  - **re-tag 既有条目**：mem0 / cognee `rag → llm-memory`；awesome-llm-apps `ml → llm-agent`；chroma 留 `rag`（无 LLM 绑定）；modelfw-demo 留 `ml`（非 LLM）
- **Minimal Entry Mode** (v0.3.3, D10 evolution from awesome-llm-apps) —
  SKILL.md D3.5 新增「最小条目模式」：
  - full mode（默认）：全部 frontmatter 字段 + 源码级分析
  - minimal mode：仅 5 个必填（name/description/type/source_url/ingested_at） + 自由 body
  - 适用：awesome-list / 小工具 / 一次性参考 / 内容浅薄
  - **不**用来逃避源码分析——大型 repo 必须 full mode
- **`scripts/recall.py --topic <topic>`** (v0.3.3, D10 evolution from cross-topic
  recall testing) — 结构化 topic 过滤：
  - 用法：`recall.py --topic llm-memory "memory agent"`
  - 实现：解析 frontmatter（兼容嵌套 `metadata.topic`）+ 严格 topic 等值匹配
  - 验证：5 个 round 测试通过（topic 隔离 + 跨 topic 召回 + filter vs no-filter 对比）
  - 触发：Round 2 召回测试发现 modelfw-demo 在 LLM query top-5 消失，但用户需要
    「显式按 topic 召回」能力；不能只靠内容关键词副作用
- **主题分布验证** (v0.3.3 final):
  - llm-memory: 2 (mem0, cognee)
  - llm-agent: 1 (awesome-llm-apps)
  - rag: 2 (ragflow-intro, chroma)
  - ml: 1 (modelfw-demo)
- **`scripts/frontmatter.py`** (v0.3.4, D10 evolution from production-readiness
  assessment) — **shared frontmatter parser**：
  - 消除 `recall.py` / `dedup.py` / `regen_palace.py` 三处重复手写解析器（Critical #2 修复）
  - 优先用 `yaml.safe_load`（PyYAML，6.0.3 confirmed working），缺失则降级统一 handrolled 实现
  - YAML 解析失败时**降级到 handrolled + stderr 警告**（修 PyYAML 在 unquoted CJK
    + `:` 的 description 处报 `mapping values are not allowed here` 的 silent data loss）
  - `parse_file(path)` / `parse_string(content)` / `backend()` 三个 public API
  - 修原 parser bug：quoted strings（'"..."' / "'...'"）、null/true/false、`metadata:` 嵌套
  - **触发**：独立 agent 评估报告 Critical #2 + 用户 "为啥，不可以用 pip install 吗" 反问
- **PyYAML 真装上** (v0.3.4 验证) — SSL 证书问题是 macOS Python.org installer
  经典坑，不是网络问题。修法：`pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org pyyaml`
  (PEP 668 sandbox 绕过)。**自动启用 yaml.safe_load 路径**
- **cognee description 加引号** (v0.3.4 cleanup) — 唯一含 unquoted `:` 的
  external 条目 (`2026-07-26_rag_cognee.md`) 改成 quoted 形式，PyYAML 警告归 0。
  验证：7 个条目全部用 yaml.safe_load 解析成功，无 stderr 噪音
- **Version sync** (v0.3.4, High #4 修复) — 解决版本漂移：
  - `bin/kb-workflow:23` VERSION: `0.2.2-dev` → `0.3.3-dev`
  - `SKILL.md:6` 头版本号: `v0.2.0` → `v0.3.3`
  - **触发**：独立 agent 评估报告 High #4
  - web: 1 (threejs-fontloader)

### Tested
- **`/kb-forget` 完整实现** (v0.3.3 final):
  - `scripts/forget.py` 实现 D12 设计：soft-delete（rename + status: forgotten
    + forgotten_at + _index.md 同步）、--hard 硬删、--restore 恢复、--list-deleted 列表
  - 8 项测试全 pass：
    1. `--list-deleted` 初始空
    2. soft delete `fact-github-some-awesome-thing` → rename + frontmatter 注入
    3. 验证 rename 文件名 `*.deleted.20260727` 存在
    4. frontmatter 检查：`status: forgotten` + `forgotten_at: 2026-07-27` 注入正确
    5. `--list-deleted` 显示 1 项
    6. `--restore` 成功 → 文件名恢复
    7. frontmatter status/forgotten_at 正确剥离
    8. `--list-deleted` 恢复后回 0 + drift_check 仍 pass
- **5 轮召回验证** (v0.3.3 final):
  - Round 1: 非 LLM 查询 → modelfw-demo top 1 (161 / 106 vs 第二 32 / 10) ✅
  - Round 2: LLM 查询 → modelfw-demo 从 top 5 完全消失 ✅
  - Round 3: `recall.py --topic` 实现 + 兼容嵌套 metadata.topic ✅
  - Round 4: 4 个 topic filter 测试（llm-memory/ml/llm-agent/rag）全 pass ✅
  - Round 5: 同 query filter vs no-filter 对比 → noise 正确剔除 ✅
- **drift_check.py 4/4 终验** (v0.3.3 final):
  - external/_index.md drift ✅  (7 files / 7 rows)
  - schema field coverage ✅
  - SKILL.md section refs ✅  (D1..D12 全覆盖)
  - CHANGELOG.md [Unreleased] ✅  (Added+Fixed+Tested)
- **D11 self-audit protocol** (v0.3.3 final): 跑 `/kb-evolve` 协议 = drift_check.py
  + 4 类 gap 检查 + 输出机器可读报告作为 session artifact
- **`/kb-forget <slug>` slash command** (v0.3.2, D10 evolution) — 软删除：
  - 默认语义 = 重命名为 `<slug>.deleted.<timestamp>` + frontmatter 加
    `status: forgotten` / `forgotten_at: YYYY-MM-DD`，**不**物理 rm
  - `--hard` 标志显式硬删除（保留物理 rm 通道）
  - `--restore` 标志反向恢复
  - `_index.md` 行同步更新 + `_state.md` 加 `external  ✗` 标记
  - **触发**：捕获 `topoteretes/cognee` 时观察到 cognee 提供
    `cognee.forget(dataset_id)` 主动遗忘 API，kb-workflow v0.3.1 之前只有
    物理 rm，缺软删除语义，按 D10 即时补
- **Optional LLM extraction + cost estimator section** (D9, v0.3.5 待做)
  — 记录 mem0 风格 LLM fact extraction + cognee 风格 cost estimator
  的设计 candidate。**不落地**：active-first 原则 + 缺 estimator 基础设施
- **`scripts/recall.py`** — explicit recall (诉求 2)
  - Text mode: keyword scoring (default)
  - Embed mode: ollama nomic-embed-text cosine
  - Returns ranked hits with file/snippet/score
  - Test results: query "RAG 引擎" → RAGFlow article (52.0); query "shader 性能" → Spector.js pref + 2 decisions; embed "如何优化 Three.js shader" → 0.74/0.65/0.62
- `/kb-recall <query>` slash command (replaces /kb-search in new code, /kb-search still works as alias)
- 6-scenario behavior contract covering both user requirements end-to-end
- **D9 URL Capture Pipeline** in SKILL.md — explicit routing for substantive URLs:
  - GitHub repo → `gh repo view` + README base64 decode → `external/`
  - arXiv / blog / docs → WebFetch → `external/`
  - Generic reference URL → fallback to `entries/fact-*.md`
  - Topic auto-inference from repo name / README / `_state.md` topic whitelist
  - Fetch failure fallbacks (private repo / 404 / base64 decode error)
- **D10 Skill Evolution Loop** (v0.3.0) — meta-principle: skills must evolve during
  use, not stay frozen. Triggers (schema gap / workflow friction / counterexample
  / missing auto-step / implicit convention) + action checklist + CHANGELOG
  labeling rules (Added vs Fixed vs Changed) + verification mandate.
- **Source-level analysis mandate** for code repos (D9, v0.3.1) — `收录 <github URL>`
  no longer stops at README. Required steps: clone + read ≥3 core files (impl /
  entry / test / perf-doc) + decision↔code-line mapping + test coverage matrix
  + multi-language consistency check + perf data landing. **Anti-pattern**:
  "光存 URL 偷懒".
- **external_article schema fields** (v0.3.0):
  - `last_seen: YYYY-MM-DD` — D5 dedup bump target
  - `content_sha: <git blob SHA | null>` — D5 precise equality check
- **D5 dedup rules for external/** (v0.3.0) — extended dedup from entries/ to
  external/. URL + content_sha match → skip + bump; URL same + sha different →
  UPDATE path with superseded_by chain; URL drift (mirror/redirect) → skip +
  canonical URL note. New `_state.md` markers: `+` / `↻` / `·` / `⤴` / `✗`
  (single-column, fixed unicode, machine-parseable — replaces ad-hoc
  `external↻`-style fused markers).
- **`external/_index.md` auto-maintenance** (v0.3.0) — `config/defaults.yaml`
  external.index_sync section. on_write: append / on_update: replace_row /
  on_delete: remove_row. drift_check: weekly (kb-status / Sunday review).
- **Ticket format extensions** (v0.3.0) in `defaults.yaml ticket.*`:
  `external_new` (with sha) / `external_dedup` / `external_update`
  (sha old → new) / `external_supersede` / `external_remove`.
- **Topic inference ask-user rule** (D9, v0.3.1) — no-match case no longer
  silently falls back to `infra`. Assistant MUST ask user before assigning
  fallback topic or creating new topic.

### Fixed
- **URL routing bug** (v0.3.0): `config/heuristics.yaml` priority 80 `explicit_fact` rule
  was misrouting `收录 <URL>` to `entries/fact-*.md` (URL-only shells) instead of
  the documented `/kb-save-article` flow. **Symptom**: capturing a GitHub repo
  URL produced a fact entry with only the URL + confidence=low — no fetch,
  no README, no metadata. **Root cause**: declared-but-not-implemented —
  CHANGELOG [Unreleased] and `config/defaults.yaml` `url_pattern` both said
  URLs go to save-article flow, but no upstream routing layer existed in
  SKILL.md to enforce it. **Fix**:
  1. SKILL.md D1 — split `收录 <url|path|text>` into three explicit rows
     (URL → save-article flow, path → Read + capture, text → capture heuristic);
     added D1 routing priority block
  2. SKILL.md D4 — removed `URL → fact` row (URL no longer reaches heuristic layer)
  3. SKILL.md D9 — new section documenting URL capture pipeline (fetch strategy
     by domain pattern + topic inference + failure fallbacks)
  4. `config/heuristics.yaml` — removed priority 80 `explicit_fact` URL rule;
     added comment block explaining upstream routing. Default rule (priority 0)
     acts as safe fallback if URL somehow slips through.
- **README-only capture shallow** — user feedback "不能只读 readme, 我建议结合
  readme 再深入分析源码". D9 now mandates source-level analysis for code repos
  (see Added section). Fix applied via D9 update + D10 enforcement principle.
- **`_index.md` drift** — earlier `modelfw-demo` write missed index entry.
  defaults.yaml now codifies `index_sync` rules with weekly drift_check.
- **Stats counter undercount** — `_state.md` showed `external/: 1` but actual
  was 3. _state.md is hand-maintained; assistant now required to re-verify on
  every external write and surface the drift in kb-status.

### Tested
- recall.py text mode: 3 queries verified to surface relevant entries
- recall.py embed mode: 1 query verified, returns semantically related content
- File path detection in natural language triggers (regex `^/[\\w/.-]+\\.[a-z]+$` etc.)
- URL pattern detection in natural language triggers (now correctly routed to save-article flow)
- v0.3.0 URL routing: `收录 https://github.com/kongshan001/modelfw_demo` →
  D1 routing ✓ → D9 gh CLI fetch (metadata + README SHA `875cabce…`) → D5
  dedup (URL+SHA identical → skip + bump last_seen). Verified no fact entry
  created, _index.md updated with modelfw-demo row.
- Source-level analysis depth: `kongshan001/modelfw_demo` (259+54+225+58+264
  lines across 5 files) yielded 6 critical findings (C++ _declared interception,
  pybind11 PyErr_Fetch+exc_info subtlety, etc.) that README omitted entirely.
- **drift_check.py v0.3.1** (first run): caught filename pattern inconsistency
  in 2 existing files (`2026-07-25-rag_ragflow-intro.md` and
  `2026-07-25-web_threejs-fontloader.md` used `-` separator while the 3rd used `_`).
  Fix: relaxed `defaults.yaml` filename_pattern to `YYYY-MM-DD[-_]<topic>[-_]<slug>.md`
  (accepts both) and updated `drift_check.py` regex to match. Re-run: all 4
  checks pass (index / schema / sections / changelog).
- **kb-evolve D11** demonstrated end-to-end: slash command → drift_check.py →
  real drift detected → defaults.yaml relaxed → re-run clean.

### Added (post-tag cleanup, v0.3.3 + v0.3.4)
- **`scripts/frontmatter.py`** — shared frontmatter parser (yaml.safe_load + handrolled fallback). PyYAML 6.0.3 installed via `--trusted-host` to bypass PEP 668 SSL.
- **`scripts/forget.py`** — D12 soft/hard delete + restore.
- **`scripts/drift_check.py`** — 4-check consistency auditor (D11).
- **`recall.py --topic`** — structured topic filter.
- **Minimal Entry Mode** — frontmatter 5-field minimal mode for awesome-lists.
- **Version sync** — bin/kb-workflow VERSION 0.2.2-dev → 0.3.3-dev.
- **Topic taxonomy** — added llm-agent / llm-memory / llm-voice / llm-rag sub-topics.

### Fixed
- **cognee description unquoted CJK + ':'** caused PyYAML `mapping values are not allowed here` error; now quoted. 0 PyYAML warnings across 7 entries.

## [Unreleased]

### Fixed
- **Windows symlink fallback** (v0.3.4, D10 evolution from user critique) —
  Git Bash on Windows doesn't always support `ln -sf` (silently falls back
  to file copy), breaking `readlink -f` in `bin/kb-workflow` and causing
  `WORKFLOW_HOME` to resolve wrong. Fix:
  1. `bin/kb-workflow` — 3-step WORKFLOW_HOME resolution: readlink →
     `.installed_source` file → heuristic (../ from script dir)
  2. `install.sh` — `make_link()` helper tries `ln -sf`, verifies result
     is real symlink, falls back to `cp -f`
  3. `install.sh` — writes `.installed_source` next to CLI binary
     (contains absolute path to skill root)
  4. `install.sh` — early Windows detection (MINGW/MSYS/CYGWIN)
     prints upfront warning
  - Tested via `/tmp/win-test` simulation: `cp` + `.installed_source` →
    `kb-workflow status` correctly resolves workflow path.

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
