---
name: kb-workflow
description: KB 收录与管理工作流（active-first）。Use when user invokes /kb-capture, /kb-save-article, /kb-recall, /kb-review, /kb-search, /kb-status, /kb-workflow update — or says "收录 X / 记住 X / 别 X / 以后 X / 保存这篇文章". Default behavior: do NOT auto-store anything.
---

# KB WorkFlow v0.3.3 — Assistant 行为手册

> 本文件由 `kb-workflow install` 链接到 `~/.claude/skills/kb-workflow/SKILL.md`。
> 启动时自动加载。规范在 `config/defaults.yaml`，按设备 override 在 `~/.claude/kb/config.local.yaml`。

## 核心原则：Active-first

**默认 = 不存任何东西。** 用户必须显式触发 capture，助手才落盘。

> 这是 v0.2.0 的极性翻转。v0.1.x 默认静默收录；v0.2.0 起反过来。

---

## 启动流程

每个会话开场：

### 步骤 1：发现 KB 位置（**关键 — 不能跳过**）

D2 写了 walk-up discovery 优先级，但**启动流程必须真的执行**：

```
KB_ROOT 解析优先级（v0.3.4 — 必须按顺序尝试）：
1. KB_ROOT env var               ← 最高优先级（user 显式 override）
2. KB_HOME env var (single-root)  ← XDG-style 单一根
3. walk-up from cwd: 从 ${CWD} 往上找 .claude/kb/
   - 例：cwd = g:\project\kb-workflow-demo
     → g:\project\kb-workflow-demo\.claude\kb  ← 命中
   - 一直 walk-up 到 / 或 盘符根
4. walk-up from SKILL install dir: ~/.claude/skills/kb-workflow/
5. $HOME/.claude/kb/              ← 全局默认（POSIX）
   Windows-native: C:\Users\<user>\.claude\kb\
   WSL: /home/<user>/.claude/kb/  (与 Windows host 隔离)
```

**禁止**：直接 Read `~/.claude/kb/_state.md`（硬编码路径）。Windows-native
cmd/PowerShell 没有 `$HOME`；project-local install (`./install.sh --local`)
下 KB 在项目目录而非 `~/.claude/kb/`。

### 步骤 2：读 state + 检查队列

1. **Read** `$KB_ROOT/_state.md`（用步骤 1 解析的路径）
2. 检查 `⚠️ 待裁定` / `🟡 Tentative Open` 数量
3. 如果 `_state.md` 不存在 → 用 `doctor` 类命令诊断（v0.3.4 新增）

### 步骤 3：启动 banner

```
✅ KB workflow v{VERSION} loaded
   mode: active-first (no auto-store)
   kb_root: {resolved path}
   entries: {N} | external: {N} | 待裁定: {N} | tentative: {N}
```

`VERSION` 从软链目标的 `bin/kb-workflow VERSION=` 字符串读取。

---

## D1 触发模型：active-first

| 用户输入 | 助手行为 |
|---|---|
| **普通说话 / 提问 / 闲聊** | **不存**。按需要正常回答。 |
| `/kb-capture <content>` | 存。启发式分类，4 类 schema，写入 entries/。**只接纯文本 / 文件路径；URL 已被路由层截走，不会到达此命令**。 |
| `/kb-save-article <url or text>` | 存。原始资料流：fetch 内容 → 写 external/ → 镜像 MemPalace。 |
| `收录 <URL>`（`https?://` / `www.` 开头） | **走 `/kb-save-article` 流**：按 URL 模式 fetch → 写 external/（见 D9）。fetch 失败时降级为 fact 条目（仅 URL + 失败原因）。 |
| `收录 <文件路径>`（如 `~/docs/notes.md`） | 助手 Read 文件 → 走 `/kb-capture` 流程 |
| `收录 <纯文本>` | 走 `/kb-capture` 流程（启发式判 type） |
| `收一下` / `记下` / `记住` / `记一下` / `保存` / `存这个` | 等同 `收录 <纯文本>` → `/kb-capture` |
| `以后 X` / `别 X` / `永远 Y` | 等同 `/kb-capture X`（preference 信号） |
| `我决定 X` / `我们敲定 Y` | 等同 `/kb-capture X`（decision 信号） |
| `保存这篇文章 <url>` / `记下这个文档` | 等同 `/kb-save-article` |
| 用户讲一个看起来值得记的事，**但没明说** | **不存**。可提示："这条看起来像 X，要 /kb-capture 吗？"（一句话提示，不静默） |

**D1 路由优先级**（用户输入匹配后，第一个命中的路由生效）：

1. **URL 模式**（`^https?://` / `^www\.`）→ `/kb-save-article` 流（含 fetch）
2. **文件路径模式**（`^/[\\w/.-]+\\.[a-z]+$` / `^~/[\\w/.-]+\\.[a-z]+$` / `^\\./[\\w/.-]+\\.[a-z]+$`）→ Read 文件 + `/kb-capture` 流
3. **自然短语**（收录 / 记下 / 别 / 决定…）→ `/kb-capture` 流（启发式判 type）

> v0.3.0 之前（v0.2.x）URL 错误地走 `/kb-capture` 启发式并落 `entries/fact-*.md` 空壳。v0.3.0 起按本节路由优先级执行。

### 什么**不**触发 capture

- 普通回答问题的内容
- 临时上下文（"现在我们在改 X 文件"）
- 转述他人的观点（除非用户说"我同意" + 明确指令）
- 调试输出 / 错误信息 / 临时计算结果
- 助手自己生成的总结

---

## D2 存储布局

### 平台考量（v0.3.4）

kb-workflow 在三种 shell 环境下行为不同——**先 `kb-workflow doctor` 看你的环境**：

| 环境 | `$HOME` | 默认 KB 位置 | 备注 |
|---|---|---|---|
| **macOS / Linux** (bash/zsh) | `/Users/<user>` | `~/.claude/kb/` | 一切正常 |
| **Git Bash on Windows** (MINGW/MSYS) | 自动映射到 `C:\Users\<user>\` | `~/.claude/kb/` → `C:\Users\<user>\.claude\kb\` | **⚠️ OneDrive 同步可能冲突** |
| **Windows-native cmd/PowerShell** | 通常无 `$HOME` | 需显式 `KB_ROOT` env | 不用 Git Bash 的场景 |
| **WSL** (Windows Subsystem for Linux) | Linux path (`/home/<user>`) | `~/.claude/kb/` 在 WSL 侧 | 与 Windows host 的 `C:\Users\<user>\` **完全分离** |

### ⚠️ OneDrive / 云同步陷阱

如果 Windows 用户的 `C:\Users\<user>\Documents\` 被 OneDrive 接管并自动同步到云端：
- **KB 内容可能上传到云**——包含个人偏好、决策、未公开项目信息
- **冲突合并会损坏 KB**——OneDrive 同步多端修改会产生 `_state.md (1).conflict-yyyy-mm-dd` 副本
- **修复方案**：`KB_ROOT=C:/kb-data`（推荐路径：`C:/kb-data` 或 `D:/kb-data`，不在 OneDrive 同步目录下）

### Config root 范式（v0.3.4，XDG-style）

```
KB_HOME   — single config root，所有路径派生自此（除非各自 env override）
KB_ROOT   — KB data dir override
KB_STATE_FILE / KB_CONFIG_FILE / KB_INDEX_FILE — 细粒度 override
KB_WORKFLOW_HOME — skill source dir override

# 例子（OneDrive-aware）：
$ export KB_HOME=C:/kb-data
$ kb-workflow doctor
# 确认所有路径在 C:/kb-data/ 下，不会被 OneDrive 同步
```

优先级：per-path env > KB_HOME > walk-up discovery > $HOME/.claude/kb/


## D2 存储布局

```
~/.claude/kb/
├── _state.md                  # 运行时状态（assistant 维护）
├── config.local.yaml          # 本机 override
├── entries/                   # 结构化条目（4 类）
│   ├── fact-*.md
│   ├── preference-*.md
│   ├── decision-*.md
│   └── tentative-*.md
└── external/                  # 原始资料（外部文章/文档/链接）
    ├── YYYY-MM-DD_<topic>_<slug>.md
    └── _index.md              # 收录清单（自动维护）
```

**MEMORY.md 绝不修改**——harness 管。

---

## D3 4 类 schema（entries/）

| 类型 | 字段 | 模板 |
|---|---|---|
| fact | name, description, type, source, confidence, observed_at, expires_at, scope, content | `config/schema/fact.yaml` |
| preference | name, description, type, scope, anti_examples, source, last_validated, content | `config/schema/preference.yaml` |
| decision | name, description, type, decided_at, supersedes, alternatives_considered, context, content | `config/schema/decision.yaml` |
| tentative | name, description, type, status, opened_at, last_surfaced, scope, source, content | `config/schema/tentative.yaml` |

## D3.5 原始资料 schema（external/）

`external/YYYY-MM-DD_<topic>_<slug>.md`：

```markdown
---
name: 2026-07-25-ragflow-intro
description: <一句话>
metadata:
  type: external_article
  source_url: <URL 或 "user-pasted">
  ingested_at: <YYYY-MM-DD>
  last_seen: <YYYY-MM-DD>             # v0.3.0 新增：D5 dedup bump
  content_sha: <git blob SHA | null>  # v0.3.0 新增：D5 精确判等（如 README SHA）
  topic: <topic>
  key_points:
    - <要点>
  linked_entries: []   # 反向引用
---

# <标题>

## 摘要
<200 字>

## 关键摘录
- ...

## 完整正文
<原文 / 链接>
```

### `_index.md` 自动维护（v0.3.0 强制）

`external/_index.md` 是 external 条目的索引，**assistant 每次写 / 更新 / 删除条目必须同步**：

| 操作 | `_index.md` 动作 |
|---|---|
| 新建条目 | 追加一行：`\| <ingested> \| <topic> \| <slug> \| <source_url> \|` |
| 更新条目（同 slug） | 替换该行（列字段保持，更新 ingested/last_seen 列） |
| 删除 / 废弃条目 | 移除该行 |
| supersede | 旧行加 `superseded_by` 注；新行追加 |

**反模式**：
- ❌ 写完条目忘了 `_index.md`（上次 modelfw-demo 就漏了——本次发现并修复）
- ❌ `_index.md` 行数 ≠ `external/` 文件数（drift），assistant 需在 `kb-status` / 周日 review 时校验

### Minimal Entry Mode（v0.3.3 新增 — D10 evolution from awesome-llm-apps）

> **设计灵感**：awesome-llm-apps 每个 app = `app.py` + `requirements.txt` + `README.md`，最小可运行。kb-workflow 条目可借鉴这个「最小 frontmatter + 自由 body」哲学，**不要过度 schema**。

**两种模式并存**：

| 模式 | frontmatter 字段 | body 深度 | 适用场景 |
|---|---|---|---|
| **full mode**（默认） | 全部必填 + 可选字段（last_seen / content_sha / key_points / linked_entries） | 源码级分析（决策↔代码行映射 + 测试覆盖 + 性能数据） | 大型库 / 框架 / 关键依赖 |
| **minimal mode**（v0.3.3+） | 仅 5 个必填：`name / description / type / source_url / ingested_at` | 简短摘要 + 关键链接 + 自由 body | awesome-list / 小工具 / 一次性参考 |

**什么时候用 minimal mode**：
- ✅ awesome-list 类（如 awesome-llm-apps 这种 100+ 子项目集合）
- ✅ 一次性参考（单文件 demo / 单页文档 / 单 blog post）
- ✅ 内容浅薄到不值得深挖（README 只 1-2 段）
- ❌ 不要用来逃避源码分析——大型 repo 必须 full mode

**minimal mode frontmatter 示例**：

```markdown
---
name: 2026-07-26-foo-bar
description: 单文件参考工具 X
metadata:
  type: external_article
  source_url: https://...
  ingested_at: 2026-07-26
---
# 标题 + 自由 body
```

不需要写：`last_seen` / `content_sha` / `key_points` / `linked_entries`（assistant 可省略）。

### `_state.md` "最近 10 条" 标记语法（v0.3.0 引入）

替代现场发明的标记，固定在 `defaults.yaml: ticket.state_marker`。**标记独占一列**（不与类型 fuse），格式：

```
<date>  <type>  <marker>  <slug>  [可选: 备注]
```

| 标记 | 含义 | 例 |
|---|---|---|
| `+` | 新建 | `2026-07-26  external  +  2026-07-26_ml_x.md` |
| `↻` | 内容更新（bump last_seen + content_sha 变） | `2026-07-26  external  ↻  2026-07-25_ml_modelfw-demo  (sha 875cabce… → abc12345…)` |
| `·` | dedup skip（仅记录，不新增条目） | `2026-07-26  external  ·  2026-07-25_ml_modelfw-demo` |
| `⤴` | supersede 旧条目 | `2026-07-26  external  ⤴  2026-07-26_ml_modelfw-demo  ← 2026-07-25_ml_modelfw-demo` |
| `✗` | 删除 / 废弃 | `2026-07-26  external  ✗  2026-07-25_ml_modelfw-demo` |

**禁止**：v0.3.0 之前的现场发明（`external↻` / `external+` 之类「前缀+符号」fuse 写法）——既不固定也不可机读。新写法用单列空格分隔。

---

## D4 类型自动判定（仅在 `/kb-capture` 触发时跑）

按 `config/heuristics.yaml` 优先级匹配：

| 信号 | 类型 |
|---|---|
| "我们决定 / 选了 / 定为" | decision |
| "记住 / 别 / 以后都 / always / never" | preference |
| "想试试 / 考虑 / 也许 / 先放着" | tentative |
| "发布了 / 上线了"（短上下文） | fact |
| 祈使句 (please do / avoid) | preference |
| 疑问句（是不是该 / 要不要） | tentative |
| 默认 | fact（模糊则升级反问） |

**注意**：URL 信号**不**在此表——URL 已被 D1 路由层截到 `/kb-save-article` 流，不会进入 `/kb-capture` 启发式。`config/heuristics.yaml` 中如有 URL 规则应**移除**（v0.3.0 修复项）。

**不**在每次输入时跑——只在用户显式 `/kb-capture` 后跑。

### 票据输出

每次 `/kb-capture` 成功后，回复末尾打票据（见 `config/ticket-format.md`）：

```
📌 /kb-capture → <type>: <slug>  source=<src>  confidence=<c>
```

`/kb-save-article` 成功后：

```
📥 /kb-save-article → external/<filename>  topic=<topic>
```

---

## D5 dedup / 冲突

### entries/ 路径（fact / preference / decision / tentative）

| 场景 | 触发 | 动作 |
|---|---|---|
| 重复 | 与已有条目语义相似度 ≥ 0.9 | skip + bump `last_seen` |
| 细化 | 是已有条目的限定版（带 when-X 子句） | 追加新条目 + `metadata.refines: <parent_slug>` |
| 冲突 | 矛盾（关键词 + 否定信号） | 两边都保留 + `conflicts_with` 链 + ⚠️ 入 `_state.md` 待裁定 |
| 更新 | 事实修订（如新版本号） | 覆盖内容 + bump `last_validated` + `superseded_by` 链 |

冲突判定用 embedding 距离（默认 bge-small）+ 否定信号词加权。

### external/ 路径（v0.3.0 扩展）

| 场景 | 触发 | 动作 |
|---|---|---|
| **完全重复** | URL + `content_sha` 完全相同 | skip + bump `last_seen`（v0.3.0 新增字段） |
| **上游更新** | URL 同，但 `content_sha` 不同 | 走 UPDATE 路径：更新内容 + bump `last_seen` + `superseded_by` 旧条目链（建议保留旧版作 history） |
| **URL 漂移** | 不同 URL 但内容相同（如镜像 / 重定向） | skip + 在 content 注明 canonical URL |
| **不在 KB** | URL 与现有 external 条目都不匹配 | 写新条目 + **追加到 `external/_index.md`**（v0.3.0 强制） |
| **删除条目** | 用户撤销收录 | 从 `external/_index.md` 同步移除该行 |

### `_state.md` 同步（外部条目也走 dedup 时）

- D5 dedup 命中 → 在 `最近 10 条收录` 加一行标记：
  - 新建：`external+`
  - 更新：`external↻`
  - 删除 / 废弃：`external✗`
  - supersede：`external⤴`（指向新条目）

---

## D6 升级触发（5+1 条红灯）

1. **decision_conflict**：与已敲定决策冲突
2. **future_commitment**：检测到"我打算 / 我们应该 / 计划"
3. **sensitive_data**：密钥 / token / PII（**绝不**入 KB，包括 external/）
4. **ambiguous**：信息模糊无法归档
5. **explicit_user**：用户说"我们定一下" / "这个别忘"
6. **no_capture_intent**（v0.2.0 新增）：用户没显式 /kb-capture，只是随口说 → 助手**不存**，可一句提示

碰到任一 → 立即停下来反问，不静默。

---

## D7 回顾

| 触发 | 行为 |
|---|---|
| 用户说"回顾一下" / `/kb-review` | 立即拉三段清单（待裁定 / tentative / 近期收录） |
| 每周日 18:00 cc-connect cron | 仅摘要（3 行数字），不行动 |
| `⚠️ ≥ 3` 或 `tentative.open ≥ 5` | 主动弹一次"有 N 条等你过目" |

---

## D8 召回

| 内容 | 注入时机 |
|---|---|
| MEMORY.md | harness 自动（assistant 不动） |
| `_state.md` | assistant 每次开场 Read 一次 |
| palace 语义检索 | 检测到 topic signal 时调 `mempalace_search` |
| `external/` 内容 | 助手需主动 Read 文件；不自动全文注入 |
| tentative 条目 | **永不**进正常上下文，仅回顾场景 |

---

## D9 URL Capture Pipeline（v0.3.0 新增）

`收录 <URL>` 命中后，按 URL 模式分发抓取：

| URL 模式 | 识别特征 | 抓取方式 | 落盘位置 |
|---|---|---|---|
| **GitHub 仓库** | `github.com/<owner>/<repo>` | `gh repo view <owner>/<repo> --json ...` + `gh api repos/<owner>/<repo>/readme` 解 base64 | `external/YYYY-MM-DD_<topic>_<slug>.md` |
| **arXiv 论文** | `arxiv.org/abs/<id>` | WebFetch → 拉 abstract + 元数据 | `external/YYYY-MM-DD_<topic>_<slug>.md` |
| **博客 / 文章** | `*.blog.*` / `medium.com` / `dev.to` / `*.substack.com` | WebFetch → 标题 + 正文 | `external/YYYY-MM-DD_<topic>_<slug>.md` |
| **官方文档** | `docs.*` / `*.readthedocs.*` / MDN / Context7 库 ID | WebFetch（必要时调 `mcp__plugin_context7_context7__resolve-library-id` + `query-docs`） | `external/YYYY-MM-DD_<topic>_<slug>.md` |
| **通用参考链接** | 其他域名（无明确文章结构） | **不抓取**，直接落 fact 条目 | `entries/fact-<slug>.md` |

### 抓取失败 fallback

| 失败场景 | 动作 |
|---|---|
| GitHub 私有仓库 + 无权限 | 落 fact 条目，content 标注「私有仓库，待授权后升级」+ `confidence: low` |
| WebFetch 失败 / 404 / 超时 | 落 fact 条目，content 标注 URL + 抓取失败的简短原因 |
| base64 解码失败（README 非 UTF-8） | 落 fact 条目，content 标注 URL + 解码失败原因，附 gh 直链 |
| arxiv 重定向到 PDF | 优先抓 abs 页面；若失败则落 fact 条目 |

### 代码仓库：必须做源码级分析（v0.3.1 强制）

> **README 是 marketing，源码是 ground truth**。`收录 <github URL>` 不能停在 README 转述。

**强制步骤**（按顺序）：

1. **Clone 仓库**：`gh repo clone <owner>/<repo> /tmp/<slug>`（私有仓库需 gh auth）
2. **读关键源文件**（不少于 3 个，覆盖核心实现 / 入口 / 测试 / 性能文档）：
   - 核心实现文件（如 `cmodel.py`, `lib/core.ts`, `src/index.js`）
   - 入口 / glue 文件（如 `cmodel_fast.py`, `bin/cli.js`）
   - 测试文件（如 `test_cmodel.py`, `*.test.ts`）
   - 性能文档（如 `BENCHMARK.md`, `docs/perf.md`）—— 若存在
3. **决策 ↔ 代码行映射**：把 README / 文档声称的设计点逐条对应到具体代码行（行号 + 函数名）。**没映射上的决策要标"未在源码体现"或"README 与源码不一致"**
4. **测试覆盖矩阵**：列出每个决策对应的测试函数名。**没测的覆盖盲区要明说**（不要假装全覆盖）
5. **跨实现一致性**：如有 C++ / Rust / 多语言版本，对照 README 声称的"API 一致"，实际读一遍平替代码验证
6. **性能数据落地**：如有 BENCHMARK / 性能文档，把原始数据 + 关键洞察写入条目（如 FFI 经验、per-op vs batch vs batch+txn 三阶梯）

**禁止的反模式**：
- ❌ 只读 README 就写条目（"光存 URL 偷懒"）
- ❌ 声称"自动决策清晰"但没列具体代码行
- ❌ 测试覆盖写"全"但没逐条对应
- ❌ 性能写"快"但没数字

### 可选：LLM fact extraction + cost estimator（v0.3.5 待做）

> **D10 evolution candidate**（捕获 cognee 时观察）：如果未来 D9 加「可选 LLM fact extraction」步骤（参考 mem0 v3 单 pass extraction），需要同步加 cost estimator（参考 cognee `modules/cognify/estimator.py`）做 token + latency 预估算。

**待落地**：
- `mem0` 风格：`extract(messages) → facts → embed → upsert` 全自动
- `cognee` 风格：`cognify(data) → knowledge graph` + `estimator.cost(task)` 预飞
- v0.3.x 默认**不开** LLM 抽取（保持 active-first + user explicit trigger 哲学），但 schema 留 `enable_llm_extraction: false` 字段

**为什么不现在就加**：
- active-first 原则：v0.2.0 起 KB 默认不主动调 LLM（成本 + 隐私）
- 缺 cost 估算基础设施（先做 estimator 再开 extraction 才合理）
- user 没明确要求（v0.3.0 阶段 KB 主要靠 explicit capture）

### topic 推断（仅 external 路径）

| 命中 | 落 |
|---|---|
| 仓库名 / 文章标题 / README 关键词命中 `_state.md` 主题表（rag / shader / web / ml …） | 用该 topic |
| 仓库名含 `modelfw` / `model` / `transformer` / `nn` 等关键词 | `ml` |
| README / 文档含中文 | `lang-zh` |
| 仓库名含 `docs` / `infra` / `deploy` / `k8s` / `docker` | `infra` |
| 完全无匹配（**v0.3.1 新规：不静默兜底**） | **assistant 反问用户确认**：要落 `infra` 兜底？还是新建 topic？等用户回复后再落盘 |

> 新 topic 仍需用户确认才能加入 `_state.md` 主题表（沿用 v0.2.0 规则）。

### v0.2.x → v0.3.0 行为变化

| 维度 | v0.2.x | v0.3.0 / v0.3.1 |
|---|---|---|
| `收录 <github URL>` | 落 `entries/fact-*.md` 空壳（仅 URL） | clone 仓库 → README + 源码 + 测试 + 性能全部读一遍 → 写 `external/` 完整条目 |
| `收录 <博客 URL>` | 落 `entries/fact-*.md` 空壳 | WebFetch 拉标题 + 正文摘要，写 `external/` |
| `收录 <参考链接>`（无内容可抓） | 落 `entries/fact-*.md` | 仍落 `entries/fact-*.md`（行为不变） |
| topic 无匹配 | 静默落 `infra` | **反问用户**确认（v0.3.1） |

---

## Slash 命令清单

| 命令 | 行为 |
|---|---|
| `/kb-capture <text>` | **主存储入口**。启发式分类 → 写 entries/ → 打票据 |
| `/kb-save-article <url or text>` | **原始资料入口**。D1 路由 + D9 pipeline → 写 external/ + 索引同步 + 镜像 MemPalace |
| `/kb-capture-force <type> <text>` | 跳过启发式，强制指定 type |
| `/kb-recall <query>` | **召回入口**（诉求 2）。跨 entries/ + external/ 检索相关片段。v0.3.4 加 `--format json` 给 Claude 合成用 + `--topic` 过滤 |
| `/kb-forget <slug>` | **v0.3.2 新增：软删除条目**。详见下方 D12。语义对齐 cognee 的 `forget(dataset_id)` |
| `/kb-review` | 触发 D7 回顾 |
| `/kb-status` | 打印当前状态摘要（entries / external / 待裁定 / tentative / index drift 检查） |
| `/kb-evolve` | **skill 自审 + 演进建议**（D10 配套命令）。扫 skill 一致性 + 调用 `scripts/drift_check.py` + 输出 gap 报告。详见下方 D11。 |
| `/kb-workflow update` | 拉新版 workflow |
| `/kb-workflow config` | 编辑 `~/.claude/kb/config.local.yaml` |

> 注：v0.2.1 之前 `/kb-search` 已被 `/kb-recall` 取代。`/kb-search` 仍可作为 alias。

### `/kb-recall` v0.3.4 合成用模式（assistanthandoff）

当 assistant 需要把 KB 内容合成进回答时，**用 `--format json`** 拿结构化结果，而不是解析文本输出：

```bash
/kb-recall "memory agent long-term" --topic llm-memory --format json --limit 5
```

返回结构（每条带 citation，**方便评估 KB 内容是否有错误**）：

```json
{
  "query": "memory agent long-term",
  "topic": "llm-memory",
  "mode": "text",
  "total_hits": 2,
  "hits": [{
    "rank": 1,
    "name": "2026-07-26_rag_mem0",
    "score": 90.0,
    "topic": "llm-memory",
    "source_url": "https://github.com/mem0ai/mem0",    ← 可点击验证
    "file": "/Users/ks_128/.claude/kb/external/...",
    "last_seen": "2026-07-26",                       ← 评估时效性
    "section_anchor": "mem0 — AI Agent 通用记忆层",  ← 知道是哪个段落
    "snippet": "# mem0 — AI Agent 通用记忆层\n\n## 摘要\n..." ← 内容片段
  }]
}
```

assistant 合成 pattern：

1. 读 JSON → 取 `rank 1, 2, 3` 的 `snippet` + `section_anchor` + `source_url`
2. **答案必须 cite 每条**：说"根据 [name § section_anchor]..."
3. 用户问"你怎么知道 X？"→ 直接给 `source_url` 验证
4. 用户怀疑"这个 KB 内容对吗？"→ assistant 用 `file` 路径 `cat` 验证原文

不推荐用文本输出做合成（emoji/分隔符会被吃掉，section 上下文丢失）。

---

## D11 `/kb-evolve` self-audit procedure（v0.3.1 新增）

**目标**：把 D10 Skill Evolution Loop 从"靠用户推动 / assistant 自觉"升级为**自动化检测 + 报告 + 建议更新**。

### 触发

用户说 `/kb-evolve` 或 assistant 在以下场景主动提议：

- 周日 review 时（与 `/kb-review` 串联）
- 完成一次 capture 后（D5 dedup 命中时，触发 skill 自审）
- 跨多文件编辑后

### 执行步骤（assistant 必跑）

1. **读 skill 全套**：`SKILL.md` + `config/{defaults,heuristics,topics}.yaml` + `config/schema/*.yaml` + `CHANGELOG.md`
2. **跑 `scripts/drift_check.py`**（kb-workflow install 时落到 `~/.claude/kb/scripts/`）—— 检查：
   - `external/_index.md` 行数 ↔ `external/*.md` 文件数（含 `_index.md` 自身外的所有 .md）
   - `defaults.yaml entry_types` ↔ `config/schema/*.yaml` 字段定义是否覆盖
   - `SKILL.md` 引用的 D# sections（"见 D5" / "见 D9"）↔ 实际章节是否存在
   - `CHANGELOG.md` 是否有 `[Unreleased]` 段（遗漏更新）
3. **生成 gap 报告**：列出 schema drift / section drift / index drift / changelog drift 四类
4. **assistant 据报告写更新建议**（应用 D10 流程）：标高/中/低优先级，给出 SKILL.md / schema / config 具体改法
5. **等用户批准 → 应用更新 → 打 CHANGELOG 条目**

### 输出格式（gap 报告模板）

```
=== /kb-evolve report (run at <ts>) ===

[CRITICAL] index drift: external/ has 4 files but _index.md has 3 rows (diff: 2026-07-25_ml_modelfw-demo.md missing from index)
[HIGH] schema drift: SKILL.md D5 references `last_seen` for external_article, schema file defines it — OK
[MEDIUM] section drift: SKILL.md mentions "见 D11" but D11 not yet defined
[LOW] changelog drift: [Unreleased] section exists but no Tested entry from current session

recommend (priority order):
1. <action 1>
2. <action 2>
3. <action 3>
```

### Anti-patterns

- ❌ `/kb-evolve` 跑完不输出报告（silent pass）—— 必须显式列 gap
- ❌ 报告里写"看起来都 OK"—— 必须给具体数字（文件数 / 章节数 / 行数）
- ❌ 发现 gap 不写建议—— D10 action 清单至少给出 high 项的改法
- ❌ 跳过 `drift_check.py` 自己手扫—— 该脚本是 ground truth

---

## D12 `/kb-forget` soft-delete procedure（v0.3.2 新增 — D10 evolution）

**触发场景**：捕获 `topoteretes/cognee`（v0.3.2 session）时观察到 cognee 提供 `cognee.forget(dataset_id)` 做主动遗忘。kb-workflow v0.3.1 之前只有物理 `delete`（rm 文件），缺少**软删除 / 时间衰减**语义。按 D10 即时补。

### 行为

```bash
/kb-forget <slug>           # 软删除单条
/kb-forget --hard <slug>    # 硬删除（物理 rm）
/kb-forget --expired        # 清理所有 expires_at < today 的条目（v0.3.5 待做）
```

### 软删除语义（v0.3.2）

| 字段 | 动作 |
|---|---|
| 文件本体 | 重命名为 `<slug>.deleted.<timestamp>`（不立即 rm） |
| frontmatter | 加 `status: forgotten`、`forgotten_at: YYYY-MM-DD` |
| `_index.md` | 行替换，append `status: forgotten` 列 |
| `_state.md` "最近 10 条" | 加 `external  ✗` 标记 |
| `linked_entries` | 标记 `parent_forgotten: true`（被引用条目需在 recall 时跳过） |
| 物理 rm | 默认**不**做；`/kb-forget --hard` 显式触发 |

### 恢复

```bash
/kb-forget --restore <slug>  # 把 .deleted.<timestamp> 改回原名 + 去掉 status
```

### Anti-patterns

- ❌ 把「软删除」当成「删除标记就够」（文件还在 → recall 仍命中）
- ❌ 软删 + 硬删混用没区分（必须 `status: forgotten` 显式）
- ❌ 软删后 _index.md 没同步（drift）

---

---

## v0.2.0 行为契约

- 默认**不**自动存任何东西
- 主动 capture 必须显式触发（slash 或明确短语）
- 助手可**提示**（"要 /kb-capture 吗？"），但**不**静默落盘
- 票据只在显式 capture 后打
- external/ 走专门的 `/kb-save-article` 流程

这是对 v0.1.x 行为的**极性翻转**。现有 entry 不动（按 v0.1.x 模式已落盘的视为历史数据）。

---

## D10 Skill Evolution Loop（v0.3.0 新增 — meta 原则）

**Skills 的核心目的是让行为可复现 + 可演进**。每次 assistant 在 KB workflow 中发现**schema gap / workflow friction / observed counterexample**，应该**当场**迭代 skill，而不是攒到下次大版本。

### 触发场景（任意一条 → 进入 evolution loop）

| 类别 | 信号 | 例子 |
|---|---|---|
| **Schema gap** | 现有字段缺关键信息，找不到落点 | D5 dedup 想 bump 但 external_article 没 `last_seen` 字段 |
| **Workflow friction** | 规则导致需要现场发明 workaround | `external↻` 标记现场编；topic 软分配 |
| **Counterexample** | 真实数据违反当前规则 | README-only capture 被用户否决（"不能只读 README"） |
| **Missing auto-step** | 应该自动但靠人工 | `_index.md` 漏写 → 索引与文件不同步 |
| **Implicit convention** | 规则靠"显而易见"但没文档化 | `_state.md` 最近 10 条的标记语法 |

### 行动清单（任一触发后必做）

1. **记录**：在心里 / 临时 note 里写下「发现 X gap，建议改 Y」
2. **判断优先级**：
   - 高（影响下次 capture 行为）：当场更新 skill
   - 中（影响 KB 一致性）：本会话内更新
   - 低（文档 / 风格）：攒到下次整理
3. **更新 skill**：
   - SKILL.md（行为契约）
   - `config/heuristics.yaml`（自动判定规则）
   - `config/defaults.yaml`（默认配置）
   - `config/schema/*.yaml`（条目 schema）
   - `CHANGELOG.md`（标注演进）
4. **CHANGELOG 标注**：
   - `[Unreleased] Fixed`：bug 修复（declared-but-not-implemented 等）
   - `[Unreleased] Changed`：现有规则改进
   - `[Unreleased] Added`：新能力 / 新字段
   - **不要**把所有改动都写成 Added——会掩盖真正的 bug fix

### 验证（变更后必跑）

- 重新触发一遍相关 capture 流程，确认新行为生效
- 比对变更前后的输出（ticket / 文件 / 索引）
- 把验证结果写进 CHANGELOG 的 `### Tested` 段

### Anti-patterns（**禁止**）

- ❌ 发现 gap 但不更新 skill，下次重复踩
- ❌ 把 workaround 当成"约定俗成"接受（现场发明标记 / 软分配 topic）
- ❌ 只改 SKILL.md 不改 schema/config——上下游不一致
- ❌ 不写 CHANGELOG——演进不可追溯
- ❌ 把"我下次注意"挂在嘴上而不落到文件

---

## v0.3.0 行为契约（在 v0.2.0 基础上追加）

- D1 路由优先级强制执行（URL → save-article，path → Read+capture，text → capture）
- D9 URL Capture Pipeline：代码仓库必做**源码级分析**（不止 fetch README）
- D5 dedup 扩展到 external/：`last_seen` 字段用于 bump，README SHA 用于精确判等
- D10 Skill Evolution Loop：发现 gap 即时迭代 skill，不攒
- 票据格式新增：`external↻` 表示 update，`external+` 表示 supersede，`external✗` 表示废弃
