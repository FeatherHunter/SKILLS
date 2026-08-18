# configure-third-party-llm

在 DSH（DeepSeek Harness）里把任意第三方 LLM 网关作为 provider 路由写入 `~/.dsh/settings.yaml`。
Anthropic-messages 与 OpenAI-completions 两种线协议都支持。改 Key、改域名、改协议都走这条路径。

## 一句话

告诉 AI 四件事（路由 id、协议、baseURL、env 名），AI 直接把你的第三方 LLM 接入 DSH，UI 上能用、能选思考等级。

## 适用场景

- 把 `minnimax.chat` 这种 OpenAI-兼容网关接到 DSH 当作 MiniMax-M3 后端
- 在 DSH 写一个自建 MiniMax 反代（Anthropic-messages 协议）
- 让已有的 DSH 第三方路由切换 Key / 域名 / 协议
- UI 上"思考等级"行不显示时——多半是本技能覆盖的事

## 不适用

- 写 DSH 插件或主题代码
- 修改 `~/.dsh/credentials.yaml` / 系统环境变量 / `.env`（让用户自己改 key 的真实值）
- 改 DSH 默认模型（用户后续自己选）
- 配置 WSL Hermes / OpenCode 等其它 agent 系统的模型
- 配置 DSH 内置已支持的 `minimax` / `minimax-cn` / `openai` / `anthropic` 等（已有 catalog）

## 30 秒上手

打开 DSH 对话，描述你想要的：

> "用 OpenAI 兼容协议接入 minnimax.chat 的 MiniMax-M3，路由叫 `xianyu-minimax`，env 是 `XIANYU_MINIMAX_API_KEY`"

AI 会按本技能的协议分支决策树写出正确的 `llm-pi-ai.providers.<route>` 段并写入 `~/.dsh/settings.yaml`。
无需重启。DSH 的 settings watcher 会热加载。

## 关键文档

- [`SKILL.md`](./SKILL.md) — AI 主读本（协议分支 / 配置模板 / 流程 / 硬规则 / 坑位 / 自检）
- [`AGENTS.md`](./AGENTS.md) — Agent 协作入口 / 边界 / 部署形态

## 实战案例（2026-08-21 · xianyu-minimax）

| 项 | 值 |
|---|---|
| 路由 id | `xianyu-minimax` |
| 协议 | `openai-completions`（第三方便宜网关 MiniMax-M3M3 走 OpenAI 兼容端点） |
| baseURL | `https://minnimax.chat/v1` |
| env | `XIANYU_MINIMAX_API_KEY` |
| 关键坑位 | openai-completions 协议下 `thinkingFormat` 默认不写，**不要**填 `deepseek`（那是 DeepSeek 自己的方言，不是 MiniMax） |
| Effort 行修复 | 加 `compat.supportsReasoningEffort: true` + 5 档 `reasoningEfforts`（off/low/medium/high/max）后 UI 正常显示 |

完整配置：

```yaml
llm-pi-ai:
  providers:
    xianyu-minimax:
      apiKeyEnv: XIANYU_MINIMAX_API_KEY
      api: openai-completions
      baseURL: https://minnimax.chat/v1
      compat:
        supportsReasoningEffort: true
      models:
        - id: MiniMax-M3
          name: MiniMax-M3-59.9
          reasoningEfforts:
            off:
            low: low
            medium: medium
            high: high
            max: max
```

## 触发词示例

- "配置第三方模型"
- "接入 MiniMax 第三方"
- "改 xianyu-minimax 的 Key"
- "minnimax.chat 换域名"
- "让自定义模型显示思考等级"
- "用 OpenAI 兼容协议接入 X"
- "用 anthropic 协议接 X"
- "删掉 xianyu-minimax"
- "我 DSH 第三方模型不显示 Effort 行"
