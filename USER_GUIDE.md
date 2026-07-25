# kb-workflow 用户手册

> 5 分钟上手，日常用说话就行。

## 1. 装上

```bash
curl -fsSL https://raw.githubusercontent.com/kongshan001/kb-workflow/main/install.sh | bash
```

装完会建好：
- `~/.claude/kb/` — KB 根目录
- `~/.local/bin/kb-workflow` — CLI 命令
- `~/.claude/skills/kb-workflow/` — Claude Code 自动加载

**验证**：

```bash
export PATH="$HOME/.local/bin:$PATH"
kb-workflow status
```

应该看到 `✅ git / bash / claude-code` 三项 + KB 状态（刚开始是空的）。

---

## 2. 第一条 entry

打开新会话，对 Claude 说：

> "BGE-M3 支持 100+ 语言，对中英混排效果好。"

助手会自动：
1. 判定类型 → `fact`（观察性陈述）
2. 写到 `~/.claude/kb/entries/fact-bge-m3-multilingual.md`
3. 更新 `~/.claude/kb/_state.md`
4. 在回复末尾打票据：

```
📌 记为 fact: fact-bge-m3-multilingual
   source=user-stated  confidence=medium  scope=ml/embedding
```

**完事**。这就是整个工作流的核心——你只管说话，助手处理归档。

---

## 3. 日常用法

### 静默收录（默认行为）

直接说话或粘贴，助手按内容自动分类：

| 你输入 | 助手归为 | 票据前缀 |
|---|---|---|
| "记住 X" / "以后都 Y" | preference | 📌 记为 preference |
| "我决定用 Z" / "敲定用 Z" | decision | 📌 记为 decision |
| "Python 3.13 发布了" / 贴 URL | fact | 📌 记为 fact |
| "我以后想试试 X" / "也许该用 Y" | tentative | 📌 记为 tentative |
| "我打算下个月..." | ⚠️ 升级反问 | 不静默 |

### 批量输入

一次贴多段，助手按句切分，**每条独立归类**：

```
我看了下 Three.js 的 MeshBasicMaterial 不支持自定义 shader uniforms。
决定 demo1 项目的 shader demo 全部用 ShaderMaterial 重写。
另外我以前提过想试试 SDF 文字渲染——这个先放着。
```

→ 一次产出 3 条票据（1 fact + 1 decision + 1 tentative）。

### 显式打标

不放心自动分类？加前缀：

```
/kb-capture BGE-M3 是个不错的嵌入模型
```

等同于"这条**确定**开始收录，按自动规则归类"。

### 主动回顾

```
/kb-review
```

或说 "回顾一下" / "看看都记了啥"。

输出三段清单：
- ⚠️ **待裁定**：所有冲突条目，等你决定保留哪条
- 🟡 **Tentative Open**：所有候选项，问你继续观望 / 升级 / 放弃
- 📥 **最近 10 条收录**：让你快速看 assistant 最近做了什么

### 搜索

```
/kb-search shader
```

或说 "查一下 shader 相关的" / "KB 里有没有 RAG 相关的"。

跨 `entries/` + `external/` + MemPalace（如果装了）一起搜。

### 看状态

```
/kb-status
```

或说 "KB 现在啥情况"。

打印当前 entry 数量 + 类型分布 + ⚠️ / 🟡 队列 + 能力检测结果。

---

## 4. 4 类条目长啥样

每条都是 `~/.claude/kb/entries/<type>-<slug>.md` 一个 .md 文件，frontmatter 标类型 + 字段。

### fact（事实/观察）

```markdown
---
name: fact-bge-m3-multilingual
description: BGE-M3 模型对中英混排效果好
metadata:
  type: fact
  source: user-stated
  confidence: high | medium | low
  observed_at: 2026-07-24
  expires_at: null
  scope: ml/embedding
---

BGE-M3 官方文档称支持 100+ 语言。

**Why:** 评估多语种嵌入模型时的备选答案。
**How to apply:** 当中英混排需要嵌入时优先 BGE-M3。
```

### preference（偏好/规则）

```markdown
---
name: pref-shader-perf-use-spector
description: 调 shader 性能问题先用 Spector.js
metadata:
  type: preference
  scope: when-debugging-shader-perf
  anti_examples: null
  source: user-stated
  last_validated: 2026-07-24
---

调 shader 性能问题时先用 Spector.js 录制帧。

**Why:** console.log 打 GPU 调用信息不全，Spector.js 能录所有 draw call。
**How to apply:** shader 卡顿时第一动作 = 装 Spector.js 录制。
**Anti-examples:** 简单语法错误不需要 Spector.js。
```

### decision（决策/已敲定）

```markdown
---
name: decision-demo1-shader-use-shadermaterial
description: demo1 shader demo 统一用 ShaderMaterial
metadata:
  type: decision
  decided_at: 2026-07-24
  supersedes: null
  alternatives_considered:
    - MeshBasicMaterial + onBeforeCompile
    - 引入 Cocos2d 渲染管线
  context: demo1 web-uieffect shader demo 需要统一渲染入口
---

demo1 项目的 shader demo 全部用 ShaderMaterial。

**Why:** 内置材质不支持完整自定义 uniforms；Cocos 过重。
**How to apply:** 新增 shader 效果直接 ShaderMaterial。
```

### tentative（候选项）

```markdown
---
name: tentative-try-sdf-text-rendering
description: 想试试用 SDF 做文字渲染
metadata:
  type: tentative
  status: open
  opened_at: 2026-07-24
  last_surfaced: null
  scope: global
  source: user-stated
---

考虑用 SDF 做文字渲染。

**Why:** 听说 SDF 缩放无锯齿、shader 友好。
**How to apply:** 暂不行动；下次回顾时确认。
```

---

## 5. 票据（assistant 每次写入都会打）

```
📌 记为 <type>: <slug>  source=<src>  confidence=<c>
```

冲突时：
```
⚠️  CONFLICT with <other_slug>: <reason>
```

细化已有条目时：
```
🔗 REFINES <parent_slug>: <delta>
```

更新已有条目时：
```
✏️  UPDATES <old_slug>: <change>
```

**怎么看 assistant 刚才做了什么**：搜回复末尾的 `📌` / `⚠️` / `🔗` / `✏️`，一眼就懂。

---

## 6. 5 条升级红灯（碰到就停下来反问）

| # | 触发 | 助手做什么 |
|---|---|---|
| 1 | 与已敲定的 decision 冲突 | 保留两边，⚠️ 入待裁定，**不**自动覆盖 |
| 2 | 含"我打算 / 计划 / 应该" | 反问"落为 decision 还是保持 tentative？" |
| 3 | 含密钥 / token / 内部凭证 | 硬拦截，**绝不**落盘，建议撤销 |
| 4 | 主语/scope 模糊 | 反问"这条想说啥？" |
| 5 | 你说"我们定一下" / "这个别忘" | 反问确认 |

典型拦截示例：

> 你: "我的 GitHub token 是 ghp_abc123..."
> 助手: 🛑 检测到敏感信息——不会写入。建议立刻去 GitHub 撤销。

---

## 7. 跨设备

### 新设备第一次

```bash
curl -fsSL https://raw.githubusercontent.com/kongshan001/kb-workflow/main/install.sh | bash
```

就这么一行。

### KB 数据要不要同步？

**默认不同步**——assistant 行为（workflow 本身）是跨设备一致的；你的 KB 数据（entries / external）是本机的。

如果你想跨设备同步 KB 数据：
- 简单：把 `~/.claude/kb/` 整个丢到 iCloud / Dropbox
- 版本化：在 `~/.claude/kb/` 跑 `git init` + push 到私有仓

### 工作流本身怎么更新

```bash
kb-workflow update
```

patch/minor 自动拉；major 会问你。

---

## 8. 配置（按需定制）

`~/.claude/kb/config.local.yaml` 改本机偏好，git-ignored 不会被 workflow 更新覆盖。

```yaml
# 加新主题到白名单
topics:
  add: [agent, eval]

# 关闭某个主题
topics:
  remove: [desktop]

# 改 KB 根目录（高级）
kb_root: ~/Documents/kb

# 改嵌入模型（如果将来加自动 dedup）
embedding:
  model: bge-large
```

---

## 9. 故障排查

### 装上但 `kb-workflow` 找不到

```bash
export PATH="$HOME/.local/bin:$PATH"
```

永久修复：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### assistant 不打票据

检查 skill 软链：

```bash
ls -la ~/.claude/skills/kb-workflow/
```

应该看到 3 个软链：`SKILL.md` / `config` / `CHANGELOG.md`。如果有缺失，重跑 `install.sh`。

### 助手分类错了

直接说"这条应该是 X 不是 Y"——assistant 会修正 + 更新 frontmatter。

或者手动改 `~/.claude/kb/entries/<file>.md` 的 `type:` 字段，下次 `kb-workflow status` 会反映。

### 冲突条目处理

`/kb-review` 里看 `⚠️ 待裁定` 段，每条给你 A/B/C 选项。

### 完全重置

```bash
kb-workflow uninstall --purge
curl -fsSL https://raw.githubusercontent.com/kongshan001/kb-workflow/main/install.sh | bash
```

⚠️  `--purge` 会删 `~/.claude/kb/` 全部数据，**先备份**。

---

## 10. 常用命令速查

| 做什么 | 怎么说 / 敲什么 |
|---|---|
| 收录一条 | 直接说 / 粘贴 |
| 强制收录 | `/kb-capture ...` |
| 回顾 | `/kb-review` 或 "回顾一下" |
| 搜索 | `/kb-search X` 或 "查一下 X" |
| 看状态 | `/kb-status` 或 "KB 现在啥情况" |
| 改配置 | `kb-workflow config` 或直接编辑 `~/.claude/kb/config.local.yaml` |
| 更新 workflow | `kb-workflow update` |
| 卸载 | `kb-workflow uninstall` |

---

## 11. 推荐工作节奏

| 节奏 | 做什么 |
|---|---|
| **日常** | 想到啥就说啥，助手自动归类 |
| **周末** | `/kb-review` 处理 ⚠️ 和 🟡 队列 |
| **新设备** | 一行 `curl` 装上 |
| **每季度** | 翻一下 `entries/`，删过时 fact / 升级重要 tentative |
| **每年** | `kb-workflow update`，看 major 升级有没有破坏性变更 |

---

## 12. 进阶：直接编辑 .md

所有条目都是纯 .md + YAML frontmatter，可以直接用任何编辑器改：

```bash
# 用 vim 改一条
vim ~/.claude/kb/entries/decision-demo1-shader-use-shadermaterial.md

# 批量看所有 decision
ls ~/.claude/kb/entries/decision-*.md
```

改完不用跑任何命令——下次 `kb-workflow status` 自动反映。

---

## 13. 设计文档（如果你好奇"为什么"）

- `specs/kb-workflow/plan.md` — 14 个核心决策的来龙去脉
- `~/kb-workflow-dev/` 里的 `SKILL.md` — assistant 实际执行规则

但日常用**完全不需要读这些**——本手册就够了。

---

## 14. 反馈 / 问题

- GitHub Issues: https://github.com/kongshan001/kb-workflow/issues
- 直接对 Claude 说"我想要 X 行为"——如果合理，下次更新就会带上

---

**核心一句话**：把"记住这个"变成一个**你不用记、助手自动处理、永远可查**的系统。
