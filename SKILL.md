---
name: kb-workflow
description: KB 收录与管理工作流（active-first）。Use when user invokes /kb-capture, /kb-save-article, /kb-review, /kb-search, /kb-status, /kb-workflow update — or says "记住 X / 别 X / 以后 X / 保存这篇文章". Default behavior: do NOT auto-store anything.
---

# KB WorkFlow v0.2.0 — Assistant 行为手册

> 本文件由 `kb-workflow install` 链接到 `~/.claude/skills/kb-workflow/SKILL.md`。
> 启动时自动加载。规范在 `config/defaults.yaml`，按设备 override 在 `~/.claude/kb/config.local.yaml`。

## 核心原则：Active-first

**默认 = 不存任何东西。** 用户必须显式触发 capture，助手才落盘。

> 这是 v0.2.0 的极性翻转。v0.1.x 默认静默收录；v0.2.0 起反过来。

---

## 启动流程

每个会话开场：
1. **Read** `~/.claude/kb/_state.md`（运行时状态 + 队列 + 统计）
2. 检查 `⚠️ 待裁定` / `🟡 Tentative Open` 数量
3. 启动 banner 打印一次：
   ```
   ✅ KB workflow v0.2.0 loaded
      mode: active-first (no auto-store)
      entries: {N} | external: {N} | 待裁定: {N} | tentative: {N}
   ```

---

## D1 触发模型：active-first

| 用户输入 | 助手行为 |
|---|---|
| **普通说话 / 提问 / 闲聊** | **不存**。按需要正常回答。 |
| `/kb-capture <content>` | 存。启发式分类，4 类 schema，写入 entries/。 |
| `/kb-save-article <url or text>` | 存。原始资料流：写 external/ + 镜像 MemPalace。 |
| `收录 <url or path or text>` | 触发 capture（自动判 type） |
| `收一下` / `记下` / `记住` / `记一下` / `保存` / `存这个` | 等同 `/kb-capture` |
| `以后 X` / `别 X` / `永远 Y` | 等同 `/kb-capture X`（preference 信号） |
| `我决定 X` / `我们敲定 Y` | 等同 `/kb-capture X`（decision 信号） |
| `保存这篇文章 <url>` / `记下这个文档` | 等同 `/kb-save-article` |
| `收录 <文件路径>`（如 `~/docs/notes.md`） | 助手 Read 文件 → 走 `/kb-capture` 流程 |
| 用户讲一个看起来值得记的事，**但没明说** | **不存**。可提示："这条看起来像 X，要 /kb-capture 吗？"（一句话提示，不静默） |

### 什么**不**触发 capture

- 普通回答问题的内容
- 临时上下文（"现在我们在改 X 文件"）
- 转述他人的观点（除非用户说"我同意" + 明确指令）
- 调试输出 / 错误信息 / 临时计算结果
- 助手自己生成的总结

---

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

---

## D4 类型自动判定（仅在 `/kb-capture` 触发时跑）

按 `config/heuristics.yaml` 优先级匹配：

| 信号 | 类型 |
|---|---|
| "我们决定 / 选了 / 定为" | decision |
| "记住 / 别 / 以后都 / always / never" | preference |
| "想试试 / 考虑 / 也许 / 先放着" | tentative |
| URL / "发布了 / 上线了"（短上下文） | fact |
| 祈使句 (please do / avoid) | preference |
| 疑问句（是不是该 / 要不要） | tentative |
| 默认 | fact（模糊则升级反问） |

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

| 场景 | 触发 | 动作 |
|---|---|---|
| 重复 | 与已有条目语义相似度 ≥ 0.9 | skip + bump `last_seen` |
| 细化 | 是已有条目的限定版（带 when-X 子句） | 追加新条目 + `metadata.refines: <parent_slug>` |
| 冲突 | 矛盾（关键词 + 否定信号） | 两边都保留 + `conflicts_with` 链 + ⚠️ 入 `_state.md` 待裁定 |
| 更新 | 事实修订（如新版本号） | 覆盖内容 + bump `last_validated` + `superseded_by` 链 |

冲突判定用 embedding 距离（默认 bge-small）+ 否定信号词加权。

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

## Slash 命令清单

| 命令 | 行为 |
|---|---|
| `/kb-capture <text>` | **主存储入口**。启发式分类 → 写 entries/ → 打票据 |
| `/kb-save-article <url or text>` | **原始资料入口**。写 external/ + 镜像 MemPalace |
| `/kb-capture-force <type> <text>` | 跳过启发式，强制指定 type |
| `/kb-recall <query>` | **召回入口**（诉求 2）。跨 entries/ + external/ 检索相关片段 |
| `/kb-review` | 触发 D7 回顾 |
| `/kb-status` | 打印当前状态摘要 |
| `/kb-workflow update` | 拉新版 workflow |
| `/kb-workflow config` | 编辑 `~/.claude/kb/config.local.yaml` |

> 注：v0.2.1 之前 `/kb-search` 已被 `/kb-recall` 取代。`/kb-search` 仍可作为 alias。

---

## v0.2.0 行为契约

- 默认**不**自动存任何东西
- 主动 capture 必须显式触发（slash 或明确短语）
- 助手可**提示**（"要 /kb-capture 吗？"），但**不**静默落盘
- 票据只在显式 capture 后打
- external/ 走专门的 `/kb-save-article` 流程

这是对 v0.1.x 行为的**极性翻转**。现有 entry 不动（按 v0.1.x 模式已落盘的视为历史数据）。
