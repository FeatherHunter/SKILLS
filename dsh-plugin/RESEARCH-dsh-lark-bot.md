# 调研报告 · DSH 飞书 IM 绑定插件

> 调研人：subagent
> 调研日：2026-08-14
> 调研路径：DSH（DeepSeek Harness）侧 — 探查开源社区插件实现

## 0. 摘要（三句话）

1. **主目标 A（PlutoKeating/dsh-lark-bot，npm 双包 `dsh-lark-bot` + `dsh-feishu-bot`）是真实存在、已发布 v0.5.1 的成熟项目**，其飞书绑定走「**飞书 PersonalAgent 应用设备流注册**」——`@larksuite/channel` 封装的 `oauth/v1/app/registration` 端点生成二维码，终端 `qrcode-terminal` 渲染 → 飞书 App 扫码 → 选择/创建 PersonalAgent 应用 → `client_id`/`client_secret` 回填，与 MCODE 的应用模型同源。
2. **本次调研最重要的二手来源（B：`AdamPlatin123/awesome-dsh-plugins/research/dsh-feishu-bot.md`）无法找到**——`AdamPlatin123/awesome-dsh-plugins` 仓库存在（也是生态雷达），但其目录树里 **没有 `research/` 子目录、没有 `dsh-feishu-bot.md` 文件**，`main` 分支下该文件 404。唯一能作为二手脉络来源的是它的 `PLUGINS.md` 与 Oh-My-DSH 的 `PLUGINS.md`（均把 dsh-lark-bot 归入「📡 远程渠道」）。
3. **调研对象 C（`plutokeating/dsh-feishu-connect`）的前提是错的**：真实同名的 `dsh-feishu-connect` npm 包是 **`limingboGitHub/dsh-feishu-connect`**（npm latest 1.2.4，维护者 `lmber`），与 PlutoKeating **无关**；而 `@lc2panda/dsh-im-channels`（npm 0.3.1，微信+飞书聚合）**不是 MCODE 式扫码绑定**——飞书侧是「表单填 App ID/Secret」+「CLI 交互式录入 + tenant_access_token 校验」，另有一套**配对码（pairing code）访问控制**机制。它与 MCODE「点图标 → 扫码 → 绑定」体验差距最大。

---

## 1. dsh-lark-bot / dsh-feishu-bot（PlutoKeating）

> 结论：这是三个项目里**最贴近 MCODE 体验**的——用飞书官方 PersonalAgent 应用 + 扫码设备流，实现「扫码即创建/绑定应用」，agent 后端走官方 dsh SDK / ACP adapter。

### 1.1 项目元数据
- 仓库：https://github.com/PlutoKeating/dsh-lark-bot（默认分支 `main`）
- README（main）：https://raw.githubusercontent.com/PlutoKeating/dsh-lark-bot/main/README.md
- package.json（main）：https://raw.githubusercontent.com/PlutoKeating/dsh-lark-bot/main/package.json
- 版本：`0.5.1`；license **AGPL-3.0**；`type: module`；`packageManager: pnpm@10.33.0`；engines `node >=22.19.0`
- **双包发布**（README 原文）：*"Both package names ship identical content — pick either one: `dsh-lark-bot` / `dsh-feishu-bot`"*，由 `scripts/publish-dual-packages.mjs` 生成仅 `name`/`bin` 不同的两份清单，同版本同依赖同 dist；同一 dist 还发到 GitHub Packages `@plutokeating/dsh-lark-bot` / `@plutokeating/dsh-feishu-bot`。
- 依赖清单（package.json dependencies，原文摘录）：
  ```
  "@agentclientprotocol/sdk": "0.25.1",
  "@deepseek-ai/dsh-sdk-client": "0.1.0-rc.6",
  "@larksuite/channel": "^0.4.1",
  "commander": "^12.1.0",
  "cross-spawn": "^7.0.6",
  "qrcode-terminal": "^0.12.0",
  "yaml": "^2.9.0"
  ```
  关键点：**`@larksuite/channel`（飞书通道封装）+ `qrcode-terminal`（终端二维码）+ 官方 dsh SDK / ACP**。对比 dsh-feishu-connect 用的是原生 `@larksuiteoapi/node-sdk`。

### 1.2 目录与关键文件
README「目录结构」表摘录：
| 目录 | 职责 |
|---|---|
| `src/bridge/` | 飞书通道接入（消息、卡片、媒体） |
| `src/onboard/` | 首次扫码创建 / 绑定 PersonalAgent 应用 |
| `src/session/` | 会话路由、排队、访问控制 |
| `src/workspace/` | 项目工作区、git worktree 隔离与规则注入 |
| `src/adapters/` | agent 后端适配器（sdk 默认 / acp 审批 / headless legacy） |
| `src/card/` | 流式卡片状态与渲染 |
| `src/bot/` | 运行注册、消息排队、审批/问答注册表 |
| `src/commands/` | 斜杠命令（/cd /ws /new …） |
| `src/cli/` | CLI 入口与 start / status / restart / stop / doctor |
| `src/platform/`、`src/service/` 等 | 跨平台原子写入、后台服务管理 |

根目录 contents 断言（api.github.com/list）：`.env.example`、`.github`、`.gitignore`、`.npmrc`、`AGENTS.md`、`LICENSE`、`README.md`、`SECURITY.md`、`bin/`、`docs/`、`examples/`、`package.json`、`pnpm-lock.yaml`、`reference/`、`scripts/`、`src/`、`test/`、`tsconfig.json`、`tsup.config.ts`、`vitest.config.ts`。`src/onboard/registration.ts`（size 2242）确认存在。
架构（README）：`飞书 ⇄ WebSocket 长连接 ⇄ bridge/ ⇄ session/ ⇄ workspace/ ⇄ adapters/ ⇄ dsh ⇄ DeepSeek V4`——**飞书通道与 agent 后端解耦**，adapter 默认 SDK、可选 ACP（审批卡）、legacy headless。

### 1.3 IM 绑定流程（按用户五张图映射）
> ⚠️ 本调研无法观察到用户「五张截图」的具体 UI，仅能按 README+src 的证据映射哪些能力存在。dsh-lark-bot 的绑定发生在**终端 CLI（`dsh-lark-bot start`）**，不在 Web GUI 里。

- **绑定入口（对应「第 1、2 图 / 聊天框」）**：这是**独立 CLI + 后台服务**，不是 Web 内嵌 UI。README Quick Start 给出 `dsh-lark-bot start` = 安装后台服务 + 开机自启，首次运行进入扫码向导。消息收发在飞书私聊/群聊/@bot，不通过 dsh Web 聊天框。**dsh-lark-bot 本身不实现 Web 侧「Agent 列表带图标 / 聊天框连接按钮」**——那是 MCODE 产品内嵌体验，本项目落在终端扫码。
- **绑定平台选项（对应「第 3 图」）**：`src/onboard/registration.ts` 关键代码摘录（入口文件，main 分支可见）：
  ```ts
  import { registerApp, type RegisterAppOptions, type RegisterAppResult } from '@larksuite/channel';
  import qrcode from 'qrcode-terminal';
  ...
  const result = await register({
    source: deps.source ?? DEFAULT_SOURCE,   // DEFAULT_SOURCE = 'dsh-lark-bot'
    onQRCodeReady: (info) => {
      print('请使用飞书 / Lark App 扫描以下二维码，创建或选择 PersonalAgent 应用：');
      renderQr(info.url);                     // qrcode.generate(value, { small: true })
      print(`二维码有效期约 ${minutes} 分钟。`);
    },
    onStatusChange: (info) => { /* domain_switched / slow_down */ },
  });
  ...
  return { appId: result.client_id, appSecret: result.client_secret, tenant, operatorOpenId: result.user_info?.open_id };
  ```
  绑定产物为 **`client_id` + `client_secret` + `tenant`（feishu/lark）+ `operatorOpenId`** ——即创建一个飞书「PersonalAgent」应用并回填其 AppID/Secret。
- **扫码二维码（对应「第 4 图」）**：QR 由 `registerApp`（`@larksuite/channel` 内部）向后端换取 `info.url`（即二维码 payload，实为设备流 `verification_uri_complete`），终端用 `qrcode-terminal` 渲染，同时打印 `info.url` 供浏览器打开。**涉及飞书 API**：`@larksuite/channel` 封装的是飞书/ Lark **应用注册设备流**，与 dsh-feishu-connect 明示的端点一致（见 §2），即 `POST https://accounts.feishu.cn/oauth/v1/app/registration`，action `init`→`begin`→`poll`：
  - `begin` → 返回 `device_code` + `verification_uri_complete`（二维码内容）——**产生链接/二维码的端点**；
  - `poll` → 用 `device_code` 轮询，用户扫码确认后返回 `client_id`/`client_secret`——**轮询设备状态的端点**（授权前返回 `authorization_pending`，即「尚未扫码」状态）；
  - `archetype: 'PersonalAgent'`（dsh-feishu-connect 明示；本包经 `@larksuite/channel` 传参一致）。
- **绑定成功（对应「第 5 图」）**：`onPromptComplete` 成功后，`registration.ts` 打 `✓ PersonalAgent 应用创建 / 绑定成功`，打印 App ID / Tenant；随后（README）bot 向私聊发送欢迎卡片。README：*"Choose or create a PersonalAgent app. Once bound, the bot sends a welcome card to your private chat."* 已有 AppID/Secret 时可 `dsh-lark-bot start --app-id cli_xxx --app-secret <secret> --tenant feishu` 跳过扫码（`src/onboard/registration.ts` 前述 + README）。

### 1.4 评估（距离 MCODE 体验还差什么）
- MCODE 是「**Web/桌面应用内嵌**」：Agent 列表带图标 → 聊天框顶层连接按钮 → 平台选择页 → 弹二维码 → 绑定后图标点亮。dsh-lark-bot **没有 Web 内嵌绑定 UI**，扫码发生在**终端**（`qrcode-terminal`），缺少「点图标绑定」的前置交互层。
- dsh-lark-bot 绑定**一次仅绑定一个 PersonalAgent 应用**（单 profile `~/.dsh/profiles/dsh-lark`），而 MCODE/多 IM 生态常要求「多机器人 + 多工作区」并可热切换（dsh-feishu-connect 已支持多 bot）。dsh-lark-bot 更接近「单 bot 单 profile」。
- 其文档/代码证据充分，适配已锁定官方 dsh SDK/ACP，工程质量高；但**从「扫码方式」角度它与 MCODE 同构**——差异主要在产品外壳（终端 vs 内嵌 GUI）而非绑定协议。

---

## 2. dsh-feishu-connect

> 结论：真实存在的 `dsh-feishu-connect` 属于 **`limingboGitHub`（作者 lmber）**，与调研前提中的 `plutokeating` **无源属关系**（GitHub 上 `plutokeating/dsh-feishu-connect` 404）。它是标准 Cordis bundle 插件：Host(index.js) + Client(client.js) + helper 子进程 + `cordis.patch.yml`，**实现了与 MCODE 几乎一致的「设置页生成二维码 → 扫码自动创建机器人」设备流**，且明示端点。

### 2.1 元数据 + 关系
- npm：`dsh-feishu-connect` latest **1.2.4**，维护者 `lmber`（675683354@qq.com），license **MIT**
- GitHub：https://github.com/limingboGitHub/dsh-feishu-connect（分支 main）
- README：https://raw.githubusercontent.com/limingboGitHub/dsh-feishu-connect/main/README.md ；contents 见 api.github.com（`client.js` 16284B、`index.js`、`helper.cjs`、`cordis.patch.yml`、`feishu.config.example.json`、`README.md`）
- npm 元数据：deps `@larksuiteoapi/node-sdk ^1.73.0` + `qrcode ^1.5.4`；peerDeps `@deepseek-ai/dsh-tools ^0.1.0-rc.5`；`dsh.bundle.patch = ./cordis.patch.yml`，`client.platform = web`；exports `./client` / `./helper`
- 安装：`dsh plugin --profile web add dsh-feishu-connect`；配置写入 **`~/.cc-connect/feishu.config.json`**（cc-connect 同款约定，本机主目录不解耦于任何仓库）；会话状态 `~/.cc-connect/state-<appId>.json`。
- 与 dsh-lark-bot 的**关系**：二者**互相独立、无上下游**（不同作者、不同许可证、不同底层 SDK 封装——`@larksuiteoapi/node-sdk` vs `@larksuite/channel`）。共同点是都做「DSH 桥飞书长连接 + 扫码建应用」，且**都抄/对齐 `lark-channel-bridge`（cc-connect）的协议**（dsh-lark-bot 的 RESEARCH.md 明示参照 `zarazhangrui/lark-coding-agent-bridge`）。
- **为何「projectId/qrcode/oauth 类工具」？**：是——它面向 **PersonalAgent 应用** QR/OAuth 设备流，绑定粒度是「**机器人 → 工作区（workspace）**」，支持**多机器人**（每 bot 一个 appId/workspace/长连接/会话池）。

### 2.2 IM 绑定流程（设备流原文摘录，index.js L912-1015）
```
// ---- Feishu official app-registration onboarding (device flow).
// POST https://accounts.feishu.cn/oauth/v1/app/registration with
// form-encoded { action, ... } — the same public API cc-connect uses:
//   init  -> supported_auth_methods (must include client_secret)
//   begin -> device_code + verification_uri_complete (the QR payload)
//   poll  -> client_id/client_secret once the user scanned and confirmed
const onboardingBase = 'https://accounts.feishu.cn/oauth/v1/app/registration'
async function onboardingCall(params) {
  const init = onboardingForm({ action: 'init' }) ...
  const begin = onboardingForm({ action: 'begin', ...params }) ...
  return beginData   // device_code + verification_uri_complete
}
async function onboardingPoll(deviceCode) {
  const form = onboardingForm({ action: 'poll', device_code: deviceCode }) ...
}
async function handleAdminOnboard(req, res) {
  const data = await onboardingCall({
    archetype: 'PersonalAgent',
    auth_method: 'client_secret',
    request_user_info: 'open_id',
  })
  // qrcode dynamic import: toDataURL(data.verification_uri_complete, { margin:1, width:240 })
  respondJson(res, 200, { ok:true, deviceCode, qrContent, qrDataUrl, userCode, expiresIn, interval })
}
// poll loop returns client_id/client_secret once scanned+confirmed
```
- **产生链接/二维码的端点**：`POST accounts.feishu.cn/oauth/v1/app/registration` `action=begin` → `verification_uri_complete`（也即 `agent.minimaxi.com` 系飞书个人应用扫码同款机制）。
- **轮询设备状态端点**：`action=poll&device_code=...` → 未扫码返回 `authorization_pending`；已确认返回 `client_id` + `client_secret`（即 AppID/AppSecret）。
- 设置页在 `/feishu/admin/*`（同源 admin 路由：status / config / delete-bot / send-test / onboard / onboard-poll），Host 插件 `index.js`（id `feishu-bridge`），Client 为 `client.js`。
- 绑定后：测试发送自动以扫到机器人的 owner open_id 建单聊（`ownerOpenId` 自动存）。

### 2.3 结论
`dsh-feishu-connect` 是现有开源实现中**与 MCODE「设置页生成二维码 → 飞书 App 扫码 → 自动建机器人 → 配置工作区」体验最接近**的（且多机器人 + 每机器人工作区）。唯一差异是它把「PersonalAgent」这个应用模型显式写为 `archetype: 'PersonalAgent'`，与 MCODE 的 PersonalAgent 语义一致。

---

## 3. @lc2panda/dsh-im-channels

> 结论：**统一 IM 频道插件（微信 + 飞书/Lark），Web UI 配置**。但飞书侧绑定是「**表单填 App ID/Secret**（RPC 保存 + tenant_access_token 校验）」和「**CLI 交互式录入**」，**不是扫码设备流**；另有一套**配对码（pairing code）访问控制**。与 MCODE 的「点图标去绑定」流程不匹配。

### 3.1 元数据 + 现状
- GitHub 仓库 `lc2panda/dsh-im-channels` 存在（api.github.com 返回 200，desc "DeepSeek Harness IM频道插件，支持微信，飞书/Lark"），但 **`main` 分支 contents 为 `[]`（空仓库），README/文件均 404**（`/contents/` 返回 `[]`，`README.md` main/master 均 404，default_branch=main）。**有效内容在 npm**。
- npm：`@lc2panda/dsh-im-channels` latest **0.3.1**，license MIT，author `lc2panda`
- npm 元数据：deps `@larksuiteoapi/node-sdk ^1.73.0`、`qrcode ^1.5.4`、`qrcode-terminal ^0.12.0`、`silk-wasm ^3.6.0`、`zod ^3.23.0`；peerDeps `@deepseek-ai/cordis ^4.0.1`、`@deepseek-ai/dsh-agent ^0.1.0-rc.6`、`@deepseek-ai/dsh-session ^0.1.0-rc.6`、`@deepseek-ai/dsh-tools ^0.1.0-rc.6`、`@deepseek-ai/schemastery ^3.18.1`、`react ^18.0.0`
- 结构（npm 0.3.1 tarball 内部）：`src/`（TS 源码）+ `lib/`（编译产物）+ `setup.js`；脚本 `setup` / `setup:wechat`=&gt;`lib/shared/wechat-login.js` / `setup:feishu`=&gt;`lib/shared/feishu-login.js`；客户端组件 `lib/client/{FeishuConfig,WechatConfig,SettingsPage}.js`；Host 侧 `lib/host/rpc-handlers.js`。

### 3.2 飞书绑定 / 绑定相关 API（关键词 link/oauth/scan/qrcode 摘录）
**(a) CLI 交互式录入凭据 + 校验 —— `src/shared/feishu-login.ts`：**
```
1. 访问 https://open.feishu.cn/app/
2. 创建或选择一个「自建应用」
3. 复制「App ID」和「App Secret」
...
const authUrl = domain === 'feishu'
  ? 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
  : 'https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal'
const authData = await fetch(authUrl, { method:'POST', body: JSON.stringify({ app_id, app_secret }) })
if (authData.code !== 0) throw new Error(...)
writeFileSync(credsFile, JSON.stringify({ appId, appSecret, domain }, null, 2), { mode: 0o600 })
// 后续：在开放平台「事件订阅」配置回调 + 订阅 im.message.receive_v1 + 发布版本
```
> 涉及 **OAuth/token API**：`auth/v3/tenant_access_token/internal`（校验 app_id+app_secret 换 token），**无扫码、无 qrcode 生成**（qrcode/qrcode-terminal 依赖用于微信侧而非飞书绑定）。

**(b) Web/RPC 表单绑定 —— `src/client/FeishuConfig.tsx`：**
```
const result = await (window as any).host.call('im-channels.saveFeishuConfig', {
  appId: state.appId.trim(), appSecret: state.appSecret.trim(), domain: state.domain,
})
```
表单字段：App ID / App Secret / 版本（feishu.cn 国内版 or larksuite.com 国际版）。保存成功后缀言「在飞书开放平台配置回调 + 订阅 im.message.receive_v1 + 发布应用版本」。

**(c) 长连接 + 事件 —— `src/channels/feishu-channel.ts`：**
```
this.wsClient = new lark.WSClient({ appId, appSecret, domain: domain==='lark' ? lark.Domain.Lark : lark.Domain.Feishu })
wsClientAny.on('im.message.receive_v1', ...) / new lark.EventDispatcher({}).register({ 'im.message.receive_v1': ... })
// 发送: client.im.message.create({ data:{ receive_id: chatId, msg_type:'text', ... }, params:{ receive_id_type:'chat_id' } })
```

**(d) 配对码访问控制 —— `src/channels/feishu-channel.ts` handlePairing()：**
```
const code = generatePairingCode()
this.access.pending[code] = { senderId, createdAt, expiresAt: Date.now()+600000, replies: 1 }
await this.sendMessage(userId, `你的配对码是 ${code}，有效期 10 分钟。`, { chat_id: chatId })
// 未授权用户发消息时弹配对码，让管理员执行配对命令放行
```

### 3.3 与 dsh-lark-bot / dsh-feishu-connect 的差异
| 维度 | @lc2panda/dsh-im-channels | dsh-lark-bot | dsh-feishu-connect |
|---|---|---|---|
| 绑定方式 | 表单/CLI 录入凭据 + token 校验；**无扫码建应用** | 扫码设备流（PersonalAgent 应用，@larksuite/channel） | 扫码设备流（PersonalAgent，accounts.feishu.cn/oauth） |
| 载体 | 原生 Cordis 插件（Web RPC `im-channels.saveFeishuConfig`） | 独立 CLI + 后台服务（非 Web 内嵌） | Cordis bundle（Web 设置页 `/feishu/admin/*`） |
| 覆盖 | 微信+飞书（统一频道） | 仅飞书（单就绑定） | 仅飞书（多机器人） |
| 额外机制 | 配对码(pairing code)访问控制；silk-wasm(微信语音) | 白名单 40 条记忆、git worktree 工作区 | 每 bot 独立会话池 + ownerOpenId 单聊 |
| 扫码 | 否 | 是（终端 qrcode-terminal） | 是（client.js qrcode → dataURL） |

---

## 4. Oh-My-DSH / awesome-dsh-plugins（清单与脉络）

### 4.1 现存 IM 绑定 / 飞书渠道相关插件（名字 / 链接 / 一句话）
- **PlutoKeating/dsh-lark-bot** → https://github.com/PlutoKeating/dsh-lark-bot — 飞书/Lark bot 桥接 dsh，扫码 PersonalAgent 绑定 + 完整工作区管理（Oh-My-DSH PLUGINS.md「📡 消息通讯」有收录，⭐6，TypeScript，活跃）。
- **omdsh-dev/dsh-lark**（npm `dsh-lark-channel`）→ https://github.com/omdsh-dev/dsh-lark — Lark/Feishu IM bot channel 插件：每聊天驱动独立 dsh agent，reasoning/tool call 以原生思考过程展示、审批为交互卡片；**传输用 `@larksuite/channel` WebSocket 长连接**（无需回调 URL），BSD-3-Clause。
- **imetn/dsh-lark-bridge** → https://github.com/imetn/dsh-lark-bridge — 双向 Lark/Feishu 控制器：DM/群/话题发任务进正确 project/session，单卡片推进状态，审批/问答回路由，测于 dsh 0.1.0-rc.6，MIT。
- **limingboGitHub/dsh-feishu-connect**（npm `dsh-feishu-connect`）→ https://github.com/limingboGitHub/dsh-feishu-connect — 扫码建 PersonalAgent 机器人 + 多 bot 工作区（§2）。
- **lc2panda/dsh-im-channels**（npm `@lc2panda/dsh-im-channels`）→ GitHub 仓库空，内容在 npm — 微信+飞书统一 IM 频道，表单/CLI 绑定凭据 + 配对码（§3）。
- **dsh-external/dsh-feishu-bot**、**dsh-external/dsh-feishu-notify** → Oh-My-DSH `data/curated.json` 收录条目（无更多内容可核实，仓库/源码未细查）；注意：Oh-My-DSH 的 `dsh-feishu-bot` 指向 `dsh-external` 组织，与 PlutoKeating 的 npm 双包 `dsh-feishu-bot` **是两码事**。
- **ben7am1n/dsh-telegram** → Telegram 渠道（同类对照，非飞书）；**STARDUSTLC666/dsh-dingtalk / dsh-slack** → 钉钉/Slack 通知（可作对比，非飞书绑定）。
- **`AdamPlatin123/awesome-dsh-plugins/PLUGINS.md`** → 也收录了 `PlutoKeating/dsh-lark-bot`，列在「📡 远程渠道」表。

### 4.2 MCODE 侧公开信息（web_search 汇总，仅脉络对照）
公开可查到 MiniMax Code/MaxClaw（OpenClaw 变体）的飞书接入是 **OpenClaw 体系 + 官方飞书插件**，核心流程（来源：博客园《OpenClaw + MiniMax + 飞书机器人 通用配置流程》：https://www.cnblogs.com/vivekgd/articles/19667044）：
1. **模型层授权**：`openclaw plugins enable minimax-portal-auth` + `openclaw onboard --auth-choice minimax-portal`（网页 OAuth 授权，选区域端点如中国区「CN」）。
2. **飞书通道**：选择「Feishu/Lark（飞书）」通道 → 安装官方飞书插件 → **输入飞书平台获取的 App ID / App Secret** → 配置 WebSocket 连接模式 + 区域域名 + 群聊白名单。
3. **配对放行**：`openclaw pairing approve feishu [配对码]`——配对码来自飞书机器人首次消息提示，用于「access not configured」权限拦截。
4. 即：**MCODE/MiniMax 侧公开做法是「表单填 AppID/Secret + 配对码」形态**，与 `@lc2panda/dsh-im-channels` 的配对码机制最像，而**不是** PersonalAgent 设备流扫码。若用户指的 MCODE「点击 IM 图标扫码绑定」是开放平台内的应用，则需 MiniMax 官方文档 `platform.minimaxi.com`（https://platform.minimaxi.com/docs/solutions/openclaw）进一步核实——当前 web_search 未返回该「点图标扫码」的官方页面。

---

## 5. 事实对比表（核心）

| 维度 | dsh-lark-bot (PlutoKeating) | @lc2panda/dsh-im-channels | dsh-feishu-connect (limingboGitHub) | MCODE（公开可查，推断） |
|---|---|---|---|---|
| 仓库/GitHub | github.com/PlutoKeating/dsh-lark-bot（main 完整，src 可见） | github.com/lc2panda/dsh-im-channels（**main 空**，实体的在 npm） | github.com/limingboGitHub/dsh-feishu-connect | 未有一手代码；见本文 §4.2 链接 |
| npm | dsh-lark-bot / dsh-feishu-bot（双包同内容）v0.5.1 | @lc2panda/dsh-im-channels v0.3.1 | dsh-feishu-connect v1.2.4 | — |
| License | AGPL-3.0 | MIT | MIT | — |
| 绑定方式（IM 图标扫码?） | PersonalAgent 设备流扫码（注册应用→client_id/secret 回填），终端 qrcode-terminal | 表单/CLI 填 AppID/Secret + tenant_access_token 校验 + **配对码**加速访问；**无扫码建应用** | PersonalAgent 设备流扫码（设置页客户端生成二维码），`accounts.feishu.cn/oauth/v1/app/registration` | OpenClaw：表单 AppID/Secret + `pairing approve` 配对码（公开可查）；「点图标扫码」无直接公开文档 |
| 绑定 API（关键端点） | `@larksuite/channel.registerApp`（底层 oauth/v1/app/registration） | `auth/v3/tenant_access_token/internal`（校验）；`im.message.receive_v1`（长连接） | `oauth/v1/app/registration`（init/begin/poll；poll 前返回 authorization_pending） | 经飞书官方插件 + OpenClaw pairing 机制 |
| 出站长连接（长连接） | 是（WebSocket，@larksuite/channel + 官方 SDK） | 是（@larksuiteoapi/node-sdk WSClient） | 是（@larksuiteoapi/node-sdk helper.cjs WSClient） | 是（WebSocket 连接模式） |
| Host/Client 双端 | 单 CLI 后台进程（非 Cordis bundle） | Cordis bundle（host + client Web UI RPC） | Cordis bundle（Client client.js + Host index.js + helper.cjs 子进程） | — |
| 绑定 UI 外壳 | 终端扫码（无 Web 内嵌「点图标」） | Web 设置页表单 + CLI setup 脚本 | Web 设置页生成二维码 + 多 robot 列表 | 产品内嵌（推断） |
| 多机器人/多工作区 | 单 bot 单 profile | 微信+飞书统一频道（多 channel） | 多 bot，每 bot 绑定 workspace | 通知/多频道（推断） |
| 距 MCODE「点图标→扫码→绑定」体验 | 协议同构，外壳是终端非内嵌 GUI，缺「Agent 图标+聊天框按钮」前置层 | 差距最大（无扫码建应用，靠填凭据+配对码） | 最接近（设置页扫码自动建应用 + 自动 ownerOpenId 单聊） | — |

---

## 6. 主要不确定 / 没法核实

- **B（二手关键来源）`AdamPlatin123/awesome-dsh-plugins/research/dsh-feishu-bot.md` 不存在**：`awesome-dsh-plugins/main` 目录树无 `research/`、无该文件，raw 文件 404。已核实其树中 `feishu|research|lark` 零命中。只能以它的 `PLUGINS.md`/`README.md` 作为替代二手来源。
- **用户五张截图的具体 UI** 无法在本调研中看到；「第 1/2 图（Agent 列表带图标、聊天框连接按钮）」只可能在 MCODE 或某个 Web 内嵌插件里出现，本调研对象均为 CLI/Cordis 形态，无法逐图断言。
- **`plutokeating/dsh-feishu-connect` 不存在**（README 与 contents 均 404）；同名真实项目属 `limingboGitHub`，且其 npm 发布者身份（`lmber`）与 GitHub 用户名（`limingboGitHub`）需读者自行核对同一人。
- **`@lc2panda/dsh-im-channels` 的 GitHub 仓库为空**（main 为空数组）：无法核对 README 与源码是否与 npm 包一致，存在「Git 未推送 / 改名 / 删除源码」的不确定；本文以其 npm 0.3.1 tarball 实测为准。
- **`dsh-external/dsh-feishu-bot` 与 `dsh-external/dsh-feishu-notify`**：仅见 Oh-My-DSH curated.json 收录条目，未深挖仓库内容，不能断言其实现。
- **MCODE 的「点 IM 图标→扫码绑定」官方一手文档**未检索到；当前 web_search 只返回 OpenClaw/博客的「填 AppID/Secret + 配对码」流程。`agent.minimaxi.com` 内部机制无法从公开资料核实，只能作为「推断」而非事实。
- **dsh-lark-bot 与 dsh-feishu-connect 是否共用 `lark-channel-bridge` 协议**：dsh-lark-bot 的 RESEARCH.md 明确其参照 `zarazhangrui/lark-coding-agent-bridge`；dsh-feishu-connect 在其代码注释里自称「cc-connect 同款」。两者都表明对齐 cc-connect，但**无证据显示二者代码直接同源/互 fork**。

---

## 附 · 核心一手/二手 URL（供顺藤摸瓜）
- https://github.com/PlutoKeating/dsh-lark-bot （README / package.json / src/onboard/registration.ts / docs/RESEARCH.md 均在 main）
- https://github.com/limingboGitHub/dsh-feishu-connect （README / index.js / client.js / cordis.patch.yml / feishu.config.example.json）
- https://www.npmjs.com/package/dsh-feishu-connect 、https://www.npmjs.com/package/dsh-lark-bot
- https://www.npmjs.com/package/@lc2panda/dsh-im-channels （GitHub 同名但 main 空）
- https://github.com/like-study1/Oh-My-DSH/blob/main/PLUGINS.md 、https://github.com/AdamPlatin123/awesome-dsh-plugins/blob/main/PLUGINS.md
- https://www.cnblogs.com/vivekgd/articles/19667044（OpenClaw+MiniMax+飞书）、https://platform.minimaxi.com/docs/solutions/openclaw
