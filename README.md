# kb-workflow

> 持续收录外部资料 + 反向抽取为结构化条目的工作流。跨设备一键装。

把"记住这个"、"别建议 X"、"以后都 Y"这种自然语言自动变成结构化条目，每条来源可追、分类可见。

## 特性

- **静默收录 + 可审计**——每条条目打票据（`📌 记为 <type>: <slug>`），你随时能看 assistant 把什么归到哪一类
- **4 类 schema**——`fact` / `preference` / `decision` / `tentative`，每类字段不一样
- **混合存储**——`external/` 存源数据，MemPalace 做语义索引；palace 挂了自动降级为 grep
- **软降级**——缺工具不全罢工，启动 banner 透明化告诉你哪些能力可用
- **一键 CLI**——`install` / `update` / `status` / `uninstall` 4 个命令搞定
- **跨设备**——新机器一行命令拉起来，workflow 行为一致

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/kongshan001/kb-workflow/main/install.sh | bash
```

或本地开发模式：

```bash
git clone <repo> ~/kb-workflow
~/kb-workflow/install.sh
```

安装完会建好：
```
~/.claude/kb/                       # KB 根目录
~/.local/bin/kb-workflow            # CLI 命令
~/.claude/skills/kb-workflow/       # Claude Code Skill 软链
```

## 命令

| 命令 | 做什么 |
|---|---|
| `kb-workflow install` | 一键装（首次或新设备） |
| `kb-workflow update` | 拉新版 workflow（patch/minor 静默，major 询问） |
| `kb-workflow status` | 看当前状态：版本、能力、队列、统计 |
| `kb-workflow uninstall` | 干净卸载（KB 数据保留，除非 `--purge`） |

## 4 类条目

| 类型 | 用途 | 示例 |
|---|---|---|
| `fact` | 关于外部世界的观察 | "BGE-M3 支持 100+ 语言" |
| `preference` | 你希望 assistant 怎么做 | "调 shader 性能先用 Spector.js 录制" |
| `decision` | 已敲定的选择 | "demo1 项目的 shader demo 全部用 ShaderMaterial" |
| `tentative` | 候选项（独立池） | "也许该用 SDF 做文字渲染" |

## 演示

### 静默收录 + 票据

输入：
> "BGE-M3 模型对中英混排效果好。另外以后调 shader 性能问题先用 Spector.js 录制帧。"

输出（assistant 回复末尾）：
```
📌 记为 fact:       fact-bge-m3-multilingual
   source=user-stated  confidence=medium  scope=ml/embedding

📌 记为 preference:  pref-shader-perf-use-spector
   source=user-stated  scope=when-debugging-shader-perf
```

`~/.claude/kb/entries/` 下立即多了 2 个 `.md` 文件，`_state.md` 自动同步统计。

### Status

```bash
$ kb-workflow status
📊 KB workflow status
  workflow: /Users/ks_128/kb-workflow (v0.1.1)
  kb_root:  /Users/ks_128/.claude/kb

  Stats
    entries/:    5  (fact=2 preference=1 decision=1 tentative=1)
    external/:   0
    待裁定:     0
    tentative:   1 (open)

🔧 Capabilities
    git                  ✅ git version 2.37.1
    bash                 ✅ 3.2.57
    claude-code          ✅ Claude Code environment detected
    mempalace            ✅ MCP server registered
    cc-connect           ✅ cc-connect v1.3.2
    python3              ✅ Python 3.13.2
    network              ✅ reachable
    kb_root              ✅ /Users/ks_128/.claude/kb ( 32K)
```

## 仓库结构

```
kb-workflow/
├── SKILL.md                  # 助手启动加载的执行手册
├── install.sh / uninstall.sh
├── bin/kb-workflow           # CLI 主入口
├── config/
│   ├── defaults.yaml         # canonical 默认（git tracked）
│   ├── schema/               # 4 类 schema 模板
│   │   ├── fact.yaml
│   │   ├── preference.yaml
│   │   ├── decision.yaml
│   │   └── tentative.yaml
│   ├── heuristics.yaml       # 启发式分类规则
│   ├── topics.yaml           # 主题白名单（10 个起步）
│   └── ticket-format.md
├── scripts/
│   ├── capability-detect.sh  # host 能力检测
│   ├── check-staleness.sh    # git 落后检测
│   └── regen_palace.py       # 从 external/ 重建 MemPalace 索引
├── CHANGELOG.md
└── README.md
```

## 配置分层

| 内容 | 在哪 | 跨设备 |
|---|---|---|
| 启发式 / schema / 票据 / 主题默认值 | Git repo | ✓ |
| 本机 KB 路径 / 自定义 topic / 阈值 | `~/.claude/kb/config.local.yaml` | ✗ |
| MemPalace / cc-connect / API keys | 运行时检测 | ✗ |

## 已知限制

- v0.1.x 阶段，CLI status 之外的统计查询需要 `awk`（macOS / Linux 都自带）
- MemPalace 镜像依赖 `~/.claude.json` 里有 `mempalace` 字符串；目前不是协议级检测
- `--purge` 模式会删 `~/.claude/kb`，谨慎用

## 完整设计文档

`specs/kb-workflow/plan.md`（含 D1-D8 决策 + W1-W6 跨设备决策 + CLI 设计）

## License

MIT
