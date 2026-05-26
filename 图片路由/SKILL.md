---
name: 图片路由
description: 图片内容智能识别与技能路由。当用户发送图片时，判断是否与技能（饼干记账/居家管家/卡路里）相关，不相关则正常聊天，相关则识别内容并推荐技能组合。
---

# 图片路由技能 v1.0

## 核心定位

作为用户发图片时的统一入口，负责：
1. **快速判断**：图片是否与任一技能相关
2. **内容识别**：识别图片具体内容
3. **技能推荐**：推荐可执行的技能组合
4. **路由执行**：用户确认后依次调用技能

## 触发条件

用户发送图片（无论是否有文字）时，首先触发此技能。

## 使用流程

### 流程原则

AI 根据图片内容自主判断，灵活处理。不要机械套用步骤，观察图片后自行决定：

1. **先subagent解析图片**：收到图片立即fork给subagent调用`mmx vision describe`识别内容，主agent调用`sessions_yield()`等待，不阻塞
2. **再判断是否相关**：subagent解析完成后，基于识别结果判断是否可能与（记账/居家管家/卡路里）相关
3. **最后确认执行**：展示识别结果和推荐操作，用户确认后再执行

### 判断依据

- 涉及金额/交易 → 饼干记账
- 涉及物品存放 → 居家管家
- 涉及食物/营养 → 卡路里
- 多信号叠加 → 可能需要多技能联动

### 重要原则

- **优先相信用户的直接意图**，避免过度关联
- 如果用户只是分享图片，不要主动推荐技能
- 用户明确要求记录时才调用技能

### ⚠️ 图片识别工具优先级

**识别图片内容时，优先使用 `mmx vision describe`：**
```bash
mmx vision describe --image <图片路径> --prompt "描述这张图片的内容"
```

**原因**：`mmx vision describe` 是用户配置的 MiniMax 图像识别 CLI，效果稳定。`image` 工具（调用视觉模型）经常因参数问题报错。

**只有当 mmx 识别效果不好时**，才考虑其他方案。

---

## AI执行指南（subagent异步模式）

图片路由的默认执行方式：主agent接收到图片后，立即fork给subagent处理，主agent通过yield等待结果。

### 标准流程

```
用户发图片 → 主agent fork subagent → sessions_yield() → 唤醒后继续主流程
```

### 工具调用顺序

```python
# 1. fork子agent处理图片（立即下发，不判断耗时）
subagent = sessions_spawn(
    context="fork",                                    # 继承主agent上下文
    task=f"mmx vision describe --image <{image_path}> --prompt "描述这张图片内容"",
    taskName="img_parse",                              # 任务标识
    delivery={"mode": "announce", "channel": "current"}  # 完成推送到当前session
)

# 2. 释放主agent（此时可处理其他消息/任务）
sessions_yield()

# 3. 唤醒后，subagent输出已在上下文中，直接使用
```

### 关键约束

- 主agent**不判断**耗时，图片路由默认走subagent模式
- **一对一到**：每个subagent对应一次sessions_yield()
- **失败容错**：唤醒后检查exitCode，失败则降级为同步识别
- **结果获取**：唤醒后直接读取子agent输出，无需额外API调用

### 降级规则

当subagent失败时，自动降级为同步执行：
```bash
mmx vision describe --image <图片路径> --prompt "描述这张图片内容"
```

---
### 用户确认

无论识别结果如何，都需要展示给用户并确认：
- 识别出了什么
- 建议执行哪些操作
- 用户选择后执行

每个技能执行完成后询问是否继续，不需要一次确认所有要执行的技能。

---