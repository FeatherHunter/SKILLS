# AGENTS · configure-third-party-llm

本技能的 Agent 协作入口。仓库级别约定见 `D:\2Study\StudyNotes\SKILLS\AGENTS.md` 与对应 DSH 项目根的 AGENTS.md（如有）。

## 文件清单

| 文件 | 角色 |
|---|---|
| `SKILL.md` | AI 主读本（5-axis Schema 字段速查 / 输入模态 / 模型容量 / 推理档位 / 路由级行为 / 配置模板 / 流程 / 自检 / 硬规则 / 坑位 / 示例） |
| `README.md` | 人类阅读版入口（一句话 / 适用场景 / 30 秒上手 / 触发词） |
| `AGENTS.md` | 本文件 |

## 部署形态

- 真实源在 `D:\2Study\StudyNotes\SKILLS\configure-third-party-llm\`
- DSH 通过 **目录 junction**（`mklink /J`）把它挂到 `C:\Users\辰辰洋洋\.dsh\skills\configure-third-party-llm`
  - DSH 的 `dsh-skill-filesystem` provider rank 400 扫 `<dshHome>/skills`
  - `watchFollowSymlinks: true` → junction 跟随
- 修改 SKILL.md 不必手工重链；junction 一旦建好就是同一个 inode

junction 建立命令（`mklink /J` 跨盘可、无需管理员）：

```powershell
# 删旧链（如存在）
cmd /c rmdir "C:\Users\辰辰洋洋\.dsh\skills\configure-third-party-llm" 2>nul
# 建新链
cmd /c mklink /J "C:\Users\辰辰洋洋\.dsh\skills\configure-third-party-llm" "D:\2Study\StudyNotes\SKILLS\configure-third-party-llm"
```

## 与 DSH 项目根的边界

- DSH 项目本身（`C:\Users\辰辰洋洋\AppData\Roaming\DSH Desktop\agent\`）的 AGENTS.md **对本技能不直接相关**——本技能改的是用户态的 `~/.dsh/settings.yaml`，不动 DSH 平台代码
- 平台代码的 schema / catalog / provider 配置如果升级，DSH 重启 DSH 进程即可，不需要重链本技能

## 边界声明（按 5-axis）

| Axis | 本技能管 | 本技能不管 |
|---|---|---|
| 1. Identity | 路由 id / displayName / api / baseURL | 路由 id 与官方 catalog provider 重名时的优先级 |
| 2. Credential | apiKeyEnv 的 env 名引用 | `~/.dsh/credentials.yaml` 的实际 key 值、系统 env 变量 |
| 3. Models | `models[]` 的完整定义 / `modelOverrides` 的 catalog 修补 | pi-ai 内置 catalog 的字段值（除非用 `modelOverrides` 修补） |
| 4. Capabilities | `input` / `contextWindow` / `maxTokens` / `reasoningEfforts` / `compat` + 路由级 `defaultContextWindow` / `defaultMaxTokens` / `defaultInput` / `reasoning` | 网关实际支持的容量与模态（DSH 不验证） |
| 5. Behavior | `headers` / `transport` / `cacheRetention` / `timeoutMs` / `streamIdleTimeoutMs` / `websocketConnectTimeoutMs` / `retryPolicy` / `thinkingBudgets` | `dsh-llm-retry` 插件的执行细节（它负责实现 `retryPolicy`） |

**全局不管**：
- 不动 `agent-default-model`（用户后续人工选）
- 不管 WSL Hermes / OpenCode 等其它 agent 系统的模型配置
- 不管附件 store（`dsh-attachment`）；本技能只声明模型能/不能收 image，不部署图片上传后端
- 不管 `read_image` 工具的输入参数 schema（`dsh-tool-fs` 的活）；本技能只确保该工具的 image gate 不会拦下调用
- 不管 audio / video / pdf 等其它模态（DSH 当前 schema 仅 `text` + `image`，其它值会被拒）

## 改动前 3 问

1. 影响哪个文件？→ 只 `SKILL.md`（AGENTS.md / README.md 偶尔调整）
2. 有没有数据迁移？→ 无（settings.yaml 是用户态，schema 升级向后兼容）
3. 回滚方案？→ `rmdir` junction + 删除 `D:\2Study\StudyNotes\SKILLS\configure-third-party-llm\`（也支持 git revert，如果源目录在 git 仓里）

## 关键设计决策（first principles）

### 为什么按 5-axis 组织

DSH 的 `PiAiProviderProfile` 实际有 19 个字段，按功能归类：
- Identity（4）：路由 id / displayName / api / baseURL
- Credential（1）：apiKeyEnv
- Models（2）：models[] / modelOverrides
- Capabilities（10 字段，3 model-level + 3 route-defaults + 2 compat 字段 + 2 路由级兜底）：input / contextWindow / maxTokens / reasoningEfforts / compat / defaultContextWindow / defaultMaxTokens / defaultInput / reasoning
- Behavior（8）：headers / transport / cacheRetention / timeoutMs / streamIdleTimeoutMs / websocketConnectTimeoutMs / retryPolicy / thinkingBudgets

5-axis 让用户/AI 按"想改什么"而非"字段叫什么"来导航。

### 为什么 vision 与 capacity 的「少声明安全」不对称

- **vision 多声明（`[text, image]` 但网关只接受 text）**：DSH 不验证网关，图片进入请求构造 → 网关拒绝 → **消息已写进 durable 历史** → 会话后续轮次重发同一图片 → **死循环**
- **capacity 多声明（`contextWindow: 1M` 但网关只给 200K）**：请求正常构造 → 网关在中间截断或 400 → **消息没成功** → 用户手动改字段

vision 是**前置门**（构造请求前 preflight 拒绝 / 不拒绝），capacity 是**后置门**（请求发送后网关兜底）。所以 vision 倾向"少声明保守拒绝"，capacity 倾向"多声明放手"。

### 为什么 thinkingFormat 是 `compat` 不是顶层字段

`compat` 是 pi-ai 的 `OpenAICompletionsCompat` 子集。pi-ai 的 wire dispatch 字段（`thinkingFormat` / `supportsReasoningEffort`）只存在于 OpenAI 兼容协议的模型上：
- Anthropic-messages：协议自带 thinking（base request body 字段）→ 不需要 compat
- OpenAI-completions：thinking 走 `reasoning_effort` 字段，但不同方言的 wrapping 不同（DeepSeek 的 `thinking: {type,effort}` / 千问的 `enable_thinking` / 等）→ 需要 compat 声明方言

所以 model-level compat 在其它协议上会被 schema 直接拒（"sets compat reasoning switches, but its api is X"）。

### 为什么 streamIdleTimeoutMs 不是 MAX_TIMER_DELAY_MS 简单上限

Node.js 的 `setTimeout` 最大值约 24.8 天（`MAX_TIMER_DELAY_MS`）。超过这个值 timer 立即触发 → 不能用来"等很久"。DSH 把上限设到这个值确保 timer 不会立即爆。

## 输入模态（image）的边界

- 本技能允许声明 `input: [text]` / `[text, image]` / `[image]`，值必须是字面量字符串
- **不**验证网关实际支持的模态（DSH 不询问）；少声明只是被 preflight 拒绝，多声明会让 durable 历史死循环
- catalog 已知 anthropic / openai 等路由自动含 vision；其他手写路由必须显式声明
- 想"保留 catalog 但改一个模型的 vision 能力" → 用 `modelOverrides`
- 想"全替换 catalog 或写新模型" → 用 `models[]`
- 两者不能并存；同一路由下 schema 直接报错

## 模型容量（capacities）的边界

- `models[].contextWindow` / `maxTokens` 字段**信任**网关（DSH 不询问）
- `maxTokens` 在 `models[]` 里是**请求默认**；catalog.maxTokens 只是**能力声明**
- `defaultContextWindow` / `defaultMaxTokens` 路由级兜底，永远不是请求默认
- 多声明比少声明安全（容量超出会被截断但不产生死循环）

## 路由级行为（behavior）的边界

- `headers` 凭据会被脱敏 `describe()` 原样返回 → 凭据一律走 `apiKeyEnv`
- `transport` / `cacheRetention` / `thinkingBudgets` **provider 不支持则静默忽略**
- `timeoutMs` / `streamIdleTimeoutMs` / `websocketConnectTimeoutMs` 是**硬超时**，到点 abort
- `retryPolicy` 是 provider 自有重试意图，由 `dsh-llm-retry` 插件在 agent 失败步骤执行
- 旧的 `maxRetries` / `maxRetryDelayMs` 顶级字段已移除（schema 拒）

## 来源声明

本技能 2026-08-21 创建；2026-08-22 加入 vision/image 输入模态支持；2026-08-22（再次）按 5-axis 第一性原理重写——补全 Axis 4 容量 + Axis 5 行为全字段，加入 Preview/Verify/Rollback 生命周期，修补 thinkingFormat 漏的 `openai` 值，加入 6 个新硬规则 + 8 个新坑位 + 3 个新示例。基于：

- DSH 实测调查：`@deepseek-ai/dsh-llm-pi-ai` (v0.1.0-rc.7) 的 schema（`catalog.d.ts` / `config.d.ts`）+ `dsh-llm-pi-ai/README.md` § Catalog resolution
- pi-ai v0.x 的 wire 协议源码（`@earendil-works/pi-ai/dist/api/openai-completions.js` 第 560-640 行）
- pi-ai 内置 catalog：`@earendil-works/pi-ai/dist/providers/data/*.json`（含 `input` 字段的 vision 模型示例）
- `dsh-tool-fs/lib/types/read-image.d.ts` 的 image gate 强制约束
- `dsh-mcp-client/README.md` 关于 "exact calling model route explicitly declares image input" 的硬约束
- `dsh-llm/lib/types/retry-policy.d.ts` 的 retryPolicy schema
- 用户实战案例：`xianyu-minimax` 路由（OpenAI-completions 协议），通过本技能首次完整跑通
- 既有的 settings.yaml 状态（C:\Users\辰辰洋洋\.dsh\settings.yaml）

## commit 规范

源目录 `D:\2Study\StudyNotes\SKILLS\configure-third-party-llm\` 目前不在 git 仓（用户 StudyNotes 主仓是另一回事）。如未来加入 git，提交规范参考根仓 AGENTS.md：
- 中文主题
- Tested-By: exempt(纯模板技能，无 fresh agent)