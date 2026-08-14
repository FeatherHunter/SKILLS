# DSH 社区飞书（Feishu/Lark）机器人插件调研

> 调研日期：2026-08（依据 awesome-dsh-plugins 仓库最近推送 2026-08-13）
> 数据源：① awesome-dsh-plugins 调研文档 ② awesome-deepseek-harness README ③ GitHub API / web_search 核实
> 标注约定：「未找到」= 公开渠道无法获取，如实标注，不臆造。

## TL;DR

- 插件本体：`github.com/dsh-external/dsh-feishu-bot`（**org 私有仓库，匿名访问 404**；内容以 awesome-dsh-plugins 调研文档为准）。
- 形态：**cordis 风格纯宿主插件**（permanent plugin），不是 patch 半插件；**不使用 `ctx.tools.register`**；飞书事件用**自实现长连接（WebSocket）客户端**监听（非 webhook）；对接 DSH 会话用 **`ctx.agents.create/resume/get` + `ctx.on('session/event')`**（非 `ctx.sessions` / `agent.followup`）。
- 亮点：零运行时依赖、扫码即用（免手动建应用）、自动区分国内 feishu.cn / 国际 larksuite.com、长连接工程化完备（重连/ACK/去重/单连接守卫）。

---

## 1. awesome-dsh-plugins 调研文档（dsh-feishu-bot.md）

来源：<https://raw.githubusercontent.com/AdamPlatin123/awesome-dsh-plugins/main/research/dsh-feishu-bot.md>

### 插件仓库地址

- `https://github.com/dsh-external/dsh-feishu-bot`
- 包名 `dsh-feishu`，版本 0.1.0，`private: true`；纯 JavaScript（ESM），Node ≥ 22；`package.json` 无任何 dependencies（零运行时依赖，测试只用 `node:test`）。

### 安装命令

- **公开渠道未找到一行式安装命令**（仓库私有）。调研文档给出的安装形态：
  - 安装位置：`~/.dsh/plugins/dsh-feishu/`，并通过 `~/node_modules/@dsh-local/dsh-feishu` 软链让宿主 resolve；凭据写回 `~/.dsh/config.yaml` 的 `dsh-feishu` 条目（寄生式/手动安装，与同族 `dsh-wecom-bot` 一致，参见 `research/dsh-wecom-bot.md`：`~/.dsh/plugins/` + `node_modules/@dsh-local/` 软链 + config.yaml `insert`）。
  - awesome-deepseek-harness README 的通用安装命令（bundle 流程，需包声明 `dsh.bundle.patch` 才生效；本插件是否声明未证实）：`dsh plugin --profile web add "github:owner/repo#ref"`。
  - 运行时本体：`npx @deepseek-ai/dsh web`。

### 功能

- 把飞书**私聊 + 群聊 @机器人**变成 DSH agent 的对话界面。
- 内联斜杠命令（不走模型，插件直接回复）：`/help`、`/new`（同义 `/reset`）、`/status`、`/model [provider/]name`（会话级切换）、`/models [provider]`（列出模型，前 20）。
- 扫码绑定（device-code 流）：`/feishu bind` → 飞书 App 扫码 → 自动拿到 `client_id/client_secret` 并写回配置 → 宿主 HMR 热重载；自动识别 `tenant_brand` 切换 `accounts.feishu.cn` ↔ `accounts.larksuite.com`。
- 访问控制：`dmPolicy` / `groupPolicy`（`open | allowlist | disabled`）+ `ownerIds` 二级安全网；群聊仅在有 @ 时处理。
- "流式"送达：`assistant/message` 事件逐条以 reply 发回（首条 reply，后续普通发送）；按 chatId 排队保证顺序。

### 工作原理

- **事件订阅 = 长连接（WebSocket），不是 webhook**。`POST /callback/ws/endpoint` 用 AppID/AppSecret 换 wss URL 与 `client_config`（重连/抖动/Ping 由服务端下发）；所有帧为**自写 protobuf** 编解码（`lib/pb.js`，215 行实现 Frame proto2 最小子集）；DATA 帧 `type=event` 为事件 JSON，多片按 `message_id + seq` 重组（TTL 5s）；收到必须回 `{"code":0}` ACK 否则飞书重推；`USER_AGENT` 必须带 `channel` 标记否则收不到消息事件；undici WebSocket 须设 `binaryType='arraybuffer'`。断线重连参数全部来自服务端，`ReconnectCount=-1` 无限重连 + 随机抖动；模块级 `activeClients` 做同 appId 单连接守卫。
- **消息↔会话映射**：私聊 `feishu-p2p-<openid>`，群聊 `feishu-group-<chatId>`；`/new` 自增 generation，id 加 `-g<n>` 后缀；重启后经 `ctx.agents.resume({resumeSessionId})` 续接（先查 `ctx.get('sessionPersistence').list()`）；generation 与 300s 去重窗口持久化到 `~/.dsh/feishu-state.json`。这些会话与 Web GUI 同一套会话 API，同样出现在 GUI 会话列表。

### 配置要求

- 用户**无需手动建飞书开发者应用**——扫码绑定自动完成（device-code 流：`POST accounts.feishu.cn/oauth/v1/app/registration`，`init → begin`，archetype=`PersonalAgent`，auth_method=`client_secret`，request_user_info=`open_id`；后台每 5s poll，600s 超时）。
- 凭据（appId/appSecret）明文 JSON 写入 `~/.dsh/config.yaml` 的 `dsh-feishu` 条目（行级 YAML 编辑，零依赖取舍）；支持 `DSH_FEISHU_*` / 旧 `FEISHU_*` 环境变量回退。
- 需要飞书侧权限：`im/v1/messages` 发消息、`auth/v3/tenant_access_token/internal` 取 token、`bot/v3/info`；长连接端点 `callback/ws/endpoint`。具体 scope 列表在私有 README 中，公开渠道未获取到完整权限清单（未找到）。

### 已知限制

- 图片/语音/视频/文件入站**只转占位描述**，无 OCR/STT/视觉；出站**仅文本**，无飞书卡片/审批按钮。
- 群聊只响应 @；一次只能连一个应用实例（多应用需多份插件配置）。
- 手写 YAML 编辑较脆（依赖固定缩进形态）；手写 protobuf 仅实现 Frame 最小子集。
- **License 不一致**：`package.json` 声明 BSD-3-Clause，仓库 LICENSE 文件实为 MIT。
- 凭据明文落盘，无额外加密。

### 维护状态

- 创建于 2026-08-04 20:14 UTC，仅 2 个 commit（Initial commit + 长连接通道提交），0 stars/0 forks/0 issues，无 CI/CHANGELOG——**首日首发，无社区使用反馈**。

---

## 2. awesome-deepseek-harness README 中的渠道机器人条目

来源：<https://raw.githubusercontent.com/0xsline/awesome-deepseek-harness/HEAD/README.md>（另有 README.zh-CN.md 中文版）

「Notifications & Channels」分类（飞书/渠道机器人相关条目摘录）：

| 条目 | 链接 | 一句话说明 |
|---|---|---|
| dsh-feishu-bot | <https://github.com/dsh-external/dsh-feishu-bot> | Feishu bot（飞书机器人，即本次调研对象） |
| dsh-feishu-notify | <https://github.com/dsh-external/dsh-feishu-notify> | Feishu notifications（会话结束 / 需要输入时的飞书通知） |
| telegram | <https://github.com/dsh-external/telegram> | Channel integration for Telegram |
| tg-bot | <https://github.com/dsh-external/tg-bot> | Telegram bot |
| qqbot | <https://github.com/dsh-external/qqbot> | QQ bot |
| dsh-wecom-bot | <https://github.com/dsh-external/dsh-wecom-bot> | WeCom（企业微信）bot |
| dsh-weixin-bot | <https://github.com/dsh-external/dsh-weixin-bot> | WeChat（微信）bot |
| dsh-voice-chat | <https://github.com/dsh-external/dsh-voice-chat> | Voice chat |
| dsh-web-ui-notify | <https://github.com/dsh-external/dsh-web-ui-notify> | WebUI 通知 |
| dsh-ica | <https://github.com/dsh-external/dsh-ica> | ICalingua 前端 |
| dsh-teamwork | <https://github.com/dsh-external/dsh-teamwork> | 团队协作（cordis） |

安装说明（README 原文要点）：官方运行时 `npx @deepseek-ai/dsh web`；外部 profile bundle `dsh plugin --profile web add "github:owner/repo#ref"`（转发给 pnpm；**只有声明 `dsh.bundle.patch` 的包才成为激活的 profile 层**，普通依赖仅安装不激活；装完重启 `dsh --profile web`）。README 注明：部分 `dsh-external` 仓库链接可能需要 org 访问权限。

---

## 3. 插件本体仓库定位（web_search + GitHub API 核实）

- web_search「dsh-feishu-bot github」与「dsh-external feishu bot」：返回结果均为通用 DeepSeek+飞书教程（如 kangarooking/feishu-chatgpt-bot、open.feishu.cn 文档、CSDN/博客园文章等），**未找到插件本体公开镜像**；其中第一个搜索把 awesome-dsh-plugins 的调研文档 URL 作为来源返回，佐证其存在。
- GitHub API 核实：`api.github.com/repos/dsh-external/dsh-feishu-bot` 匿名访问返回 **404**；raw.githubusercontent.com 上 README.md / package.json 同样 404 → 结论：**仓库存在于 dsh-external org 下但为私有/受限**，与 awesome README「部分 dsh-external 链接需 org 权限」的提示一致。
- 唯一权威公开摘要即第 1 节的调研文档（作者具有 org 访问权，直接读过源码与 README，并给出了 `lib/` 文件级细节）。
- 同族调研文档（同一 research 目录，可交叉参考）：`dsh-wecom-bot.md`、`dsh-weixin-bot.md`、`qqbot.md`、`telegram.md`、`tg-bot.md`。

## 4. 「host 半插件」机制核查

**结论：不是 patch 半插件，是 cordis 风格纯宿主插件。** 依据调研文档（源码级阅读），插件本体源码未能公开直接读取（仓库私有，未找到公开镜像），以下结论以调研文档为准：

- **插件形态**：遵循 cordis 契约——`export const name`、`export const inject = ['agents','commands']`、`export function apply(ctx, config)`；**不打补丁、不改主仓库代码**，非 `dsh.bundle.patch` overlay 分发（对照：同 org 的 `tg-bot` 才是"源码 overlay + host patch"分发，见 `research/tg-bot.md`）。
- **是否用 `ctx.tools.register` 注册工具**：**否**。注册的是宿主**命令**：`ctx.commands.register(...)` 注册 `/feishu status`、`/feishu bind`；内联 `/model` 等命令由 `agent-bridge.js` 直接处理，均不走工具注册。
- **是否监听飞书事件**：**是，但用自实现长连接客户端**（`lib/feishu-client.js`，WS + protobuf），不是宿主事件总线；对宿主的监听是 `ctx.on('session/event', ...)`（过滤本插件拥有的 sessionId，做 turn/assistant message → 飞书回复）与 `ctx.on('dispose', ...)`（生命周期清理）。
- **是否对接 DSH 会话/agent**：**是**，走 `ctx.agents`：`create({sessionId, agentOptions:{provider,model}, meta:{cwd}})` / `resume({resumeSessionId, agentOptions})` / `get(sessionId)`；辅以 `ctx.get('sessionPersistence').list()`（重启续接）与 `ctx.get('llm')`（listProviders/listModels）。**未使用 `ctx.sessions` 或 `agent.followup` 这类 API**（调研文档未提及；公开渠道无法进一步核实其不存在，仅能确认文档所述路径）。
- **其他宿主集成点**：`ctx.logger`、`ctx.effect()`、配置读 `~/.dsh/config.yaml` 插件 `config:` 字段 + HMR 热重载。

---

## 信息来源清单

1. <https://raw.githubusercontent.com/AdamPlatin123/awesome-dsh-plugins/main/research/dsh-feishu-bot.md>（主依据，源码级调研）
2. <https://raw.githubusercontent.com/0xsline/awesome-deepseek-harness/HEAD/README.md>（渠道条目 + 安装说明）
3. <https://github.com/dsh-external/dsh-feishu-bot>（本体仓库，org 私有，匿名 404）
4. <https://github.com/dsh-external/dsh-feishu-notify>、<https://github.com/dsh-external/tg-bot>、<https://github.com/dsh-external/telegram>、<https://github.com/dsh-external/qqbot>、<https://github.com/dsh-external/dsh-wecom-bot>、<https://github.com/dsh-external/dsh-weixin-bot>（同族渠道机器人）
5. GitHub API：`api.github.com/repos/dsh-external/dsh-feishu-bot`（404，私有佐证）；`api.github.com/repos/AdamPlatin123/awesome-dsh-plugins`（公开）
6. web_search：`dsh-feishu-bot github`、`dsh-external feishu bot`、`"dsh-feishu-bot" DeepSeek Harness 飞书 插件`（未发现公开镜像/额外仓库）

## 未找到项（如实标注）

- 插件本体 README.md / package.json 公开内容（org 私有，raw 与 API 均 404；web_search 无镜像）→ 相关结论转引调研文档。
- 官方一行式安装命令、飞书侧完整权限 scope 清单（仅在私有 README 中）。
- `ctx.sessions` / `agent.followup` / `ctx.tools.register` 的直接源码证据（仅能确认调研文档所述路径，无法排除其他路径存在）。
