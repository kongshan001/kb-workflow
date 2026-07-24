# kb-workflow

> 持续收录外部资料 + 反向抽取为结构化条目的工作流。跨设备一键装。

## 一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/yourname/kb-workflow/main/install.sh | bash
```

## 命令

| 命令 | 做什么 |
|---|---|
| `kb-workflow install` | 一键装（首次或新设备） |
| `kb-workflow update` | 拉新版 workflow |
| `kb-workflow status` | 看当前状态 |
| `kb-workflow uninstall` | 干净卸载 |

## 设计要点

- **静默收录 + 可审计**：每条条目来源可追、分类可见
- **4 类 schema**：fact / preference / decision / tentative
- **混合存储**：文件（源数据）+ MemPalace（语义索引）
- **软降级**：缺工具不全罢工
- **分级更新**：patch/minor 自动，major 询问

详见 `specs/kb-workflow/plan.md`（设计文档）。

## 仓库结构

```
kb-workflow/
├── SKILL.md                  # 助手启动加载
├── install.sh / uninstall.sh
├── bin/kb-workflow           # CLI 主入口
├── config/
│   ├── defaults.yaml
│   ├── schema/               # 4 类 schema 模板
│   ├── heuristics.yaml
│   ├── topics.yaml
│   └── ticket-format.md
├── scripts/
│   ├── capability-detect.sh
│   ├── check-staleness.sh
│   └── regen_palace.py
├── CHANGELOG.md
└── README.md
```

## License

MIT
