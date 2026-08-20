---
name: configure-third-party-llm
description: 在 DSH（DeepSeek Harness）中向 `~/.dsh/settings.yaml` 的 `llm-pi-ai.providers.<route>` 段添加第三方 LLM 模型路由，覆盖 Anthropic-messages / OpenAI-completions 两种协议。教 AI 正确写 5 类字段——身份（id/displayName/api/baseURL）/ 凭据（apiKeyEnv）/ 模型列表（models[] 或 modelOverrides）/ 能力（input/contextWindow/maxTokens/reasoningEfforts/compat + 路由级默认值）/ 行为（headers/transport/cacheRetention/retryPolicy/timeouts/thinkingBudgets）。改 Key、改 URL、改协议、加 vision、改上下文窗口、调超时、加 User-Agent 都走这里。当用户说"配置第三方 LLM / 添加 MiniMax 第三方 / 改 xianyu-minimax 的 Key / 换 minimax.chat 域名 / 让自定义模型显示思考等级 / 让第三方模型能看图 / vision 模型接图片 / 改上下文窗口 / 加 HTTP 头 / 换 transport / 调重试策略 / 让 read_image 工具能用 / 第三方 LLM 接入 DSH"等时使用。
---

# configure-third-party-llm

> **第一性原理**：一份 provider route 是声明式描述——DSH 在 `dsh-llm-pi-ai` 把它编译成 `pi-ai` 的 `Provider` + `Models`。schema 字段穷尽在 `@deepseek-ai/dsh-llm-pi-ai/lib/types/config.d.ts`（19 路由字段）和 `catalog.d.ts`（7 模型字段）。本技能只覆盖 DSH 暴露的 5 类字段、两条协议、必要的自检；完整 schema 请看 DSH README。

## 30 秒边界

**管**（5 类字段）：

- **身份** —— 路由 id（dict key）/ `displayName` / `api` / `baseURL`
- **凭据** —— `apiKeyEnv`
- **模型列表** —— `models[]`（替换 catalog）或 `modelOverrides`（修补 catalog），二选一互斥
- **能力** —— model 级 `input` / `contextWindow` / `maxTokens` / `reasoningEfforts` / `compat`；route 级 `defaultContextWindow` / `defaultMaxTokens` / `defaultInput` / `reasoning`
- **行为** —— `headers` / `transport` / `cacheRetention` / `timeoutMs` / `streamIdleTimeoutMs` / `websocketConnectTimeoutMs` / `retryPolicy` / `thinkingBudgets`

**不管**：

- 不改 `~/.dsh/credentials.yaml`（key 裸值；本技能只写 env 名）
- 不动 `agent-default-model`
- 不创建 DSH 插件
- 不管 WSL Hermes / OpenCode / 其它 agent 系统
- 不管 DSH 内置 catalog（`minimax-cn` / `openai` / `anthropic` 等——pi-ai 已自带）
- 不管 attachment store 部署、`read_image` 工具内部、其它 DSH 插件（`dsh-vision` 等）
- 不管 audio / video / pdf 等非 text+image 模态（DSH schema 不支持）

## 触发词表

按 5 类分组——AI 按用户问题路由到对应章节：

### Identity / 协议
| 触发词 | 必备输入 |
|---|---|
| 配置第三方 LLM / 接入 X 模型 / 加一个 MiniMax 路由 | 路由 id / 协议 / baseURL / env 名 |
| 改 Key / 换 key / 换 env | 路由 id，新 env 名 |
| 改 URL / 换域名 / 网关搬迁 / 私有代理 | 路由 id，新 baseURL |
| 换协议 / 改 anthropic / 改 openai-completions | 路由 id，目标协议 |
| 改 UI 显示名 / displayName | 路由 id，新 displayName |
| 删路由 / 移除 X 路由 | 路由 id |

### Models / catalog
| 触发词 | 必备输入 |
|---|---|
| 加新模型 / 加模型 X | 路由 id，模型 id + 能力 |
| 删模型 / 不再列 X | 路由 id，模型 id |
| 修内置 catalog 的 X 模型 | 路由 id（必须命中 catalog provider），`modelOverrides` 路径 |

### Capabilities
| 触发词 | 必备输入 |
|---|---|
| 让 X 模型能看图 / 加 image 模态 / vision 模型接图片 | 路由 id，模型 id 清单（**先确认网关支持 image！**） |
| 关掉 vision / 剥 image 能力 | 路由 id，模型 id |
| 改上下文窗口 / contextWindow 改 X / 1M 上下文 | 路由 id，模型 id，新 contextWindow |
| 改输出上限 / maxTokens 改 X | 路由 id，模型 id，新 maxTokens |
| 让整条路由默认 vision / 默认上下文 X | 路由 id，`defaultInput` / `defaultContextWindow` / `defaultMaxTokens` |
| 让 UI 显示 Effort 行 / 修 reasoningEfforts / 加思考档位 | 路由 id，模型 id + 5 档 reasoningEfforts |
| 修 Effort 行不显示 / 思考等级不见了 | 路由 id + 协议（openai-completions 必补 compat） |
| 修网关方言 / thinkingFormat 改 X | 路由 id，目标 thinkingFormat（**只对 openai-completions**） |

### Behavior
| 触发词 | 必备输入 |
|---|---|
| 加 HTTP 头 / 自定义 User-Agent | 路由 id，`headers` 字典 |
| 换 transport / 改 WebSocket / 改 SSE | 路由 id，目标 transport |
| 改 KV 缓存 / cacheRetention | 路由 id，none / short / long |
| 调超时 / 改 timeout / 改 streamIdleTimeoutMs | 路由 id，目标 ms |
| 调重试策略 / 改 retryPolicy | 路由 id，retryPolicy 配置 |
| 限思考 token / thinkingBudgets | 路由 id，per-level budget 字典 |

## 协议分支决策树

```
1. 路由 id 是否命中内置 catalog provider？
   ├─ 是 → catalog 复用：api/baseURL/models 可省；必改apiKeyEnv
   └─ 否 → 手写路由：必填 api + baseURL + 非空 models[]
2. 网关协议 = ?
   ├─ anthropic-messages → 不写 compat（协议自带 thinking）
   └─ openai-completions → 必写 compat.supportsReasoningEffort: true
3. 模型支持 vision 吗？
   ├─ 确认 → models[].input: [text, image]
   └─ 不确认 → 不写 input（保守拒绝优于死循环）
4. 模型上下文 / 输出是多少？
   ├─ 网关文档明确 → 显式写 models[].contextWindow / maxTokens
   └─ 不确定 → 不写（用 catalog 或 route default；schema 默认 262144 / 32768）
5. 需非 OpenAI 方言吗？
   ├─ 知道 → compat.thinkingFormat
   └─ 不知道 → 不写（pi-ai 按 baseURL 猜）
```

## 输入模态 (Input Modalities)

DSH 仅支持 `text` / `image` 两种模态。`input` 数组可任意顺序，`[text, image]` 与 `[image, text]` 等价；空数组 `[]` 与不写等价。

**三处可声明**（解析顺序：模型 entry `input` → catalog 条目 `input` → route `defaultInput`；route `defaultInput` 必须非空）：

1. **模型 entry 级** —— `models[].input: [text, image]`，单模型覆盖
2. **route 级 `defaultInput`** —— `defaultInput: [text, image]`，给所有手写模型兜底；catalog 模型保留 catalog 自带的模态
3. **catalog 修补 `modelOverrides`** —— 给内置 catalog 模型打补丁（catalog 标 text 但网关实际支持 image）

`image` 没声明会怎么样：

| 场景 | 结果 |
|---|---|
| 用户上传图片附件 | 适配器构造请求时直接抛 `LlmError("pi-ai model \"X\" does not support image input", "UNSUPPORTED_CONTENT")` |
| 模型调用 `read_image` 工具 | `assertImageCapableRoute` 提前拒绝（`dsh-tool-fs` 强制 image gate） |

> 反过来——**多声明更糟**：声明 `image` 但网关实际不接受 → 网关中途拒绝 → 消息已 durable 化 → 会话后续轮次重复同一失败请求。**只在确认网关支持时才声明 `image`**；不知道就不写。

## 模型容量 (Capacities)

`contextWindow` 与 `maxTokens` 解析顺序都是：entry → catalog → route `defaultContextWindow` / `defaultMaxTokens`（262144 / 32768）。**多声明比少声明安全**（容量超出被网关截断但不产生死循环——与 vision 不对称）。

| 字段 | 路由级 default | model entry 显式 | 何时用 |
|---|---|---|---|
| `defaultContextWindow` | 整条路由兜底（262144） | `models[].contextWindow: N` 单模型覆盖 | 网关文档支持多大但 catalog 不描述；统一放大所有手写模型 |
| `defaultMaxTokens` | 整条路由兜底（32768） | `models[].maxTokens: N` 单模型覆盖 | 同上；**注意**：`models[].maxTokens` 会变成**请求默认**，catalog.maxTokens 不会 |

**`maxTokens` 的双义陷阱**：
- catalog 里 `maxTokens: 200000` 只是模型的**能力**——DSH 不会拿它当请求默认
- 用户 profile 里写 `models[].maxTokens: 200000` 是**请求默认**——以后每个不发 `max_tokens` 的请求都被截到 200000
- 想"声明能力但不当默认" → 不写在 `models[]`；想"声明能力且做默认" → 写在 `models[]`

## 推理档位与 compat

### thinkingFormat 全表（DSH 允许 8 个值）

| 值 | 实际发送 | 谁用 |
|---|---|---|
| `openai` | 纯 `reasoning_effort` 字段（默认行为） | 任何标准 OpenAI 兼容网关 |
| `deepseek` | `thinking: {type: "enabled"}` + `reasoning_effort` | DeepSeek V3/V4 openai-completions 方言 |
| `zai` | `thinking: {type: "enabled"}` + `reasoning_effort` | GLM 系列（z.ai / 智谱） |
| `qwen` | `enable_thinking: <bool>` + `reasoning_effort` | 千问系列 |
| `openrouter` | `reasoning: {effort: ...}` 嵌套 | OpenRouter |
| `ant-ling` | `reasoning: {effort: ...}` 嵌套 | ant-ling 网关 |
| `together` | `reasoning: {enabled: ...}` + `reasoning_effort` | together.ai |
| `string-thinking` | `thinking: <effort字符串>` | 未知网关兜底 |

DSH **拒绝**以下两个值（需要 `chatTemplateKwargs`，schema 不暴露）：`chat-template` / `qwen-chat-template`。

> 警告：`thinkingFormat` 描述的是**网关的 wire 协议方言**，不是"网关背后接哪个模型"。DeepSeek 不等于 MiniMax。

### reasoningEfforts

键取自 `THINKING_LEVELS = { off, minimal, low, medium, high, xhigh, max }`，值是 wire spelling：

- `off:`（留空）→ "send nothing"（请求时不带该字段）
- `off: none` → 发送 `reasoning_effort: "none"`
- `low: low` → 透传
- `max: ultra` → 网关用 `ultra` 而非 `max` 时改名

## 路由级行为（简述）

完整 schema 在 `dsh-llm-pi-ai/lib/types/config.d.ts`。本技能只提示何时用：

- **`headers`** —— HTTP 头透传。**凭据禁止放在这里**（会被脱敏 `describe()` 原样返回）；凭据一律走 `apiKeyEnv`
- **`transport`** —— `"sse"` / `"websocket"` / `"websocket-cached"` / `"auto"`。provider 不支持则忽略
- **`cacheRetention`** —— `"none"` / `"short"` / `"long"`（默认 `"short"`）。影响 KV 缓存保留
- **`thinkingBudgets`** —— 按档位限制思考 token。`{ minimal?, low?, medium?, high? }` 各自 number。provider 不支持则忽略
- **`timeoutMs`** —— 整请求超时。**`streamIdleTimeoutMs`** —— stream 两次读之间最大空闲（默认 300000 = 5 分钟；超过 MAX_TIMER_DELAY_MS ≈ 24.8 天 schema 拒）。**`websocketConnectTimeoutMs`** —— WS 建连超时
- **`retryPolicy`** —— provider 自有重试意图：

```yaml
retryPolicy:
  mode: normal            # "normal"（默认；只重试 transient failure）或 "always"（每个失败都重试——慎用，会无限循环）
  maxRetries: 2           # normal 模式：首次请求后最多重试次数（默认 2）
  retryableCodes: [RATE_LIMIT, TIMEOUT]   # normal 模式：可重试的 stable failure code 清单
  backoff:
    initialDelayMs: 500   # 首次重试本地延迟（默认 500）
    maxDelayMs: 10000     # 本地最大延迟（默认 10000）
    jitterRatio: 0.1      # 对称随机抖动比例（默认 0.1）
```

> 旧字段 `maxRetries` / `maxRetryDelayMs`（顶级）已移除（schema 拒）。具体执行交给 `dsh-llm-retry` 插件。

## 配置模板

### 模板 A：anthropic-messages 手写路由

```yaml
llm-pi-ai:
  providers:
    cc-private:
      apiKeyEnv: MY_CC_KEY
      api: anthropic-messages
      baseURL: https://private.anthropic.example
      defaultInput: [text, image]      # 路由级 vision 兜底
      defaultContextWindow: 200000     # 路由级兜底
      models:
        - id: claude-3.5-sonnet
          name: Claude 3.5 Sonnet
          input: [text, image]         # 显式 vision
          maxTokens: 8192               # 显式声明 + 成为请求默认
        - id: claude-3-haiku
          name: Claude 3 Haiku
          input: [text]               # 显式 text-only（覆盖 defaultInput）
      # 不要写 compat（协议自带 thinking）
```

### 模板 B：openai-completions 手写路由（推荐写法）

```yaml
llm-pi-ai:
  providers:
    mm-vision-gw:
      apiKeyEnv: MM_VISION_KEY
      api: openai-completions
      baseURL: https://vision.example/v1
      compat:                          # 必写
        supportsReasoningEffort: true  # 必写
        # thinkingFormat 默认不写（pi-ai 按 baseURL 猜；错了再填）
      defaultInput: [text, image]      # 路由级 vision 兜底
      defaultContextWindow: 1048576    # 1M 兜底
      models:
        - id: mmv-pro
          name: MMV Pro
          reasoningEfforts:            # 必写, 5 档 + off
            off:
            low: low
            medium: medium
            high: high
            max: max
```

### 模板 C：修补内置 catalog（用 `modelOverrides`）

```yaml
llm-pi-ai:
  providers:
    openai-private:
      apiKeyEnv: MY_OPENAI_KEY
      baseURL: https://private.openai.example/v1
      modelOverrides:                 # 与 models[] 互斥（schema 直接报错）
        gpt-4.1:
          input: [text, image]         # 私有代理给 4.1 加 vision
          contextWindow: 1000000       # 1M 覆盖 catalog
        gpt-4o-mini:
          input: [text]                # 私有代理禁了 4o-mini 的 vision
          reasoningEfforts: false      # 私有代理让 4o-mini 不再推理
```

## 流程

### 0. 询问/确认输入（按需问）

最小集合：路由 id + 协议 + baseURL + apiKeyEnv。按场景加问：
- 加 vision → 哪些模型支持？网关实测过吗？（**违反 H9 让会话死循环**）
- 改上下文 → 目标值？网关实际支持吗？
- 改协议 → 旧协议下的 `compat` / `thinkingFormat` 还合法吗？

### 1. 读现状

打开 `~/.dsh/settings.yaml`，读 `llm-pi-ai.providers` 段：
- 路由 id 是否已存在？存在 → 修改；不存在 → 新增
- 已有协议 / 已有字段是什么？增量改时核对冲突

### 2. 写入（精确 edit）

- **新增路由** —— 在 `providers` 末行追加，锚"前一个路由的最后一行"
- **修改路由** —— 改对应字段。锚点选**前后都有、不会被改的稳定行**（如 `apiKeyEnv`、route 字段名），不要锚 `name` / `id` / `input` 这种会改的行
- **删除路由** —— 找到完整路由块，前后挨着锚定删除
- **同时备份** —— `cp settings.yaml settings.yaml.bak.<ts>`（settings.yaml 没有自动备份）

### 3. 自检清单

| 项 | 怎么验 |
|---|---|
| YAML 语法 | `node -e "const y=require('yaml');const d=y.parseDocument(require('fs').readFileSync(process.env.DSH_HOME+'/settings.yaml','utf8'));console.log(d.errors.length===0?'OK':d.errors.map(e=>e.message).join('\n'))"` |
| 字段名 | `baseURL`（非 `baseUrl`）/ `input`（非 `modalities`）/ `defaultContextWindow`（非 `default_context_window`）/ `modelOverrides`（非 `overrides`） |
| 字段对齐 | 2 空格步进；tab 全替；ASCII 半角空格 |
| `off:` key | 不能 `"off":` 或 `~~off`；裸 `off:` 才是"send nothing" |
| `reasoningEfforts` 完整 | 至少含 `off` + 至少 1 个 thinking 档（只 `off` schema 拒） |
| vision 字段 | `input` 元素只能是 `text` / `image`；拼写错（`images` / `Image`）schema 拒 |
| `defaultInput` 非空 | 空数组 schema 拒 |
| `models` 与 `modelOverrides` 互斥 | 同路由下并存 → schema 拒 |
| `thinkingFormat` ∈ 8 值 | `chat-template` / `qwen-chat-template` 等 schema 拒 |

### 4. 验证（可选但推荐）

- DSH 控制台应无 `settings-rejected` 报错；日志显示 `llm-pi-ai: route X registered`
- 选 Model/Reasoning 选择器：模型出现即生效；Effort 行 5 档出现 → reasoningEfforts + compat 正确；上传图片不报错 → vision 生效
- 实际发起一次对话 → 模型回答 → 路由可达

### 5. 回滚（失败怎么撤）

- schema reject（没存进去）→ 啥也不用做
- runtime 报错 → 反向 edit 删字段；或 `cp settings.yaml.bak.<ts> settings.yaml` 覆盖
- `agent-default-model` 指向新路由但路由挂了 → 临时改 `agent-default-model.provider` 回旧值

## 硬规则

| 编号 | 规则 |
|---|---|
| H1 | **Key 只走 env 名**。绝不写 key 裸值到 `apiKeyEnv` |
| H2 | **不擅自修改 `agent-default-model`** |
| H3 | **anthropic-messages 不写 `compat`**（协议自带 thinking） |
| H4 | **openai-completions 不写 `thinkingFormat` 当不确定**（默认 OpenAI 原生） |
| H5 | **不动用户已有路由**（除非用户明确"改 X"或"删 X"） |
| H6 | **精确 edit，不整段重写** |
| H7 | **不支持 reasoning 的模型不写 `reasoningEfforts`**（UI Effort 行不出现） |
| H8 | **vision 必须显式声明 image**（手写路由 + 第三方网关必写） |
| H9 | **未确认网关支持 vision 就不要声明 image**（多声明 = durable 死循环；少声明 = preflight 拒绝，更安全） |
| H10 | **`models` 与 `modelOverrides` 互斥** |
| H11 | **headers 不放凭据**（凭据一律走 `apiKeyEnv`） |
| H12 | **`maxTokens` 在 `models[]` 里**会成为请求默认**；catalog 来的不会 |

## 坑位

### 坑位 1：YAML 1.2 兼容下的特殊 key

`off` / `on` / `yes` / `no` 在 PyYAML（YAML 1.1）下解析为布尔，但 DSH 用 `eemeli/yaml`（YAML 1.2），这些字符串 key 都正常。验证 YAML 用 node + `yaml`（DSH 同款解析器），别用 Python。

### 坑位 2：缩进与全角空格

settings.yaml 用 2 空格步进，不要 tab。所有缩进 ASCII 半角空格（DSH `yaml` 包对全角空格不宽容）。

### 坑位 3：`baseURL` vs `baseUrl`

DSH schema 是 `baseURL`（全大写）。`baseUrl` 会被静默忽略 → 路由回退到 catalog 默认 baseURL。

### 坑位 4：`thinkingFormat` 不可猜

用户说"自建网关 / 不知道方言" → **绝不瞎填**。让它走默认 OpenAI 风格。

### 坑位 5：路由 id 与 skill name 重名

DSH skill name 是 kebab-case；provider route id 也最好是 kebab-case。两者不冲突。建议带 provider 后缀（如 `xianyu-minimax` 而不是 `minimax`——会和官方 `minimax-cn` 撞名规则）。

### 坑位 6：vision 模型错声明 image → 会话死循环

DSH 的 `input` 字段**信任**网关——不主动询问。声明 `[text, image]` 但网关实际只接受 text → 网关中途拒绝 → 消息已 durable 化 → 会话每次重试都重发同一张图 → **死循环**。所以**只在确认网关支持时才声明 `image`**。

### 坑位 7：DSH 仅 `text` + `image` 两种模态

`MODALITIES = { text: true, image: true }`。任何其它值（`audio` / `video` / `pdf`）schema 直接拒。

### 坑位 8：`maxTokens` 双义陷阱

`models[].maxTokens` 是**请求默认**；catalog.maxTokens 只是**能力声明**。错把 `maxTokens` 写小 → 任何长回复都被截；写大 → 浪费但无害。

### 坑位 9：`models` 与 `modelOverrides` 不能并存

- `models[]` 存在 + 任何 `modelOverrides` → "sets modelOverrides for X beside a models list"
- `modelOverrides` 在手写路由上 → "installed catalog does not describe this route"
- `modelOverrides` 的 key 不在 catalog → "modelOverrides names X, which the installed catalog does not describe"

**两种模式二选一**：
- "保留 catalog，改一个模型" → `modelOverrides`
- "全替换 catalog 或写新模型" → `models[]`

### 坑位 10：`api` 只接受 `supportedProtocols()` 的子集

DSH 比 pi-ai 的全集**窄**：
- ✅ `anthropic-messages` / `openai-completions` / `openai-responses`
- ❌ `bedrock`（要 SigV4）/ `vertex`（要 project + ADC）/ `azure-openai-responses`（要 api-version）/ `openai-codex`（OAuth）

这些协议的 catalog 路由仍可复用内置 provider，**只是不能手写 `api: bedrock`**。

### 坑位 11：headers 塞凭据 → 脱敏失效

`headers` 是纯字符串 dict，`describe()` 在脱敏时**只过 `apiKeyEnv`**，不扫 headers。`Authorization: Bearer abc` 在 `headers` 里**原样**返回给配置 UI。

### 坑位 12：旧字段 `maxRetries` / `maxRetryDelayMs` 已移除

❌ **已移除，schema 直接拒**：

```yaml
providers:
  my-route:
    maxRetries: 3          # ← 报错："maxRetries was removed"
    maxRetryDelayMs: 30000 # ← 报错："maxRetryDelayMs was removed"
```

✅ **改用 `retryPolicy`**（嵌套）：

```yaml
providers:
  my-route:
    retryPolicy:
      mode: normal
      maxRetries: 3
      backoff:
        maxDelayMs: 30000
```

完整报错信息："llm-pi-ai: provider \"X\" sets maxRetries or maxRetryDelayMs, which were removed; compose agent recovery with dsh-llm-retry"。

## 路由示例

### 例 1：闲鱼 MiniMax（OpenAI-completions · 已实战 · xianyu-minimax）

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
          contextWindow: 1000000        # 1M 上下文（猜测；网关实际支持多少以实测为准）
          maxTokens: 32768
          reasoningEfforts:
            off:
            low: low
            medium: medium
            high: high
            max: max
```

### 例 2：修补内置 OpenAI catalog 的 vision + 容量

```yaml
llm-pi-ai:
  providers:
    openai-private:
      apiKeyEnv: MY_OPENAI_KEY
      baseURL: https://private.openai.example/v1
      modelOverrides:
        gpt-4.1:
          input: [text, image]
          contextWindow: 1000000
        gpt-4o-mini:
          input: [text]
          reasoningEfforts: false
```

### 例 3：catalog 复用 + 自定义 HTTP 头 + 重试 + 缓存

```yaml
llm-pi-ai:
  providers:
    anthropic:
      apiKeyEnv: ANTHROPIC_API_KEY
      headers:                      # catalog 路由也允许 behavior 字段
        X-Trace-Source: harness
      cacheRetention: long
      timeoutMs: 600000
      retryPolicy:
        mode: normal
        maxRetries: 3
        retryableCodes: [RATE_LIMIT, TIMEOUT]
        backoff:
          initialDelayMs: 1000
          maxDelayMs: 30000
```

### 例 4：thinkingBudgets 限制思考 token + 长流空闲

```yaml
llm-pi-ai:
  providers:
    claude-private:
      apiKeyEnv: MY_CLAUDE_KEY
      api: anthropic-messages
      baseURL: https://private.anthropic.example
      thinkingBudgets:
        minimal: 512
        low: 1024
        medium: 4096
        high: 16384
      streamIdleTimeoutMs: 900000   # 15 分钟
      models:
        - id: claude-3.5-sonnet
          name: Claude 3.5 Sonnet
          input: [text, image]
```

## 自检 · 端到端

1. **YAML 合法**：`node -e "..."` 跑通
2. **DSH 接受**：控制台无 `settings-rejected`；reload 日志显示 `route X registered`
3. **UI 自检**：
   - 模型出现即生效
   - Effort 行 5 档出现 → `reasoningEfforts` + `compat.supportsReasoningEffort` 正确
   - 上传图片不报错 → `input: [text, image]` 或 `defaultInput` 生效
   - `read_image` 工具不被拒 → 走 `dsh-tool-fs` 的 image gate 正确

## 边界 · 与其他技能的边界

- **「修改 DSH 插件 / 主题」** → 不在本技能
- **「写新插件代码」** → 不在本技能
- **「OpenCode / Hermes / 别的 agent 系统的模型配置」** → 各有各的 skill
- **「修改 credentials.yaml / .env / 系统 env 变量」** → 引导用户单独完成；本技能只写 env 名
- **「把模型加到 awesome-dsh-plugin 市场」** → 走 `awesome-dsh-plugin-submit` 技能
- **「附件 store 部署 / image 上传后端」** → `dsh-attachment` 负责；本技能只声明模型能/不能收 image
- **「`read_image` 工具的内部实现」** → `dsh-tool-fs` 的活；本技能只确保 image gate 不拦下调用
- **「其它 DSH 插件（如 `dsh-vision`）的配置 / 运行行为」** → 不在本技能
- **「audio / video / pdf 等非 text+image 模态」** → DSH schema 不支持
- **「DSH retry 插件 `dsh-llm-retry` 的执行细节」** → 本技能只声明 `retryPolicy` 意图，具体执行由 `dsh-llm-retry` 处理