# kb-workflow 用户手册

> v0.2.0 起改为 **active-first**——默认不存任何东西，slash 命令是主路径。

## 1. 装上

```bash
curl -fsSL https://raw.githubusercontent.com/kongshan001/kb-workflow/main/install.sh | bash
```

装完会建好：
- `~/.claude/kb/` — KB 根目录
- `~/.local/bin/kb-workflow` — CLI 命令
- `~/.claude/skills/kb-workflow/` — Claude Code 自动加载的 Skill

**验证**：

```bash
export PATH="$HOME/.local/bin:$PATH"
kb-workflow status
```

---

## 2. v0.2.0 最重要的变化：默认 = 不存

> **不**像印象笔记 / Notion / Apple Notes 那样被动收集。
> 你必须**显式触发**，助手才落盘。

| 你只是聊天 | → 不存，正常回答 |
|---|---|
| 你**主动** capture | → 存 |

这避免"随口一句也被永久记录"的失控感。

---

## 3. 主存储入口：`/kb-capture`

**用法**：

```
/kb-capture 记住：BGE-M3 支持 100+ 语言
```

或：

```
/kb-capture 我决定 demo1 的 shader demo 全部用 ShaderMaterial
```

或：

```
/kb-capture 想试试 SDF 文字渲染
```

助手会自动：
1. 启发式分类（fact / preference / decision / tentative）
2. 写到 `~/.claude/kb/entries/`
3. 更新 `_state.md`
4. 在回复末尾打票据：

```
📌 /kb-capture → fact: fact-bge-m3-multilingual
   source=user-stated  confidence=medium  scope=ml/embedding
```

### 强制指定类型

不确定自动分类对不对？强制指定：

```
/kb-capture-force preference 调 shader 性能用 Spector.js
```

### 自然语言等价

不想每次打 `/kb-capture`？这些短语同样触发：

| 你说 | 等同于 |
|---|---|
| "记住 X" | `/kb-capture X` |
| "记一下 X" | `/kb-capture X` |
| "以后 X" / "以后都 X" | `/kb-capture X`（preference） |
| "别 X" / "不要 X" | `/kb-capture X`（preference） |
| "我决定 X" / "我们敲定 X" | `/kb-capture X`（decision） |

---

## 4. 原始资料入口：`/kb-save-article`

存**整篇文章 / URL 指向的文档 / 长资料**。与 `/kb-capture` 的区别：

| | `/kb-capture` | `/kb-save-article` |
|---|---|---|
| 适合 | 短事实 / 偏好 / 决策 | 长文章 / 文档 / 链接 |
| 路径 | `entries/` | `external/` |
| 镜像 | 不需要 | 镜像到 MemPalace（语义检索） |
| 票据 | 📌 /kb-capture → | 📥 /kb-save-article → |

**用法**：

```
/kb-save-article https://github.com/infiniflow/RAGFlow
```

或粘贴全文：

```
/kb-save-article [粘贴文章内容]
```

助手会：
1. 提取标题、摘要、关键点
2. 写到 `external/YYYY-MM-DD_<topic>_<slug>.md`
3. 追加到 `external/_index.md`
4. 镜像到 MemPalace 对应 topic room
5. 打票据：

```
📥 /kb-save-article → external/2026-07-25-ragflow-intro.md
   source_url=https://github.com/infiniflow/RAGFlow
   topic=rag
```

### 主题（topic）

`topic` 决定归档位置和 MemPalace room。默认白名单 10 个（rag / shader / ocr / web / infra / ml / lang-zh / lang-en / mobile / desktop）。

需要新主题？直接说"加 topic：xxx"，或编辑 `~/.claude/kb/config.local.yaml`。

---

## 5. 其他 slash 命令

| 命令 | 做什么 |
|---|---|
| `/kb-review` | 触发 D7 回顾：⚠️ 待裁定 + 🟡 Tentative + 最近收录 |
| `/kb-search X` | 跨 entries/ + external/ + MemPalace 检索 |
| `/kb-status` | 看当前状态（统计、队列、能力） |
| `/kb-workflow update` | 拉新版 workflow |
| `/kb-workflow config` | 编辑 `config.local.yaml` |

**自然语言等价**：
- "回顾一下" / "看看都记了啥" → `/kb-review`
- "查一下 X" / "KB 里有没有 X" → `/kb-search X`
- "KB 现在啥情况" → `/kb-status`

---

## 6. 助手主动提示（v0.2.0 新行为）

看到值得记的内容但你**没明说** capture，助手会**提示一次**（不静默）：

```
你: "BGE-M3 这模型看着不错，文档说支持 100+ 语言。"

助手: "💡 这条看起来像 fact：BGE-M3 支持 100+ 语言。
       要 /kb-capture 吗？"
```

你回 "好" / "不用" / 不回都行。**不回 = 不存**。

---

## 7. 5 条升级红灯（碰到就反问）

| # | 触发 | 助手做什么 |
|---|---|---|
| 1 | 与已敲定 decision 冲突 | 保留两边，⚠️ 入待裁定，不自动覆盖 |
| 2 | 含"我打算 / 计划" | 反问"落为 decision 还是保持 tentative？" |
| 3 | 含密钥 / token / PII | 硬拦截，建议撤销 token |
| 4 | 主语/scope 模糊 | 反问"这条想说啥？" |
| 5 | 你说"我们定一下" / "这个别忘" | 反问确认 |
| 6 | 你随口说但**没** /kb-capture | **不存**，可一句提示 |

典型示例：

> 你: "我的 GitHub token 是 ghp_abc123..."
> 助手: 🛑 检测到敏感信息——**不会写入**。建议立刻去 GitHub 撤销。

---

## 8. 4 类条目 + external 长啥样

### fact（事实/观察）

`~/.claude/kb/entries/fact-bge-m3-multilingual.md`：

```markdown
---
name: fact-bge-m3-multilingual
description: BGE-M3 对中英混排效果好
metadata:
  type: fact
  source: user-stated
  confidence: high
  observed_at: 2026-07-25
  expires_at: null
  scope: ml/embedding
---

BGE-M3 官方文档称支持 100+ 语言。

**Why:** 评估多语种嵌入模型时的备选答案。
**How to apply:** 中英混排时优先 BGE-M3。
```

### preference / decision / tentative

字段见 `config/schema/*.yaml`（schema 模板文件）。

### external article

`~/.claude/kb/external/2026-07-25-rag_ragflow-intro.md`：

```markdown
---
name: 2026-07-25-rag-ragflow-intro
description: RAGFlow 入门指南
metadata:
  type: external_article
  source_url: https://github.com/infiniflow/RAGFlow
  ingested_at: 2026-07-25
  topic: rag
  key_points:
    - 支持 GraphRAG
    - 内置 OCR
  linked_entries: []

---

# RAGFlow 入门

## 摘要
开源 RAG 引擎，深度文档理解...

## 关键摘录
- ...

## 完整正文
<原文 / 链接>
```

---

## 9. 票据（capture 后必看）

```
📌 /kb-capture → <type>: <slug>  source=<src>  confidence=<c>   # 结构化条目
📥 /kb-save-article → external/<filename>  topic=<topic>           # 原始资料
⚠️  CONFLICT with <other_slug>: <reason>                            # 冲突
🔗 REFINES <parent_slug>: <delta>                                   # 细化
✏️  UPDATES <old_slug>: <change>                                    # 更新
💡 这条看起来像 <type>：<摘要>。要 /kb-capture 吗？                  # 助手提示
```

---

## 10. 跨设备

### 新设备第一次

```bash
curl -fsSL https://raw.githubusercontent.com/kongshan001/kb-workflow/main/install.sh | bash
```

一行搞定。

### KB 数据要不要同步

**默认不同步**——workflow 本身跨设备一致；你的 KB 数据（entries + external）是本机的。

跨设备同步可选：
- 简单：把 `~/.claude/kb/` 整个丢到 iCloud / Dropbox
- 版本化：跑 `git init` + push 到私有仓

### Workflow 怎么更新

```bash
kb-workflow update
```

patch/minor 自动；major 询问。

---

## 11. 配置（按需定制）

`~/.claude/kb/config.local.yaml` 改本机偏好，git-ignored。

```yaml
# 加主题到白名单
topics:
  add: [agent, eval]

# 关闭主题
topics:
  remove: [desktop]

# 改 KB 根（高级）
kb_root: ~/Documents/kb
```

---

## 12. 故障排查

### `kb-workflow` 找不到

```bash
export PATH="$HOME/.local/bin:$PATH"
# 永久：echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

### assistant 不打票据

v0.2.0 默认**不**打票据——只在 `/kb-capture` 或 `/kb-save-article` 后打。

如果你预期它打却没打，检查是否真的触发了 capture。

### 助手存了你没让它存

不应该发生——v0.2.0 默认不存。如果你看到静默写入，说明触发到了自然语言短语（"记住 X" / "别 X" / "以后 X"）。明确说"这条**不**存"会让它跳过。

### 助手漏了你让它存

确认用了 `/kb-capture` 或自然语言触发短语之一。否则它只在出现"看起来值得记"时**提示**一次。

### 改分类错了

直接说"这条应该是 X 不是 Y"——助手会改 frontmatter `type:` 字段。或手动 `vim ~/.claude/kb/entries/<file>.md` 改 `metadata.type`。

### 完全重置

```bash
kb-workflow uninstall --purge
curl -fsSL https://raw.githubusercontent.com/kongshan001/kb-workflow/main/install.sh | bash
```

⚠️  `--purge` 会删 `~/.claude/kb/` 全部数据。

---

## 13. 速查表

| 做什么 | 怎么说 / 敲什么 |
|---|---|
| 存一条 | `/kb-capture ...` 或 "记住 X" |
| 强制类型 | `/kb-capture-force <type> ...` |
| 存文章 | `/kb-save-article <url or text>` |
| 回顾 | `/kb-review` 或 "回顾一下" |
| 搜索 | `/kb-search X` 或 "查一下 X" |
| 状态 | `/kb-status` 或 "KB 现在啥情况" |
| 更新 | `kb-workflow update` |
| 卸载 | `kb-workflow uninstall` |

---

## 14. 推荐工作节奏

| 节奏 | 做什么 |
|---|---|
| **日常** | 有值得记的就 `/kb-capture` 一条；遇到好文章就 `/kb-save-article` |
| **周末** | `/kb-review` 处理 ⚠️ 和 🟡 队列 |
| **新设备** | 一行 `curl` 装上 |
| **每季度** | 翻 `entries/` 删过时 fact，升级重要 tentative |
| **每年** | `kb-workflow update`，看 major 升级有没有破坏性变更 |

---

## 15. 反馈

- GitHub Issues: https://github.com/kongshan001/kb-workflow/issues
- 直接对 Claude 说"我想要 X 行为"——合理的话下次更新带上

---

**核心一句话**：把"记住这个"从"我控制不了 assistant 记了啥"变成"我**主动**用 skill 记，且**只**记我让它记的"。
