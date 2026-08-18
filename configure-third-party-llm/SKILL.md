---
name: configure-third-party-llm
description: 在 DSH（DeepSeek Harness）中向 `~/.dsh/settings.yaml` 的 `llm-pi-ai.providers.<route>` 段添加第三方 LLM 模型路由，Anthropic-messages / OpenAI-completions 两种协议都支持。提供协议、baseURL、API key（或 env 名），AI 自动填 `compat` / `thinkingFormat` / `reasoningEfforts` 等字段，保证 UI 的 Model/Reasoning 选择器正确显示 Effort 行。改 Key、改 URL、改协议都走这里。当用户说"配置 MiniMax 第三方模型 / 添加第三方模型 / 改 xianyu-minimax 的 Key / 换 minimax.chat 域名 / 让自定义模型显示思考等级 / 改 MiniMax-CN 的设置 / 第三方 LLM 接入 DSH / 闲鱼 MiniMax 网关更换"等时使用。
---

# configure-third-party-llm

> 把一个第三方 LLM 网关（或厂商）作为 provider 路由，写入 DSH 的 `~/.dsh/settings.yaml`。
> 覆盖 Anthropic-messages 与 OpenAI-completions 两种线协议；改 Key、改 baseURL、改协议都走这里。
> 实战：以 `xianyu-minimax`（OpenAI-completions 走 `minnimax.chat`）为蓝本；可迁移到任何厂商。

## 30 秒边界

**管**：
- 在 `~/.dsh/settings.yaml` 的 `llm-pi-ai.providers` 下新增 / 修改 / 删除一个 provider 路由
- 两个线协议的配置：`anthropic-messages` 与 `openai-completions`
- 编写 `compat` / `thinkingFormat` / `reasoningEfforts` 等让 UI 显示 Effort 行所需的元数据
- Key 切换（env 名字 or 新值）、baseURL 切换、协议切换
- YAML 写入合法性自检（DSH 用 `eemeli/yaml` v2，YAML 1.2 模式）

**不管**：
- 不改 `~/.dsh/credentials.yaml`（DSH 的 key 存储；本技能只写 env var 名字）
- 不动 `agent-default-model`（修改路由后用户应人工选取默认模型；本技能不擅自改默认）
- 不创建任何 DSH 插件或 plugin 包
- 不管 WSL Hermes / OpenCode / 别的 agent 系统的模型配置（仅 DSH）
- 不管 DSH 自己的官方 MiniMax-CN / Anthropic / OpenAI 等「内置」catalog
  （那些由 `@earendil-works/pi-ai` 内置 JSON 提供；本技能不重写它们）

## 触发词表

| 核心触发词 | 变体 | 必备输入 |
|---|---|---|
| 配置第三方 LLM | "在 DSH 加一个 MiniMax"、"添加一个第三方模型"、"接入 X 模型" | 协议 / URL / Key（或 env 名） |
| 改 Key | "换 key"、"更新 API key"、"换另一个 env" | 路由 id，新 env 名或新值 |
| 改 URL / 域名 | "minimax.chat 换域名"、"换 baseURL"、"网关搬迁" | 路由 id，新 baseURL |
| 换协议 | "改成 anthropic 形式"、"改成 openai-completions" | 路由 id，目标协议 |
| 修 Effort 行 | "思考等级不见了"、"UI 不显示 Effort"、"reasoningEfforts 没出现" | 路由 id（+协议） |
| 删路由 | "删掉 xianyu-minimax"、"移除某个第三方模型" | 路由 id |

## 必备输入（三件套）

| 字段 | 含义 | 例 |
|---|---|---|
| **路由 id** (kebab-case) | `llm-pi-ai.providers.<id>` 这个 key；唯一 | `xianyu-minimax` |
| **协议 (api)** | `anthropic-messages` 或 `openai-completions` | `openai-completions` |
| **baseURL** | 网关端点（不要以 `/` 结尾） | `https://minnimax.chat/v1` |
| **apiKeyEnv** | DSH 解析的 env 变量名（值在 `credentials.yaml`） | `XIANYU_MINIMAX_API_KEY` |

可选输入：模型 list（不传则继承 pi-ai 内置 catalog；harness home 路由在 DSH 端仅起到路由改写作用）

## 协议分支决策树

```
协议 = anthropic-messages
  → 协议本身就定义 thinking；pi-ai baseURL 反推即认
  → 字段：仅 apiKeyEnv / api / baseURL / models 即可
  → UI 上的 Effort 行：自动出现（来自模型 catalog）

协议 = openai-completions
  → 需要显式声明 compat 与 reasoningEfforts
  → thinkingFormat 默认【不写】（→ 走 pi-ai 默认 OpenAI 风格 `reasoning_effort` 字段）
  → 必写：compat.supportsReasoningEffort: true
  → 必写：每个模型 entry 的 reasoningEfforts
  → 可选：thinkingFormat（仅当网关要求特定方言时；详见 §坑位 4）
```

## 配置模板

### 分支 A：Anthropic-messages（MiniMax-CN 风格）

```yaml
llm-pi-ai:
  providers:
    <route-id>:                          # kebab-case, e.g. minimax-cn-private
      apiKeyEnv: <ENV_VAR_NAME>          # 字符串，env 名,非裸 key
      api: anthropic-messages
      baseURL: https://your-gateway.example/anthropic   # 不要 / 结尾
      # 可选 models: 若不写→继承 pi-ai 内置 catalog(provider 同名时)
      models:
        - id: MiniMax-M3
          name: My MiniMax M3
          # 不需要 reasoningEfforts: 协议自带 thinking
```

### 分支 B：OpenAI-completions（Minimax 闲鱼 / 第三方代理风格；推荐写法）

```yaml
llm-pi-ai:
  providers:
    <route-id>:                          # e.g. xianyu-minimax
      apiKeyEnv: <ENV_VAR_NAME>
      api: openai-completions
      baseURL: https://your-gateway.example/v1
      compat:                            # 必写
        supportsReasoningEffort: true    # 必写 → 启用 OpenAI 风格 reasoning_effort
      models:
        - id: <model-id-on-gateway>      # e.g. MiniMax-M3
          name: <ui-display-name>        # e.g. MiniMax-M3-59.9
          reasoningEfforts:              # 必写,5 个 level
            off:                         # off: 留空 = "send nothing"
            low: low
            medium: medium
            high: high
            max: max
```

> **为什么 `off:` 留空合法**：DSH 用 `eemeli/yaml` v2.x（YAML 1.2 模式），裸 `off:` 解析为字符串 `"off"` + 值 `null`。这是 `catalog.d.ts` 注释第 67-73 行规定的："`off` alone may leave its value empty — 'supported, send nothing'"。不要把 `off` 加引号（`"off":`）也没必要，纯属多余。
>
> **thinkingFormat 默认不写**——只有当网关明确要求非 OpenAI 风格（`thinking={type,effort}` / `reasoning={effort}` / `enable_thinking` 开关 / 自由字符串）时才需要。下面是全部可选值（来自 `pi-ai` 源码）：
>
> | 值 | 实际发送 | 谁用 |
> |---|---|---|
> | `zai` | `thinking: {type:"enabled"}` + `reasoning_effort` | GLM 系列 |
> | `qwen` | `enable_thinking: <bool>` | 千问系列 |
> | `deepseek` | `thinking: {type:"enabled"}` + `reasoning_effort` | DeepSeek V3/V4 openai-completions 方言 |
> | `openrouter` | `reasoning: {effort: ...}` 嵌套 | OpenRouter |
> | `ant-ling` | `reasoning: {effort: ...}` 嵌套 | ant-ling |
> | `together` | `reasoning: {enabled:...}` + `reasoning_effort` | together.ai |
> | `string-thinking` | `thinking: <effort字符串>` | 未知网关的兜底 |
>
> 警告：`thinkingFormat` 描述的是**网关的 wire 协议方言**，不是"网关背后接哪个模型"。DeepSeek 不等于 MiniMax。

## 流程

### 0. 询问/确认输入（三件套）

- 路由 id（kebab-case）
- 协议（anthropic-messages 或 openai-completions）
- baseURL
- apiKeyEnv（**只收 env 名**，不要 key 裸值）

如：用户说"接入 minnimax.chat 的 M3M3 模型"——反问路由 id 是否已有/是否复用。

### 1. 读现状

打开 `~/.dsh/settings.yaml`，读 `llm-pi-ai.providers` 段：
- 路由 id 是否已存在？存在 → 走"修改"，不存在 → 走"新增"
- 已有协议是哪个？换协议要提示用户并征得确认（这是变更行为）

### 2. 写入（用 edit 工具精确替换）

**新增路由**——在 `llm-pi-ai.providers` 末行追加：
- 用 `edit` 工具，把 `providers:` 段的最后一行作为锚点，在它后面插入新块
- 不要重写整段——精确最小变更

**修改路由**——改对应字段，不动其他字段：
- 改 `baseURL` / `apiKeyEnv` 等标量：单字段替换
- 改协议（api）：同时检查模型 entries 是否仍合法；anthropic → openai 时必须补 `compat` + `reasoningEfforts`，反向简化

**删除路由**：
- 找到完整路由块，前后挨着锚定删除
- 提示用户：默认模型若指向本路由也会失效

### 3. 自检清单（写入后必跑）

| 项 | 怎么验 |
|---|---|
| YAML 语法 | node `yaml.parseDocument()` 解析不报错；`doc.errors` 为空 |
| 字段名 | 严格匹配 §配置模板；不接受拼写变体（`baseUrl` ❌ / `baseURL` ✓） |
| 字段对齐 | `compat` / `models` 缩进与模板一致（2 空格步进） |
| `off:` key | 不能写成 `"off"`，也不能写成 `~~off`；裸 `off:` 是正解 |
| `reasoningEfforts` 完整 | off / low / medium / high / max 五档，缺一不显示对应 Effort 选项 |
| 路由 id kebab-case | 正则：`/^[a-z0-9]+(?:-[a-z0-9]+)*$/`（与 DSH skill name 同规则） |
| 与已有路由无冲突 | 当前 path `llm-pi-ai.providers.<id>` 不应已有同名 |
| 与官方路由兼容 | 不与 `minimax-cn` / `openai` / `anthropic` 等已内置的路由 id 重复 |

### 4. 告诉用户去看什么

- settings.yaml watcher 会自动 reload，无需重启
- 切到 Model/Reasoning 选择器：模型出现即生效；Effort 行（low/medium/high/max）只在 openai-completions 走完整配置后出现
- 实际抽 1 个问题测一次，再来收敛观察

## 硬规则

| 编号 | 规则 |
|---|---|
| H1 | **Key 只走 env 名**。本技能绝不写入 key 裸值；把 env 名写到 `apiKeyEnv`，由用户在 `credentials.yaml` 单独维护 |
| H2 | **不擅自修改 `agent-default-model`**。改了路由不影响默认模型；用户后续手动选 |
| H3 | **Anthropic-messages 协议不写 `compat`**。该协议 thinking 由协议本身定义；多余 `compat` 反而冲突 |
| H4 | **OpenAI-completions 协议不写 `thinkingFormat` 当不确定**。默认走 OpenAI 原生 `reasoning_effort`（最通用）。仅当你已经知道网关方言时才填 |
| H5 | **不动用户已有路由**。除非用户明确"改 X"或"删 X"。任何"清理 / 收敛 / 合并"先问 |
| H6 | **精确 edit，不整段重写**。`settings.yaml` 是高敏感文件；写错一位（缩进或拼写）会破坏整个文件 |
| H7 | **触发词必须自带触发面**。该路由如果不支持 reasoning（如纯 embedding 模型），不写 `reasoningEfforts`；UI Effort 行会不出现 |

## 坑位

### 坑位 1：YAML 1.2 兼容下的特殊 key

`off` / `on` / `yes` / `no` 在 PyYAML（YAML 1.1）下被解析为布尔，但 DSH 用的是 `eemeli/yaml`（YAML 1.2），这些字符串 key 都正常。**别因为在 Python 里看到 `"false": null` 就以为被改成布尔了**——DSH 那边认的是字符串 `"off"`。Python 的 PYTHON_YAML_AS_YAML_1_1 默认是 1.1，所以验证 YAML 应该用 node + `yaml`（即 DSH 同款解析器）：

```js
const yaml = require('yaml');
const d = yaml.parseDocument(fs.readFileSync(settingsPath, 'utf8'));
if (d.errors.length) throw new Error(d.errors.map(e => e.message).join('\n'));
```

### 坑位 2：缩进与全角空格

settings.yaml 用 2 空格步进，不要用 tab。所有缩进用 ASCII 半角空格（DSH `yaml` 包对全角空格不会宽容）。复制我给你的模板，看清"全角空格"陷阱。

### 坑位 3：`baseURL` vs `baseUrl`

DSH schema 是 `baseURL`（全大写 URL 后缀）——一字母大小写错误会被静默忽略，导致**路由回退到 catalog 默认 baseURL**（也就是 `anthropic-messages` 协议 → `https://api.minimaxi.com/anthropic`）。所以你以为"换了 baseURL"实际没换。

### 坑位 4：`thinkingFormat` 不可猜

如果用户说"我的网关是自建的 / 我不知道方言"，**绝不要瞎填**。让它走 §分支 B 默认（不填）→ OpenAI 风格 `reasoning_effort` 字段。

### 坑位 5：路由 id 与 skill name 重名

DSH skill name 是 kebab-case；DSH provider route id 也最好是 kebab-case。两者可能重名，但不冲突（一个 `skills/`，一个 `llm-pi-ai.providers/`）。但**给 route id 命名时建议带 provider 后缀**（如 `xianyu-minimax` 而不是 `minimax`）——后者会和官方 `minimax-cn` 撞名规则。

### 坑位 6：DSH 设置层只写 overrides

路径语义是 `llm-pi-ai.providers.<route>`。**整张 `llm-pi-ai.providers` 段是从 pi-ai catalog + profile 合并而来**（见 `dsh-llm-pi-ai/lib/types/config.d.ts` "Validates profiles and return a detached route-keyed map"）。改一段只改对应的字段，不要凭空写一个"完整新表"。

### 坑位 7：apiKey 复制粘贴陷阱

对方把"实际值"粘贴到对话里说："这是我的 key" → 你**不能**直接 `apiKey: gw-xxx`（会裸值进 git / settings.yaml）。提示用户改用 env：
- 让用户在 `credentials.yaml` 设值
- 本技能只引用 env 名（如 `XIANYU_MINIMAX_API_KEY`），不粘裸值
- 与 DSH 的 `credentials-set` 工具协同（用户侧负责把真实 key 写入 keychain）

### 坑位 8：`minimax-cn` / `minimax` 官方内置

`minimax-cn` 与 `minimax` 是 pi-ai **内置**的两个 provider id。`apiKeyEnv` 缺省即可让 router 自动走它们，**不需要在本技能里重新声明**。本技能的应用范围是"pi-ai 没听过的网关 / 自建代理 / 改 baseURL"。

### 坑位 9：删路由后默认模型失效

如果删除的路由正好是 `agent-default-model.provider`，下次启动会报 `Provider is not configured`。删之前先查这个引用。

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

### 例 2：自建 MiniMax 兼容代理（OpenAI-completions · thinkingFormat: deepseek 错误的反例）

```yaml
llm-pi-ai:
  providers:
    my-mm-proxy:
      apiKeyEnv: MY_MM_API_KEY
      api: openai-completions
      baseURL: https://my-mirror.example/v1
      compat:
        supportsReasoningEffort: true
        # ❌ 不要填 thinkingFormat: deepseek ← 这是 DeepSeek 方言, 不是 MiniMax
      models:
        - id: MiniMax-M3
          name: My MiniMax M3
          reasoningEfforts:
            off:
            low: low
            medium: medium
            high: high
            max: max
```

### 例 3：MiniMax 官方 anthropic-messages 私有反代（Anthropic-messages）

```yaml
llm-pi-ai:
  providers:
    minimax-cn-private:
      apiKeyEnv: MY_PRIVATE_MM_KEY
      api: anthropic-messages
      baseURL: https://private.minimaxi.example/anthropic
      models:
        - id: MiniMax-M3
          name: MiniMax M3 (private)
```

## 自检 · 端到端

写完后跑这三步以确认成功：

1. **YAML 结构合法**：

   ```js
   const yaml = require('yaml');
   const d = yaml.parseDocument(fs.readFileSync(`${process.env.DSH_HOME}/settings.yaml`, 'utf8'));
   console.log(d.errors.length === 0 ? 'OK' : d.errors);
   ```

2. **UI Effor 行出现了**：打开 DSH 的 Model/Reasoning 选择器，选这个路由对应模型 → 看 Effort 行 5 个选项是否都在
3. **实际推理可用**：发起一次对话，检验 `reasoning_effort` 被正确发出（可在网关侧日志确认）

## 边界 · 与其他技能的边界

- **「修改 DSH 插件 / 主题」** → 不在本技能
- **「写新插件代码」** → 不在本技能
- **「OpenCode / Hermes / 别的 agent 系统的模型配置」** → 各有各的 skill；本技能只看 DSH
- **「修改 credentials.yaml / .env / 系统 env 变量」** → 在本技能写完路由后，**引导用户单独完成**；本技能不越界
- **「把模型加到 awesome-dsh-plugin 市场」** → 走 `awesome-dsh-plugin-submit` 技能，与本技能正交
