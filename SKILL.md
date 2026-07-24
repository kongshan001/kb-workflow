---
name: kb-workflow
description: KB 收录与管理工作流。Use when user pastes articles/URLs/preferences/observations, asks to capture, recall, review, or search the personal knowledge base. Also triggers on /kb-capture, /kb-review, /kb-search, /kb-status, /kb-workflow update.
---

# KB WorkFlow — Assistant 行为手册

> 本文件由 `kb-workflow install` 链接到 `~/.claude/skills/kb-workflow/SKILL.md`。
> 启动时自动加载。规范在 `config/defaults.yaml`，按设备 override 在 `~/.claude/kb/config.local.yaml`。

## 启动流程

每个会话开场：
1. **Read** `~/.claude/kb/_state.md`（运行时状态 + 队列 + 统计）
2. 检查 `⚠️ 待裁定` / `🟡 Tentative Open` 数量
3. 启动 banner 打印一次：
   ```
   ✅ KB workflow loaded v{version}
      topics: {N} | entries: {N} | external: {N}
      待裁定: {N} | tentative: {N}
   ```

---

## D1 触发模型

| 用户输入类型 | 行为 |
|---|---|
| 明确指令（"记住 X"、"别建议 Y"、"以后都 Z"） | 静默落盘 |
| URL / 文档 / 长文 / 观察描述 | 启发式分类 + 静默落盘 |
| 模糊 / 多义 / 范围不清 | 反问 |
| 长文批量提取 | 升级：列候选 + 确认后再落盘 |
| 含敏感信息（密钥 / token / PII） | **绝不**自动落盘，立即反问 |

## D2 存储

根目录：`~/.claude/kb/`
```
~/.claude/kb/
├── _state.md                  # 运行时状态（assistant 维护）
├── config.local.yaml          # 本机 override
├── entries/                   # 4 类结构化条目
│   ├── fact-*.md
│   ├── preference-*.md
│   ├── decision-*.md
│   └── tentative-*.md
└── external/                  # 外部文章（源数据 + MemPalace 索引）
    └── YYYY-MM-DD_<topic>_<slug>.md
```

**MEMORY.md 绝不修改**——那是 harness 管。

## D3 条目 schema

| 类型 | 字段 | 模板 |
|---|---|---|
| fact | name, description, type, source, confidence, observed_at, expires_at, scope, content | `config/schema/fact.yaml` |
| preference | name, description, type, scope, anti_examples, source, last_validated, content | `config/schema/preference.yaml` |
| decision | name, description, type, decided_at, supersedes, alternatives_considered, context, content | `config/schema/decision.yaml` |
| tentative | name, description, type, status, opened_at, last_surfaced, scope, source, content | `config/schema/tentative.yaml` |

## D4 类型自动判定

按 `config/heuristics.yaml` 优先级匹配：

| 信号 | 类型 |
|---|---|
| "我们决定 / 选了 / 定为" | decision |
| "记住 / 别 / 以后都 / always / never" | preference |
| "想试试 / 考虑 / 也许 / 先放着" | tentative |
| URL / "发布了 / 上线了" | fact |
| 祈使句 (please do / avoid) | preference |
| 疑问句（是不是该 / 要不要） | tentative |
| 默认 | fact（模糊则升级反问） |

**每次写入在回复末尾打印票据**（见 `config/ticket-format.md`）：

```
📌 记为 <type>: <slug>  source=<src>  confidence=<c>
```

## D5 去重 / 冲突

| 场景 | 判定 | 动作 |
|---|---|---|
| 重复 | 与已有条目语义相似度 ≥ 0.9 | skip + bump `last_seen` |
| 细化 | 是已有条目的限定版（带 when-X 子句） | 追加新条目 + `metadata.refines: <parent_slug>` |
| 冲突 | 矛盾（关键词 + 否定信号） | 两边都保留 + `conflicts_with` 链 + ⚠️ 入 `_state.md` 待裁定 |
| 更新 | 事实修订（如新版本号） | 覆盖内容 + bump `last_validated` + `superseded_by` 链 |

冲突判定用 embedding 距离（默认 bge-small）+ 否定信号词加权。

## D6 升级触发（5 条红灯）

1. **decision_conflict**：与已敲定决策冲突
2. **future_commitment**：检测到"我打算 / 我们应该 / 计划"
3. **sensitive_data**：密钥 / token / PII
4. **ambiguous**：信息模糊无法归档
5. **explicit_user**：用户说"我们定一下" / "这个别忘"

碰到任一 → 立即停下来反问，不静默。

## D7 回顾

| 触发 | 行为 |
|---|---|
| 用户说"回顾一下" / `/kb-review` | 立即拉三段清单（待裁定 / tentative / 近期收录） |
| 每周日 18:00 cc-connect cron | 仅摘要（3 行数字），不行动 |
| `⚠️ ≥ 3` 或 `tentative.open ≥ 5` | 主动弹一次"有 N 条等你过目" |

回顾时清单模板：
```
⚠️ 待裁定 (N):
  - [date] <slug-A> ↔ <slug-B>
  → "以哪条为准？"

🟡 Tentative Open (N):
  - [opened date] <slug> "<原话>"
  → 继续观望 / 启动调研 / 放弃？

📥 最近 10 条收录:
  - YYYY-MM-DD  <type>  <slug>
```

## D8 召回

| 内容 | 注入时机 |
|---|---|
| MEMORY.md | harness 自动（assistant 不动） |
| `_state.md` | assistant 每次开场 Read 一次 |
| palace 语义检索 | 检测到 topic signal 时调 `mempalace_search` |
| tentative 条目 | **永不**进正常上下文，仅回顾场景 |

---

## Slash 命令清单

| 命令 | 行为 |
|---|---|
| `/kb-capture` | 显式标记"这条开始收录"（默认已静默，兜底用） |
| `/kb-review` | 触发 D7 回顾 |
| `/kb-search X` | 跨 KB + palace 检索 X |
| `/kb-status` | 打印当前状态摘要 |
| `/kb-workflow update` | 拉新版 workflow（git pull） |
| `/kb-workflow config` | 编辑 `~/.claude/kb/config.local.yaml` |

---

## 票据输出（必填）

每次静默写入后，回复末尾**必须**包含票据。详见 `config/ticket-format.md`。
