# 票据输出格式

v0.2.0 active-first：票据只在显式 capture 后打。

## /kb-capture 成功后（结构化条目）

```
📌 /kb-capture → <type>: <slug>  source=<src>  confidence=<c>
```

示例：
```
📌 /kb-capture → fact: fact-bge-m3-multilingual
   source=user-stated  confidence=medium  scope=ml/embedding
```

## /kb-save-article 成功后（原始资料）

```
📥 /kb-save-article → external/<filename>  topic=<topic>
```

示例：
```
📥 /kb-save-article → external/2026-07-25-ragflow-intro.md  topic=rag
   source_url=https://github.com/infiniflow/ragflow
```

## 冲突（D5）
```
⚠️  CONFLICT with <other_slug>: <reason>
```

## 细化（D5）
```
🔗 REFINES <parent_slug>: <delta>
```

## 更新（D5）
```
✏️  UPDATES <old_slug>: <change>
```

## 助手主动提示（v0.2.0 新增）

看到值得记的内容但用户没明说 → 助手**只提示一次**，不静默写：

```
💡 这条看起来像 preference：调 shader 性能用 Spector.js。
   要 /kb-capture 吗？
```

提示后**等用户回答**。不回答就不存。
