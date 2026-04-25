---
name: hermes-openclaw-bridge
description: Hermes 与 OpenClaw 联合调度 - 让 Hermes 通过 terminal 工具调用 OpenClaw agent 执行任务，结果返回 Hermes 再处理。适用场景：OpenClaw 独有功能、隔离执行、已有 OpenClaw workflow 复用。
---

# Hermes OpenClaw Bridge

让 Hermes 作为调度器，调用 OpenClaw agent 执行任务，结果返回 Hermes 处理。

## 架构

```
微信/消息 → Hermes → [terminal工具] → openclaw agent CLI
                                         ↓
                                   OpenClaw 执行
                                         ↓
                                   返回 JSON 结果
                                         ↓
                          Hermes 解析 → 处理 → 回复用户
```

## 调用命令

```bash
openclaw agent --agent <agent_id> --message "<任务描述>" --json
```

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--agent` | 指定 agent ID | `main`、`ops` 等 |
| `--message` | 任务描述，可包含上下文 | "用户说：XXX，请执行YYY" |
| `--json` | 输出 JSON 格式，方便解析 | 必须加 |
| `--timeout` | 超时秒数，默认 600 | `--timeout 300` |
| `--thinking` | 思考深度 | `off`, `medium`, `high` |

### 返回格式

```json
{
  "runId": "uuid",
  "status": "ok",
  "summary": "completed",
  "result": {
    "payloads": [
      { "text": "执行结果文本", "mediaUrl": null }
    ],
    "meta": {
      "durationMs": 24046,
      "agentMeta": {
        "sessionId": "uuid",
        "provider": "minimax",
        "model": "MiniMax-M2.7-highspeed",
        "usage": { "input": 104, "output": 31, ... }
      }
    }
  }
}
```

## 解析结果

Hermes 的 `terminal()` 返回后，用 Python 解析：

```python
import json
result = terminal("openclaw agent --agent main --message '...' --json")
data = json.loads(result["output"])
text = data["result"]["payloads"][0]["text"]
```

## 完整示例

### Python execute_code 方式

```python
from hermes_tools import terminal
import json

def call_openclaw(task: str, context: str = "") -> str:
    msg = f"【来自Hermes调度】\n任务：{task}"
    if context:
        msg += f"\n上下文：{context}"
    
    res = terminal(f'openclaw agent --agent main --message "{msg}" --json')
    data = json.loads(res["output"])
    
    if data["status"] == "ok":
        return data["result"]["payloads"][0]["text"]
    else:
        return f"执行失败：{data.get('error', 'unknown')}"
```

### Hermes cron prompt 调用方式

在 cron 的 prompt 中直接写：

```
用以下命令让 OpenClaw 执行任务：
  openclaw agent --agent main --message "【任务描述】" --json
解析返回的 JSON，从 result.payloads[0].text 提取结果。
```

## 使用场景

| 场景 | 为什么用 Bridge | 示例 |
|------|----------------|------|
| OpenClaw 独有插件 | OpenClaw 有特定插件 Hermes 没有 | OpenClaw 的某些第三方集成 |
| 隔离执行 | 危险操作想在沙盒里跑 | 未验证的代码、下载陌生脚本 |
| 已有 workflow | OpenClaw 已有成熟流程不想迁移 | 之前写好的 OpenClaw cron 任务链 |
| OpenClaw 调试 | 想单独在 OpenClaw 环境测试 | `--thinking high` 深度思考 |
| 负载分担 | 两个系统跑不同类型任务 | Hermes 跑对话，OpenClaw 跑定时脚本 |

## 限制与注意事项

- **不是消息通道** — 这是 Hermes 主动调用 OpenClaw，不是 OpenClaw 收到微信消息转发 Hermes
- **单向调度** — Hermes → OpenClaw，OpenClaw 不会主动回调 Hermes
- **需要 OpenClaw Gateway 运行** — `openclaw-gateway` 必须在跑，端口 18789
- **结果需解析** — 需要 terminal 返回后手动解析 JSON
- **超时默认 600s** — 复杂任务可能需要 `--timeout` 调大

## 检查 OpenClaw 状态

```bash
openclaw health
# 或
openclaw agents list
```

## 故障排查

**报错：Gateway agent failed**
→ OpenClaw Gateway 没在跑，启动它：`openclaw gateway run` 或 `tmux new -s openclaw 'openclaw gateway run'`

**报错：Pass --to / --session-id / --agent**
→ 没指定 agent，需要加 `--agent main` 或其他 agent ID

**返回空 text**
→ 检查 `result.payloads` 是否有内容，或看 `result.meta` 里的错误信息

**JSON 解析失败**
→ 某些命令输出可能不是纯 JSON，先 `terminal(... --json 2>&1)` 捕获所有输出再解析
