# 票据输出格式

每次静默收录后，在回复末尾打印票据行。

## 基础捕获
```
📌 记为 <type>: <slug>  source=<src>  confidence=<c>
```

示例：
```
📌 记为 fact: fact-three-meshbasic-no-custom-uniforms  source=user-stated  confidence=high
```

## 冲突
```
⚠️  CONFLICT with <other_slug>: <reason>
```

## 细化
```
🔗 REFINES <parent_slug>: <delta>
```

## 更新
```
✏️  UPDATES <old_slug>: <change>
```

## 完整示例（一次输入触发多条）

```
📌 记为 fact:       fact-three-meshbasic-no-custom-uniforms
   source=user-stated  confidence=high  scope=web/threejs

📌 记为 decision:   decision-demo1-shader-use-shadermaterial
   source=user-stated  supersedes=null  context=demo1 shader demo 渲染入口统一

📌 记为 tentative:  tentative-try-sdf-text-rendering
   source=user-stated  status=open
```
