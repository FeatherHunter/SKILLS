# AI 行为日志协议

> 本协议定义智剪工坊 AI 行为日志的文件结构、写入触发、字段 schema、self-reference 风险缓解。
> SKILL.md 必须引用本协议；AI 加载 SKILL.md 后必读。

## 1. 概述

AI 行为日志记录 AI 在执行智剪工坊任务时的：
- **流程节点**（Stage X.Y 当前在哪）
- **决策理由**（为什么这么做）
- **思考链**（考虑过的方案）

**输出位置**：`<workspace>/00_智剪/中间产物/logs/<task_id>_<timestamp>.<ext>`（完整命名见 §6）

**目的**：
1. 审计 AI 是否按流程走（合规性）
2. 诊断错误时区分「AI 流程问题」vs「底层脚本 bug」

## 2. 双格式设计

| 文件 | 用途 | 写入时机 | 写入主体 |
|---|---|---|---|
| `<task_id>.md` | 人类可读总结 | 阶段结束 + 异常时 | AI 重写整文件或 append stage section |
| `<task_id>.jsonl` | 机器可读详细 | **每次 CLI 调用前** append 一行 | AI 用 `open('a').write(json.dumps(...)+chr(10))` |

## 3. JSONL 字段 Schema

每行一个 JSON 对象：

```json
{
  "time": "2026-07-10T10:30:15",
  "stage": "1",
  "step": "2",
  "action": "trim",
  "decision": "trim 0-5s",
  "thinking": "视频抖动 + 用户提到...",
  "result": "exit 0",
  "error": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| time | string (ISO 8601) | 是 | 时间戳 |
| stage | string | 是 | 当前阶段号（"0"-"5"）|
| step | string | 是 | 当前 stage 内步骤 |
| action | string | 是 | 执行的操作类型（trim / color / ask / ...）|
| decision | string | 是 | 本次决策内容 |
| thinking | string | 是 | 思考链（含考虑的方案）|
| result | string | 否 | CLI exit code / 异常类型 |
| error | string|null | 否 | 错误信息（null = 无错误）|

## 4. Self-reference 风险缓解

LLM 有 self-reference 风险：AI 输出思考后，会在后续 context 里看到自己说"我选 X 因为 Y"，这会强化 X 的执行（即使错了也不易反转）。

**缓解策略**：

1. **XML 标签隔离**：thinking 用 `<thinking>` 标签包裹，AI 不主动回看 thinking 内容
2. **阶段 checkpoint**：每 stage 结束 AI 必须 re-decide "我现在还坚持前面的决策吗？"

**审计时机**（3 种触发场景）：
- **每 stage 结束**：写入 .md + checkpoint 重决策
- **异常时**：写入 .md 异常节 + chat 通知用户
- **决策犹豫时**（用户在 chat 追问）：写入 .md 并主动暴露 thinking 给用户审查

**AI 写入模板**：

```xml
<thinking>
[阶段 X.Y] 决策：...
思考：考虑了 A/B/C，B 最优因为...
</thinking>

<action>
[JSONL append]
</action>
```

## 5. Markdown (.md) 章节结构

```markdown
# 任务 <task_id>

## Stage 0 项目初始化
[时间] 决策：HTML 表单填写
[时间] 异常：...（如有）

## Stage 1 意图对齐
[时间] 决策：与用户确认 3 个意图点
[时间] 决策：选择「健身 vlog」模板

## Stage 2 粗加工
[时间] 调：scripts/video/trim.py
[时间] 异常：CUDA OOM（已重试 3 次失败）

## Stage 3 模板
...

## Stage 4 产物审查·用户交互循环
...

## Stage 5 收尾
...
```

## 6. 文件命名约定

`<workspace>/00_智剪/中间产物/logs/<task_id>_<timestamp>.<ext>`

- `<task_id>`：来自 intent.json.project.title 的 slug（小写、连字符）
- `<timestamp>`：YYYYMMDD_HHMMSS

**示例**：
- `vlog_20260710_103015.md`
- `vlog_20260710_103015.jsonl`

## 7. 文件生命周期

- 创建时机：阶段 0 完成、用户提交 intent.json 后
- 跟随任务：直至阶段 5 完成
- 归档时机：剪映导出后，可选 `mv logs/ .archive/logs/<task_id>/`
