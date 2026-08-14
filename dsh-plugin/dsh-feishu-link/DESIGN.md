# DESIGN · dsh-feishu-link · v1 设计定稿

> 设计文档（合并 `RESEARCH-im-binding.md` §10.7 + `ADR-GRILLING-UX.md`）
> 调研档案：`D:\2Study\StudyNotes\SKILLS\dsh-plugin\RESEARCH-im-binding.md`（v3）
> UX 默认决策：`D:\2Study\StudyNotes\SKILLS\dsh-plugin\dsh-feishu-link\docs\ADR-GRILLING-UX.md`
> 撰写日：2026-08-14

## 0. 一句话定位

DSH（DeepSeek Harness）Web 界面插件 — 给 DSH Agent 接入飞书/Lark IM 的能力，仿 MCODE 5 张图 UX，落地路线 A。

## 1. 命名 / 命名空间

- **插件名**：`dsh-feishu-link`（"link" 含"链接"语义，亦呼应"中继"连续动作；不撞 GitHub 已知的 dsh-feishu-* 系列）
- **Wayfinder 标签**：`dsh:plugin:feishu-link`（新建，紫色 #a959e8）
- **Cordis pluginId idPrefix**：`feishu`（3–6 字母）
- **package name**：`dsh-feishu-link`
- **GitHub Issues**：[#387 map](https://github.com/FeatherHunter/SKILLS/issues/387) + #388-#392 子票

## 2. 背景

- DSH Agent 通过 DSH 内部的 `agentLoop.create` / `agentPresets` 已支持创建
- 飞书"Lark/Feishu"开放平台已有完整的 OAuth 设备流 / WSS 长连接方案
- MCODE（MiniMax Code）等竞品实现了"Agent 列表 + 飞书扫码绑"的体验
- DSH 之前没有 IM 桥接插件

### 2.1 目标
让每个 DSH Agent 都能：
1. 扫码绑到一个飞书机器人应用（无须先去开发者后台建 App）
2. 长期保持 WSS 长连接，飞书消息双向收发
3. 状态可视化在 IM 中心 overlay

## 3. UI 形态（路线 A · ADR 已拍板）

| MCODE 5 张图 | DSH 落地 |
|---|---|
| 图 1 · Agent 列表 + 旁标📱 | shell.overlay「IM 中心」内 Agent 列表视图 |
| 图 2 · 聊天框顶部"连接 IM"按钮 | conversation.input.dock 一次性 toast + 「× 不再提醒」 |
| 图 3 · 平台选项弹窗 | IM 中心主面板 inline 入口 + Modal |
| 图 4 · 扫码二维码 | BindWizardModal · QR + 状态机（scan/waiting/success/failed/timeout）|
| 图 5 · 绑定后图标变化 | IM 中心状态徽标（30s 自动 refresh）|

**5 组件**：
1. SidebarButton（侧栏入口）
2. IMStationOverlay（IM 中心主面板）
3. BindWizardModal（扫码向导）
4. ConfirmUnbindModal（解绑确认）
5. SettingsPage（settings.plugins.tab「飞书 IM」配置页）
6. BindHint（conversation.input.dock 提示条）

## 4. 数据模型

### 4.1 凭证（DSH credentials 服务）
- 命名空间：`im-lark`
- ref：`{ ns: 'im-lark', id: agentId }`
- value：`JSON.stringify({ appId, appSecret, tenant, operatorOpenId, accessToken, expiresAt, boundAt })`

### 4.2 元数据（文件系统）
- 路径：`~/.dsh/im-bindings/<agentId>.json`
- 字段：`{ agentId, platform: 'lark', status, appId, operatorOpenId, tenant, boundAt }`
- 解绑 = `writeText({status: 'deleted', deletedAt: ts})`（避免 fs 服务不支持 unlink）

### 4.3 Ring buffer（host 进程内）
- 大小：200 条最近消息
- 字段：`[{ agentId, message, receivedAt }]`
- model 工具 `im_pull` 暴露给模型读取

## 5. 协议栈

### 5.1 飞书设备流
- 端点：`POST https://accounts.feishu.cn/oauth/v1/app/registration`
- 流程：`init → begin (拿 device_code + verification_uri_complete) → poll (轮询直到 success)`
- `archetype: 'PersonalAgent'` — 飞书侧自动识别"扫码即建应用"

### 5.2 飞书 token
- `POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
- 2h 自动过期；host.js `ensureFreshToken()` 自动换发并 cache

### 5.3 WSS 长连接
- `@larksuiteoapi/node-sdk@^1.73.0` · `WSClient({ appId, appSecret, domain: Domain.Feishu })`
- `EventDispatcher({}).register({ 'im.message.receive_v1': handler })`
- 域切换：`Domain.Feishu`（open.feishu.cn，国内版）或 `Domain.Lark`（open.larksuite.com，海外版）

### 5.4 消息路由
- helper 子进程 spawn → 跑 WSClient → 收消息 → 上行 `{ type: 'message', agentId, eventType, payload }`
- host 解析 `payload.messageId / chatId / messageType / content / senderId / senderType / createTimeMs`
- host 推 `harness.handleEvent('im.message.received', ...)` 到 Client
- Client 暂时不主动路由到 Session（让用户/模型决定何时 pull）

## 6. Host / Client 双形态

### 6.1 动态版（开发用）
- `host.js` —— cordis_define code.host 函数体
- `client.js` —— cordis_define code.client 函数体
- 在带 cordis 工具的会话中 `cordis_define` + `cordis_run` 加载（首次需批准）

### 6.2 npm 安装版（生产用）
- `package/lib/index.js` —— ESM host 半（`export const name + inject + apply`）
- `package/lib/client.js` —— 浏览器 bundle（`window.__ModuleLoader__.load` 格式）
- `package/scripts/install-patch.cjs` —— postinstall 自动注册 `cordis.patch.yml`
- 安装命令：
  ```bash
  npx --yes @deepseek-ai/dsh plugin --profile web add dsh-feishu-link
  ```

## 7. Host RPC 清单（harness.handle 7 个）

| RPC | in | out |
|---|---|---|
| `im.listAgents` | `{}` | `{ok, agents:[{agentId, name, bound, platform, appId, status, boundAt}]}` |
| `im.beginBind` | `{agentId}` | `{ok, bindId, agentId, qrContent, verificationUriComplete, expiresAt, intervalMs, status}` |
| `im.pollBind` | `{bindId}` | `{ok, bind:{...session}}` 或 `{ok:false, error:{kind:'not_found'}}` |
| `im.cancelBind` | `{bindId}` | `{ok, bindId, status}` |
| `im.unbind` | `{agentId}` | `{ok, agentId}` |
| `im.send` | `{agentId, chatId, msgType?, content, receiveIdType?}` | `{ok, messageId, chatId}` |
| `im.health` | `{}` | `{ok, helperReady, helperPid, bindsActive, recentMessagesCount, agents}` |
| `im.listHelpers` / `im.recentMessages` | `{agentId?, limit?}` | `{ok, recentMessages}` |

## 8. Client ↔ Host 通讯

- Client → Host：`host.call(method, args)`（R5 验证）
- Host → Client：`harness.handleEvent(name, payload)` 单向推送
- 事件名：
  - `im.bind.changed` —— 绑定状态变化
  - `im.message.received` —— helper 收到新消息

## 9. 状态机

### 9.1 bindSession 状态机
```
scan ──user scans QR──> waiting ──success──> success (消失, 触发 refresh)
  │                       │
  └─timeout──> timeout   └─fail──> failed (用户 retry)
  └─cancel──> cancelled
```

### 9.2 Host 内部状态机
```
helper: not_started → spawn(args) → ready (broadcastList 把已绑 Agent 喂给它)
                    → done → restart-after-3s
each bot: connecting → connected (emit im.bind.changed)
                  → closed/failed (触发 reconnect / emit)
                  → stalled (>30s 无心跳) → emit reconnecting
```

## 10. 自动重连 / 错误恢复

- helper 进程死掉 → 3s 后 restart（DSH timer）
- WSClient 长连接断了 → SDK 内置重连；30s 还连不上 → emit `botStalled`
- token 过期 → host `ensureFreshToken()` 检测 → 自动换发
- 命令 / RPC 错误 → 抛 `FeishuBindError` 给上层（UI 显示）

## 11. 路线图

- **P0**（本次 v0.1.0）：单飞书 + 单 Agent + 5 张图完整流程 + 双向消息 + IM 中心 + npm 双形态发布
- **P1**：多 Agent 路由 + 富文本卡片 + 群聊 @ 路由 + 主动推送
- **P2**：sidebar 行级图标 + 聊天框顶部按钮（DSH 端开口）
- **P3**：微信 / 钉钉 / Telegram 平台抽象

## 12. 文件结构（最终）

```
dsh-feishu-link/
├── README.md
├── DESIGN.md                          (本文件)
├── ACCEPTANCE.md
├── package.json
├── host.js                            (cordis_define code.host 动态版)
├── client.js                          (cordis_define code.client 动态版)
├── lib/
│   ├── fetch.mjs                      (5 纯 fetch)
│   └── ipc.mjs                        (IPC schema + writeLine/parseLines)
├── helper/
│   └── helper.mjs                     (WSS 子进程)
├── tests/
│   ├── verify-fetch.mjs               (PASS · 32/32)
│   └── verify-ipc.mjs                 (PASS · 23+/23+)
├── docs/
│   └── ADR-GRILLING-UX.md             (6 条 UX 默认决策)
└── package/                           (npm 安装版)
    ├── package.json
    ├── scripts/install-patch.cjs      (postinstall)
    ├── lib/index.js                   (ESM host 半)
    └── lib/client.js                  (browser bundle)
```

## 13. 测试

```bash
npm run test:fetch        # lib/fetch.mjs 自检
npm run test:ipc          # lib/ipc.mjs 自检
```

完整验收（包括 helper 进程 + WSS 在线测试）见 `ACCEPTANCE.md`。

## 14. 风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| 飞书端点变更 / 鉴权变更 | 🟡 中 | T1 research 已核实 + 用户授权"按最佳实践拍板" + 飞书 OpenClaw SDK 1.73 自带部分兼容 |
| WSS 在 Electron 主进程挂掉 | 🟡 中 | helper 子进程 + watchdog 3s 重启 |
| token 过期 | 🟢 低 | host `ensureFreshToken()` 自动换发 + cache |
| 多 Agent 路由 | 🟢 低 | P0 单 Agent，P1 加 |
| 用户没装 lark SDK | 🔴 高 | 包 deps 声明 `@larksuiteoapi/node-sdk@^1.73.0` + `ws@^8.18.0`，让 npm 自动装 |
| AGPL 传染（勿踩） | 🟢 低 | 仅借鉴开源思路，不复刻任何 AGPL 项目代码 |
