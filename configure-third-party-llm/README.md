# configure-third-party-llm

在 DSH（DeepSeek Harness）里把任意第三方 LLM 网关作为 provider 路由写入 `~/.dsh/settings.yaml`。
覆盖 Anthropic-messages 与 OpenAI-completions 两种线协议。技能按 **5-axis** 组织：身份（id/displayName/api/baseURL）/ 凭据（apiKeyEnv）/ 模型列表（models[] 或 modelOverrides）/ 能力（input/contextWindow/maxTokens/reasoningEfforts/compat + 路由级默认值）/ 行为（headers/transport/cacheRetention/retryPolicy/timeouts/thinkingBudgets）。

## 一句话

告诉 AI 4 件事（路由 id、协议、baseURL、env 名），AI 直接把你的第三方 LLM 接入 DSH——UI 能选模型 / 选推理档位 / 上传图片附件 / 调 `read_image` 工具 / 走 WebSocket / 重试 / 长留 KV 缓存——全部正确生效。

## 适用场景

- 把 `minnimax.chat` 这种 OpenAI-兼容网关接到 DSH 当作 MiniMax-M3 后端
- 在 DSH 写一个自建 MiniMax 反代（Anthropic-messages 协议）
- 让已有的 DSH 第三方路由切换 Key / 域名 / 协议 / 上下文窗口 / vision 能力 / 重试策略 / HTTP 头
- **让第三方 vision 模型能看图**：上传图片附件不再报 `does not support image input`；`read_image` 工具可调
- **给内置 catalog 模型打 vision / 容量补丁**：用 `modelOverrides` 给 `gpt-4.1` 之类补上 `input: [text, image]` 或 `contextWindow: 1000000`
- **调超时 / 重试 / KV 缓存 / transport**：catalog 复用路由也能加 axis 5 字段
- UI 上"思考等级"行不显示时——多半是本技能覆盖的事

## 不适用

- 写 DSH 插件或主题代码
- 修改 `~/.dsh/credentials.yaml` / 系统环境变量 / `.env`（让用户自己改 key 的真实值）
- 改 DSH 默认模型（用户后续自己选）
- 配置 WSL Hermes / OpenCode 等其它 agent 系统的模型
- 配置 DSH 内置已支持的 `minimax` / `minimax-cn` / `openai` / `anthropic` 等（已有 catalog）
- 配置附件 / attachment store（由 DSH 平台负责；本技能只声明模型能/不能收 image）
- 配置 audio / video / pdf 等其它模态（DSH 当前仅支持 `text` + `image`）
- 写 `dsh-llm-retry` 插件的细节（retry 的执行交给它，本技能只声明意图）

## 30 秒上手

打开 DSH 对话，描述你想要的：

> "用 OpenAI 兼容协议接入 minnimax.chat 的 MiniMax-M3，路由叫 `xianyu-minimax`，env 是 `XIANYU_MINIMAX_API_KEY`，支持图片，1M 上下文，10 分钟流空闲超时"

AI 会按本技能的 5-axis 协议分支决策树写出正确的 `llm-pi-ai.providers.<route>` 段，先 **Preview diff** 给你确认，再写入 `~/.dsh/settings.yaml`，然后让你去 DSH UI 验证。
无需重启。DSH 的 settings watcher 会热加载。

## 关键文档

- [`SKILL.md`](./SKILL.md) — AI 主读本（5-axis Schema 字段速查 / 输入模态 / 模型容量 / 推理档位 / 路由级行为 / 配置模板 / 流程 / 自检 / 硬规则 / 坑位 / 示例）
- [`AGENTS.md`](./AGENTS.md) — Agent 协作入口 / 边界 / 部署形态

## 实战案例（2026-08-21 · xianyu-minimax）

| 项 | 值 |
|---|---|
| 路由 id | `xianyu-minimax` |
| 协议 | `openai-completions`（第三方便宜网关 MiniMax-M3 走 OpenAI 兼容端点） |
| baseURL | `https://minnimax.chat/v1` |
| env | `XIANYU_MINIMAX_API_KEY` |
| 关键坑位 | openai-completions 协议下 `thinkingFormat` 默认不写，**不要**填 `deepseek`（那是 DeepSeek 自己的方言，不是 MiniMax） |
| Effort 行修复 | 加 `compat.supportsReasoningEffort: true` + 5 档 `reasoningEfforts`（off/low/medium/high/max）后 UI 正常显示 |
| vision 启用 | 模型 entry 加 `input: [text, image]`，或整条路由 `defaultInput: [text, image]`（**前提**：minimax.chat 实测支持 vision——多声明让 durable 历史死循环） |
| 上下文扩 1M | `models[].contextWindow: 1000000`（DSH 不验证网关是否兑现，**多声明比少声明安全**——超出被截断但不产生死循环） |
| 流空闲超时 | `streamIdleTimeoutMs: 900000`（15 分钟，长 thinking 模型的合理值） |

完整配置（含 vision + 1M 上下文 + 长流空闲）：

```yaml
llm-pi-ai:
  providers:
    xianyu-minimax:
      apiKeyEnv: XIANYU_MINIMAX_API_KEY
      api: openai-completions
      baseURL: https://minnimax.chat/v1
      compat:
        supportsReasoningEffort: true
      streamIdleTimeoutMs: 900000       # 长 thinking 需要
      models:
        - id: MiniMax-M3
          name: MiniMax-M3-59.9
          input: [text, image]          # vision 能力（前提：minimax.chat 实测支持）
          contextWindow: 1000000        # 1M 上下文
          maxTokens: 32768              # 输出上限 + 请求默认
          reasoningEfforts:
            off:
            low: low
            medium: medium
            high: high
            max: max
```

## 触发词示例

### Identity / 协议 / 凭据
- "配置第三方模型"
- "接入 MiniMax 第三方"
- "改 xianyu-minimax 的 Key"
- "minnimax.chat 换域名"
- "用 OpenAI 兼容协议接入 X"
- "用 anthropic 协议接 X"
- "删掉 xianyu-minimax"
- "我 DSH 第三方模型不显示 Effort 行"
- "env 没读到"

### Vision / image
- "让 xianyu-minimax 能看图"
- "让 read_image 工具能用"
- "第三方模型收不到图片附件"
- "model does not support image input"
- "给 gpt-4.1 加上 vision"
- "用 modelOverrides 给内置模型打补丁"
- "整条路由默认支持 vision"
- "这个模型只要文本能力，剥掉 image"

### 容量 / 推理
- "改 1M 上下文"
- "contextWindow 改 X"
- "maxTokens 改 X"
- "让自定义模型显示思考等级"
- "改网关方言 / thinkingFormat 改 X"
- "Effort 行不显示"

### 行为
- "加 User-Agent / 自定义 HTTP 头"
- "换 transport / 改 WebSocket"
- "改 KV 缓存策略 / cacheRetention 改 long"
- "调超时 / 改 timeout / 改 streamIdleTimeoutMs"
- "调重试 / 加 retryPolicy"
- "限思考 token / thinkingBudgets"

### Lifecycle
- "给我看 diff / 预览改动"
- "备份 settings.yaml"
- "验证配置生效 / 怎么测"
- "回滚 / 撤销刚才改动"