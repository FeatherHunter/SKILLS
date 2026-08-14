# DeepSeek Harness（DSH）插件体系调研

> 调研日期：2026-08-13
> 一手来源（双路）：
> 1. 本地安装包 `@deepseek-ai/dsh` v0.1.0-rc.6 及其全部模块源码/官方文档（npx 缓存 `node_modules/@deepseek-ai/*`，含官方内置「创造模式」预设自带的两份插件开发技能文档）；
> 2. GitHub 仓库 `deepseek-ai/deepseek-harness`（默认分支 **master**）源码快照与官方文档（raw.githubusercontent.com / codeload 抓取），以及 `dsh-plugin` topic / `dsh-external` 社区的一手插件仓库。
>
> 结论性质：**DSH 中「插件」= Cordis 插件，且"一切皆插件"是架构第一原则**。官方 README 原文："It uses an architecture where **everything is a plugin**, and is powered by [Cordis](https://github.com/cordiverse/cordis)". 整个 DSH 没有特权内核——模型适配器、工具注册表、会话日志、agent loop 本身都是插件（"There is no privileged core to patch"），扩展 DSH 的唯一方式就是挂上另一个插件。

---

## 1. 项目是什么

DeepSeek Harness（仓库 `deepseek-ai/deepseek-harness`，npm 包 `@deepseek-ai/dsh`）是 DeepSeek 官方的 **AI 代理（agent）运行框架/平台**：

- `dsh --profile web` 启动本地 Web GUI；`dsh --profile headless "job"` 跑无头会话；`dsh web` 是 web profile 的别名。
- 支持多模型提供方（deepseek-official、pi-ai 等），含 agent 循环、子代理/工作流、目标（goal）机制、计划模式、技能（skill）系统、文件沙箱与审批栈、会话持久化等完整平台能力。
- **技术底座是 Cordis 插件框架**（Koishi 生态的依赖注入容器，官方在仓库内 vendor 了一份）。所有功能模块（`@deepseek-ai/dsh-*` 一百多个包）都是 Cordis 插件，靠 `cordis.yml` 组合清单装配。
- **状态声明**：官方 README 明示项目处于 *developer preview*（开发者预览），快速迭代中，"**THERE WILL BE COMPATIBILITY-BREAKING CHANGES**"（必有破坏性变更）；仓库根 AGENTS.md 补充：首个 tag 发布前可随意改名/重组装，SQLite/SESSION_FORMAT_VERSION 存储格式**无兼容承诺**。
- 反馈渠道走 GitHub **Discussions**（仓库未开放 Issues 作为反馈渠道）；第三方插件仓库打 `dsh-plugin` topic 便于被发现。

## 2. 「插件」的确切含义

### 2.1 定义：插件是一个导出 apply 的模块

官方用户教程最简定义：

> 「在 Harness 中，插件是一个导出 `apply` 函数的 TypeScript 模块。框架在加载时调用 `apply`，传入一个 `ctx`（上下文对象），你通过 `ctx` 注册能力。」「通过 `ctx` 注册的任何东西——事件监听、工具、定时器——在插件卸载时都会被自动清理。」

Cordis primer 的完整定义：

> "A plugin is a object that implements Service. It can be a function with optional `inject` and `apply(ctx)` fields, or a `Service` subclass whose lifecycle Cordis mounts into the current context."

官方教程给出三种书写形态（`docs/cordis-tutorial/01-first-plugin.md`）：

1. **函数插件**：named-export `name` / `inject` / `Config` / `apply(ctx)`（**约定：函数插件不得有 default export**，否则 Loader 会丢弃其命名空间）；
2. **对象插件**：`{ name, apply }`；
3. **类插件**：`Service` 子类（`super(ctx, 'myService')`），用于对外提供服务。

最小插件（官方原文）：

```ts
import type { Context } from '@deepseek-ai/cordis'
export const name = 'hello-plugin'
export function apply(ctx: Context) {
  console.log('[hello-plugin] plugin loaded!')
}
```

### 2.2 与 skill / hook / 内置能力的关系

- **插件 vs skill**：插件是**运行时代码**（挂载即执行 `apply` 注册能力）；skill 是**模型可选的指令数据**（Markdown 正文，`SkillDefinition.content: string`），本身不执行，模型经 `skill({ name })` 工具按需注入。skill 在插件机制上的实现 = section + 工具注册 + `agent.inject()`。
- **插件 vs hook**：hook 不是独立机制，而是**一类插件**——`dsh-hooks-claude-code` / `dsh-hooks-codex` 把 Claude Code/Codex 的 `hooks.json` shell 钩子协议**桥接**到 DSH 的类型化拦截点（`agent/session-start`、`agent/pre-step`、`tools/pre-execute` 等）。「原生钩子」只是这些扩展点上的普通 Cordis 插件。
- **插件 vs 内置能力**：没有特权内核。`dsh-base` bundle 只是「第一层插件组合」；模型适配器、工具注册表、会话日志、agent loop 全部可被插件替换。唯一约束：**改 loop 本体必须更新架构文档**（"Plugins, not loop changes"）。

### 2.3 运行位置：Host 半 / Client 半 / 组合层

**按运行位置分两类**（官方核心分类）：

| | Host 半（后端 Node） | Client 半（浏览器） |
|---|---|---|
| 运行位置 | DSH 进程内，`node:vm` 沙箱求值（动态插件）或直接加载（静态插件） | 浏览器端 bundle，经 `window.__DSH_BOOT__` 引导 |
| 接入条件 | 常规 npm 包 | `package.json` 声明 `dsh.client`（`platform: 'web'`、可选 `inject` 边、可选 `immediately`），`exports["./client"]` 导出构建好的 bundle（client 包 `extends tsconfig.base.client.json`） |
| 典型能力 | 文件/命令/进程/网络、注册模型工具、会话数据、生命周期事件 | 插槽 UI 注入、主题、会话数据 props、React 渲染 |

**按组合归属分两个平面**（官方 `editing-cordis-compositions` 技能）：

- **HOST 组合**：进程级单例。注册表（tools、agents、sessions 等）、跨会话共享物（持久化、设置、凭据、遥测）、沙箱与审批栈、模型路由、子代理注册表及其后端。
- **AGENT 预设**：每个会话一份，随会话挂载/卸载。会话向注册表贡献的工具插件、persona、提示词区段、压缩策略。
- 规则：**发布服务（provide）的插件不能裸放在预设里**（会撞进程全局 realm，第二个会话挂载即冲突），必须用 `group + isolate` 包进私有 realm，且该服务的消费者也要在同一 realm 内。

### 2.4 三种插件形态（分发/生命周期维度）

| 形态 | 存放/运行位置 | 生命周期 | 典型用途 |
|---|---|---|---|
| **静态插件（npm 包）** | 装进 profile 的 `node_modules`，在 `cordis.yml` / `cordis.patch.yml` 里声明为插件行 | 持久，随 profile 启动加载 | 正式发布的工具、服务、UI 模块；官方 100+ 个 `dsh-*` 模块全是这种 |
| **动态插件（运行时）** | DSH 进程内存（host 半）+ 每个打开的浏览器页面（client 半） | 进程级临时，`cordis_stop`/`cordis_undefine`/重启后消失 | AI 在会话里即时写的试验性插件：注册临时工具、注入 UI、改主题 |
| **Agent 预设（composition）** | `${DSH_HOME}/.agent-presets/<id>/agent.cordis.yml` | 持久 | 给"一个会话"定制整套插件组合（工具集+人格+提示词），本身也是插件行清单 |

### 2.5 装配机制（bundle 层叠 + patch 行）

- 每个 profile 目录含 `package.json` + 清单 `dsh.profile`（记录有序 `bundles` 列表）+ 用户 patch 层 `cordis.patch.yml`。
- **组合包（bundle）**：npm 包在 `package.json` 声明 `dsh.bundle.patch: ./cordis.patch.yml` 即为组合包——安装后自动进入 profile 层叠栈，其 patch 里的插件行被插入配置树（`dsh-base` 就是例子：一个 patch 插入 timer/hmr/llm/session/agent/jobs 等几十行）。
- 配置层顺序：空根 → 各 bundle 的 patch → profile 的 `cordis.patch.yml` → home 级 `$DSH_HOME/cordis.patch.yml` → `--patch` 覆盖层。**按行 id 定位，后写覆盖先写，整行 config 替换而非深合并**。
- **加载生命周期**：`PENDING → LOADING → ACTIVE`（PENDING 等待 `inject` 依赖就绪；FAILED = apply 抛异常）；`ACTIVE → UNLOADING → DISPOSED`（卸载自动撤销全部注册，dispose 递归卸载子插件）。每个注册都是 `ctx.effect`/`ctx.on`，因此**插件热重载（HMR）直接生效**。
- 安装命令：`dsh plugin --profile <name> <pnpm args...>`——薄的 pnpm 转发器（add/remove/why/update 都可用），成功后按"已安装状态"对账 `dsh.profile.bundles`：解析到带 `dsh.bundle` 声明的依赖自动入栈，被移除或失去声明的自动出栈；纯依赖（无 bundle 声明）会打警告。
- Web GUI 里有「设置 → 插件」管理面板：`host/plugin-inventory` 提供 Loader 树的只读投影（entry id、模块说明符、启用状态、Fiber 相位）。

## 3. 插件能做什么（能力清单）

### 3.1 官方「功能 → 插件机制」映射表（extension-cookbook，节选）

| 产品功能 | 插件机制 |
|---|---|
| 钩子系统（用户级+项目级） | `agent/session-start`、`agent/pre-step`、`agent/request`、`tools/pre-execute`、`tools/post-execute`、`agent/turn-stopping` 监听器；`dsh-hooks-claude-code`/`dsh-hooks-codex` 桥接 |
| 内置工具 | `ctx.tools.register()`；schema 自动流入装配（`dsh-tool-*` 系列是已交付示例） |
| 工具策略（允许/拒绝/询问/超时/重试/指标） | `tools/pre-execute`、`ctx.tools.guard()`、`tools/execute`、`tools/post-execute`、`tools/result` |
| 子进程沙箱 | `ctx.sandbox` 后端（`dsh-bash-sandbox`） |
| 权限系统 / AskUserQuestion | `tools/pre-execute` 返回 `ask` + `ctx.approval` |
| subagent 委派 | `ctx.subagents` 提供方注册表 |
| MCP | 每服务器一个插件：发现工具 → `ctx.tools.register()` |
| skill / 记忆 | section 提供方 + 工具；`agent.inject()` 注入 |
| 定时任务（cron） | 插件注册调度工具，定时器触发 → `followup(...)` / `inject()` |
| UI（GUI / CLI） | 监听 `session/event`；输入 → `followup()` |
| Web Chat 业务节点 | 注册 `ConversationNodeDefinition` + keyed renderer |
| 模型适配器 | `registerAdapter` 注册 `LlmAdapter` 子类（`dsh-llm-deepseek`、`dsh-llm-pi-ai`） |
| 插件热重载 | 每个注册是 `ctx.effect` → HMR 直接生效 |

### 3.2 Host 侧明细

| 能力 | 说明 |
|---|---|
| 文件 / 命令 / 进程 / 网络 | 通过 `fs`、`bash`/`pwsh`、`subprocess`、`pty`、`web` 等服务 |
| Agent、会话数据、主机生命周期 | 通过相关 Service + 事件（`Event.listEvents`） |
| **注册动态模型工具** | `harness` 注册"下一步模型就能调用"的工具（`harness.defineTool` + `harness.registerTool`），JSON 参数/返回值，随插件卸载自动移除 |
| **客户端→主机 RPC** | `harness.handle(method, handler)`（host）↔ `host.call(method, args)`（client），包内私有 JSON-RPC，只传可无损序列化的 JSON |
| 事件 | `ctx.on('some/event', ...)`；waterfall 事件监听器必须调用并返回 `next()` |
| 服务 | `ctx.get(name)` 可选依赖；`inject: ['x']` 硬依赖（Guard 拒绝未声明访问） |
| 定时器 | `timer` 服务：`ctx.timeout` / `ctx.interval`（须声明 `inject: ['timer']`） |
| 副作用管理 | `ctx.effect(() => disposer)`；一切贡献在插件 stop/update/remove 时自动清理 |

### 3.3 Client 侧明细（浏览器 UI）

| 能力 | 说明 |
|---|---|
| **插槽（Slot）UI 注入** | `slots.register({ name, id/key }, (props) => ReactElement)`；官方列举槽位：设置页（`settings.section` / `settings.general.item`）、侧边栏（含 `sidebar.footer.action` 小动作）、输入区、浮层（`shell.overlay`，toast/状态条/全局浮层）、**工具调用卡片**（`tool.call.toolview`，按工具名 key）、会话尾部（`conversation.chat.turnTail`）、`cordis_run` 面板（`tool.view.cordis`，key `'self'`） |
| **主题** | `theme` 服务查询/覆盖主题 token（亮/暗两套值），返回 disposer；局部样式用 `styles.insert(css)` 并优先用主题 CSS 变量 |
| 会话/页面数据 | 会话作用域槽位通过标准 props 提供 `useSession`/`useSessions`/`useWorkspaces`/`useProjection` 等 |
| React 渲染 | 仅 `React.createElement`（动态插件无 JSX；静态插件正常 TSX） |
| 事件/定时器 | 与 host 相同的 `ctx.on`、`timer` 服务 |

### 3.4 官方最小可运行示例——权限门禁钩子插件

```ts
import type { Context } from '@deepseek-ai/cordis'
import type { PreToolDecision, ToolExecution } from '@deepseek-ai/dsh-tools'

export const name = 'permission-gate'

export function apply(ctx: Context) {
  ctx.on('tools/pre-execute', async (exec, next): Promise<PreToolDecision> => {
    if (!(await isAllowed(exec))) {
      return { kind: 'deny', reason: 'Denied by policy.' }
    }
    return next()
  })
}
```

## 4. 官方预置模块与示例（插件的实证）

### 4.1 模块全景（本地 rc.6 装了一百多个 `@deepseek-ai/*` 模块，摘选）

- **基础/框架**：`dsh-base`（核心 bundle）、`dsh-app-boot`、`cordis-plugin-loader/hmr/timer/group/include`
- **Agent 循环**：`dsh-agent`、`dsh-agent-loop`、`dsh-agent-presets`、`dsh-agent-instructions`、`dsh-persona`、`dsh-system-prompt`
- **模型/LLM**：`dsh-llm`、`dsh-llm-deepseek`、`dsh-llm-pi-ai`、`dsh-llm-retry`、`dsh-agent-default-model`
- **模型工具**：`dsh-tool-bash/pwsh/fs/fs-search/subagent/subagent-control/subagent-report/workflow/ralph/ask-user/todo/web/goal/jobs/skill/cordis` 等
- **会话/持久化**：`dsh-session*`（persistence-jsonl、projection、query-sqlite、telemetry、title、stats…）、`dsh-settings-file`、`dsh-storage-*`、`dsh-spill-*`
- **沙箱/审批**：`dsh-fs-sandbox`、`dsh-fs-observation-policy`、`dsh-pwsh-sandbox`、`dsh-bash-sandbox`、`dsh-sandbox-windows-acl`、`dsh-user-approval`、`dsh-permission-presets`
- **客户端 UI**：`dsh-client-ui-*` 三十余个（conversation、sidebar、settings、subagent、workflow-run、goal、jobs、slots、theme、trajectory…）、`dsh-client-ui-cordis`
- **运行器**：`dsh-cordis-host-runner`（vm 沙箱跑 host 半）、`dsh-cordis-client-runner`（浏览器跑 client 半）
- **部署形态**：`dsh-web-app`、`dsh-web-frontend`、`dsh-headless`、`dsh-terminal`、`dsh-cmdline`

### 4.2 examples/ 目录（可运行的插件树组合，非独立插件仓库）

| 示例 | 一句话说明 |
|---|---|
| mcp-memory | 通过通用 MCP 客户端连接受支持第三方记忆服务器的可选 overlay |
| headless-agent | 非交互式 agent——接受任务并运行，输出机器可读或人类可读结果 |
| jsonrpc-agent | 由 Python SDK 与 JSON-RPC 驱动的无人值守编码 agent |
| web-cordis | 能检查并更改内存中 Cordis 插件树的自指 agent（演示模型书写/挂载/卸载动态插件） |
| web-schedule | 持久、仅限 Session 内提醒的可选 Web overlay（`schedule_create/list/delete`） |
| acp-agent | 面向程序化客户端的 ACP（Agent Client Protocol）自动化服务器，支持会话、权限与取消 |

### 4.3 官方 MCP 桥接示例

每个 MCP server 一个插件实例（`name: '@deepseek-ai/dsh-mcp-client'` + config：stdio 或 streamable-http），远端工具以 `mcp__<serverName>__<rawName>` 注册进 `ctx.tools`。注意官方默认**不启用任何 MCP server**：每个 server 命令都是"agent 沙箱之外的可信可执行代码"。

## 5. 开发路径：三条路

### 路径 A：写正式插件（npm 包，可分发）

官方发布教程的目录结构：

```
hello-plugin/
├── package.json       # 声明 "dsh": { "bundle": { "patch": "./cordis.patch.yml" } }
├── cordis.patch.yml   # - insert: - id: hello / name: dsh-hello-plugin
└── index.js           # export const name / export function apply
```

- 安装：`dsh plugin --profile demo add ./hello-plugin`（profile 首次使用自动初始化，`@deepseek-ai/dsh-base` 成为第一个组合包）；卸载 `dsh plugin --profile demo remove dsh-hello-plugin`。
- Git 安装 `dsh plugin --profile demo add github:you/hello-plugin` 拉的是**源码**，需要作者的 `prepare` 脚本 + 用户在 profile 的 `pnpm-workspace.yaml` 显式 `allowBuilds` 授权（pnpm ≥10 默认拒绝 git 依赖的 prepare 脚本；**该授权等于允许该包代码在你机器上执行，且不在 agent 沙箱之内**——官方文档要求只对可信包授权并锁定 commit）。发布 npm 或交付 tarball（`pnpm pack`）则无需构建授权。
- 仓库内包目录结构：`packages/<group>/<pkg>/`，含 `package.json`（`@deepseek-ai/cordis` 在 peerDependencies + devDependencies）、`tsconfig.json`（client 包用 `tsconfig.base.client.json`）、`src/index.ts`、`README.md`（须含 Service API / 事件 / 扩展点 / Model Experience / Known Limitations 章节）。
- 文档配套：`docs/cookbook/adding-a-tool.md`（greet 工具示例）、`adding-an-llm-adapter.md`、`adding-a-conversation-node.md`（UI 业务节点）、`adding-a-vendored-package.md`（vendor 上游 Cordis 包）。

### 路径 B：动态开发（AI 即时创作，官方 cordis「创造模式」预设）

- 会话切到 **cordis 预设** → `cordis_inspect_list/query`（查当前进程真实的服务/事件/工具/槽位/主题签名）→ `cordis_define` 提交 `code.host` + `code.client` 两半 JS → 用户预览代码并在浏览器批准 → `cordis_run` 激活 → `cordis_inspect_self` 看诊断 / `cordis_stop` / `cordis_undefine`。
- 动态包**不写插件文件、不装包、不改 cordis.yml、不跨重启持久**；要保留成果须让 agent 用常规开发流程落成普通插件。
- `cordis_mount` 可把一段 JS 临时装进活运行时（重启即消失），仅用于探测。

### 路径 C：预设创作（改 agent 行为）

- `agentPresets.copy('standard', <id>, <name>)` → 编辑 `agent.cordis.yml`（工具行、persona、realm）→ `standingKeyFor(id)` 挂载校验（能抓出包解析失败、配置非法、行未激活、进程级服务泄漏四类错误）→ 新会话生效。官方自带 standard/code/minimal/cordis 四套预设，**不得改动部署自带预设**，只能 copy 后改副本。

## 6. 能实现什么功能和效果（含社区真实案例）

**能力场景**：
- 给 agent 加自定义工具（注册动态工具，一次会话内即可用，迭代完再落成正式插件）；
- 深度定制 Web UI（主题 token、侧边栏/输入区/设置页/工具卡片注入组件、会话尾部渲染、全局浮层）；
- 造新 Agent 预设（"只读审查员""翻译专家"等角色：增删工具、换 persona、调压缩策略）；
- 集成外部系统（host 侧 `web`/`bash`/`subprocess` 接 API、跑脚本；client 侧 `host.call` 取数渲染）；
- 监听/改写运行时行为（`ctx.on` 钩子：权限门禁、结果后处理、水瀑过滤）；
- 接入新模型提供方（`registerAdapter`）或外部协议（ACP/MCP 桥接）；
- 官方「创造模式」本身是最大示范：**运行在 DSH 上的 AI 可以读写 DSH 自己**——写插件、改组合、造预设，全程在会话里完成（信任级别等同 shell 访问）。

**社区真实插件案例**（`dsh-plugin` topic / `dsh-external` 生态，一手仓库主页证据）：
- **dsh-at-file**（github.com/FSMargoo/dsh-at-file）：DSH Web GUI 实现 Codex 风格 `@file` 提及——输入框敲 `@` 即时搜索文件，发送时 host 在 agent pre-step 边界把文件内容展开注入模型；"UI 插件 + host 半"的典型组合。
- **dsh-visualize**（github.com/Nagi-ovo/dsh-visualize）：对话内生成式 UI 插件——模型调用 `visualize(...)` 后，会话流里直接渲染可交互 HTML 卡片（模拟器/图表/UI mockup），卡片跑在 sandboxed iframe（CSP 禁网络/嵌套/表单）。
- **dsh-external 生态**（github.com/dsh-external，汇总见 awesome-deepseek-harness）：DeepResearch 编排、跨会话长期记忆+后台自演化、数据库直连写 SQL、上下文/Token 审计、官方 UI 插件参考实现（turtle-ui）、浏览器面板、渠道机器人（telegram/qqbot/企业微信/微信/飞书 bot）等。安装范式统一为 `dsh plugin --profile web add "github:owner/repo#ref"`。
- **plugin-registry**（github.com/dsh-external/plugin-registry，社区维护）：浏览器面板管理 profile 插件安装态 + `make-dsh-plugin` skill 引导按官方格式写插件。
- **dsh-feishu-bot**（github.com/dsh-external/dsh-feishu-bot，**org 私有仓库**，匿名 404）：飞书机器人插件——把飞书私聊 + 群聊 @ 变成 DSH agent 对话界面。实现要点（据 awesome-dsh-plugins 源码级调研文档）：事件订阅走**自实现 WebSocket 长连接**（`callback/ws/endpoint` + 手写 protobuf 帧 + ACK + 断线重连，非 webhook）；扫码绑定（device-code 流，免手动建应用，自动区分 feishu.cn / larksuite.com）；对接 DSH 会话用 **`ctx.agents.create/resume/get` + `ctx.on('session/event')`**（非 `ctx.tools.register`，命令用 `ctx.commands.register` 注册 `/feishu bind|status`）；消息↔会话映射 `feishu-p2p-<openid>` / `feishu-group-<chatId>`，重启后 `resume` 续接，与 Web GUI 同一套会话。限制：出站仅文本（无卡片/审批按钮）、入站图片/语音仅占位、一次仅一个应用实例、凭据明文落盘、仓库首日首发（2026-08-04，2 commits，0 stars）无维护。详细调研见同目录 `_feishu-bot-调研草稿.md`。同族渠道机器人还有 `dsh-feishu-notify`（会话结束/需输入时飞书通知）、`telegram`、`tg-bot`、`qqbot`、`dsh-wecom-bot`、`dsh-weixin-bot`（均 dsh-external org）。

## 7. 限制与注意（官方原文）

1. **开发者预览 + 破坏性变更**：README 明示 "THERE WILL BE COMPATIBILITY-BREAKING CHANGES"；存储格式（SQLite SCHEMA_VERSION、SESSION_FORMAT_VERSION）无兼容承诺。
2. **信任边界**：动态插件沙箱"隔离全局变量，但不是安全边界"——官方原话 "Treat this toolset like bash access"；`cordis_mount` 对活运行时执行模型写的 JS，等同 shell 访问。加载他人插件要像授权 bash 工具一样慎重。
3. **动态包是临时的**：进程内存、重启即失、不落文件；正式能力要走静态插件路径。
4. **MCP 默认不启用**：每个 server 命令是沙箱之外的可信可执行代码。
5. **不得改动部署自带预设**（standard/code/minimal/cordis）：升级会覆盖，且破坏 cordis 预设会废掉预设创作本身。
6. **客户端半需浏览器审批**；拒绝后不可自动重试；`run` 成功 ≠ UI 渲染成功（渲染失败经 `reportRenderFailure` 上报）；带浏览器半的包在无页面连接时会挂起、无超时。
7. **接口以运行时/生成物为准**："永远不要凭服务名/事件名/槽位名猜 API"——开发前先 `cordis_inspect`（Host：`Service.listService`/`Event.listEvents`/`Builtin.listBuiltins`/`Tool.listTools`；Client：`Slots.listSubTree`/`Theme.listTokens`）。每个 subsystems 页的 `cordis-surface` 区域由 `scripts/gen-cordis-catalog.ts` 生成并与源码一致性门禁校验；工具/配置清单见 `docs/tool-catalog.md`、`docs/config-catalog.md`。
8. **机制演进快（社区佐证，非官方文档）**：2026-08 官方曾短暂推出 `.dsh-plugin` 仓库插件机制、数日后移除（本次 master 快照核实 `vendor/loader/src/` 已无 `repository.ts`，但 `docs/subsystems/skills.md` 与 tool-cordis 提示中仍残留 "repository Plugin" 提法）；社区据此建议以 `dsh.bundle` + `cordis.patch.yml` 为现行标准写法。

## 8. 参考来源

### 本地安装包（v0.1.0-rc.6，npx 缓存 node_modules/@deepseek-ai/*）

- `dsh`：`README.zh.md`、`lib/plugin-*.js`（dsh plugin CLI）、`config/agent-presets/*`（standard/code/minimal/cordis 四套预设的 `agent.cordis.yml`）
- `dsh/config/agent-presets/cordis/skills/cordis-plugin-development/SKILL.md`（官方动态插件开发技能）
- `dsh/config/agent-presets/cordis/skills/editing-cordis-compositions/SKILL.md`（官方组合编排技能）
- `dsh-base/cordis.patch.yml`（bundle patch 实例）、`dsh-web-app/cordis.patch.yml`（Web 组合层实例）
- `dsh-tool-cordis`、`dsh-cordis-host-runner`、`dsh-cordis-client-runner` 的 README

### GitHub 仓库（master 分支，raw 链接前缀 `https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/`）

- 总纲：README.md / README.zh.md、architecture.md、cordis-primer.md、AGENTS.md、CONTRIBUTING.md
- 插件开发教程：`docs/user/develop/basic/{index,tool,config,publish}.md`、`docs/cordis-tutorial/01-first-plugin.md`、`docs/user/develop/framework/index.md`（Fiber 生命周期）
- Cookbook：`docs/cookbook/extension-cookbook.md`、`adding-a-package.md`、`adding-a-tool.md`、`adding-an-llm-adapter.md`、`adding-a-conversation-node.md`、`adding-a-vendored-package.md`
- 子系统：`docs/subsystems/extensions.md`（动态插件注册表 API）、`client-modules.md`（浏览器端打包/引导，window.__DSH_BOOT__）、`skills.md`
- 包 README：`packages/hooks/README.md`、`packages/extensions/README.md`、`packages/extensions/tool-cordis/README.md`、`packages/extensions/cordis-host-runner/README.md`、`packages/mcp/mcp-client/README.md`、`packages/host/plugin-inventory/README.md`
- CLI 参考：`apps/cli/reference/README.md`；示例：`examples/README.md`
- 生成契约：`docs/tool-catalog.md`、`docs/config-catalog.md`、`docs/module-graph.md`

### 社区生态（一手仓库）

- github.com/FSMargoo/dsh-at-file · github.com/Nagi-ovo/dsh-visualize · github.com/dsh-external（含 plugin-registry、dsh-feishu-bot 等渠道机器人）· github.com/0xsline/awesome-deepseek-harness · github.com/AdamPlatin123/awesome-dsh-plugins（社区调研文档，含 dsh-feishu-bot 源码级调研）· github.com/cordiverse/cordis（上游框架）
- 附：本目录 `_feishu-bot-调研草稿.md`——dsh-feishu-bot 专项调研（长连接协议、会话映射、安装形态、限制）
