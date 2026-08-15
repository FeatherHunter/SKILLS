# SPEC · dsh-feishu-link · v0.2 产品视角规格

> 与 `DESIGN.md`（实现视角）**配对存在**：本文说什么、DESIGN 怎么说怎么实现。
> Version: v0.2.0（完善版）
> 用户授权："不搞最小需求开发，搞最完善的开发"——按对抗式审查全部 30+ 项落地。

## 1. 名字 / 标签 / 命名空间

- **插件名**: `dsh-feishu-link`（GitHub label `dsh:plugin:feishu-link`）
- **Cordis pluginId idPrefix**: `feishu`
- **package name**: `dsh-feishu-link`
- **wayfinder 标签**：`dsh:plugin:feishu-link`（紫色 #a959e8）

## 2. 解决什么问题

每个 DSH Agent 独立绑一个飞书机器人应用（PersonalAgent），让用户能用手机飞书 App 跟任意 Agent 实时双向对话，工具调用回流到 DSH Agent 对话。

**核心承诺**:
- 普通用户 30 秒内绑一个 Agent（含扫一次 QR）
- 一旦绑完，**永远不掉线**（长连接 + watchdog 重启 + token 自动换发）
- 双向消息同一会话连贯

## 3. 用户场景（end-to-end）

### 场景 1 · 首次绑定

1. 用户在 DSH 已有一个 Agent（如 `coder-1`）
2. 用户进 IM 中心（侧栏 ⛓ 飞书 IM 入口）
3. 点 `coder-1` 行的「扫码绑定」按钮
4. 弹出 BindWizardModal：QR + 倒计时 + spinner
5. 用户用手机飞书 App 扫码
6. 飞书侧弹「**创建机器人应用**」授权（PersonalAgent 流程），用户点确认
7. 自动建出应用 → 自动绑 → Modal 关闭 → IM 中心列表显示 `coder-1 ● 已绑`
8. 侧栏入口红点消失（n>0 → n=0）

### 场景 2 · 双向收发

1. Agent `coder-1` 已绑
2. 用户用手机飞书 App 私聊机器人 / 在群里 @机器人 发「继续刚才的工作」
3. 消息到达 DSH → Agent `coder-1` 的下一轮对话上下文里有这条 user 消息
4. Agent 思考 → 输出
5. DSH 把 Agent 输出发回飞书原聊天
6. 用户手机看到 Agent 响应

### 场景 3 · 解绑

1. IM 中心点 `coder-1` 行的「解绑」
2. 弹 ConfirmUnbindModal 「解绑后该 Agent 的飞书消息将不再自动转入 DSH 会话...」
3. 点「解绑」（红字）/「取消」
4. 解绑完 → IM 中心列表更新 + helper 子进程停 bot + credentials 清

### 场景 4 · 跨会话持久化

1. 用户今天绑了 Agent
2. 关 DSH
3. 第二天开 DSH
4. IM 中心列表自动恢复（无重扫）
5. 长连接自动恢复（DSH 启动 → helper 起 → 喂 broadcastList → 自动连飞书）

### 场景 5 · 用户首次（0 Agent 状态）

1. 用户没绑任何 Agent
2. 输入区 dock 显示提示条「尚未绑定任何飞书 IM。打开 IM 中心 · 绑一个 ×」
3. 点 `×` 后 localStorage 记忆，下次不再显示

## 4. 行为合约（contract）

### 4.1 host.RPC

| RPC | 入参 | 出参契约 |
|---|---|---|
| `im.listAgents` | `{}` | `{ok, agents:[{agentId, bound, platform, appId, status, boundAt}]}` |
| `im.beginBind` | `{agentId, domain?: 'feishu'\|'lark'}` | `{ok, bindId, qrContent, verificationUriComplete, expiresAt, intervalMs, status:'scan'}` |
| `im.pollBind` | `{bindId}` | `{ok, bind:{...session}}` 或 `error.not_found` |
| `im.cancelBind` | `{bindId}` | `{ok, status:'cancelled'\|'not_found'}` |
| `im.unbind` | `{agentId, domain?}` | `{ok}` |
| `im.send` | `{agentId, chatId, msgType, content, receiveIdType}` | `{ok, messageId, chatId}` 或 `error.not_bound`/`token_error` |
| `im.health` | `{}` | `{ok, helperReady, helperPid, bindsActive, recentMessagesCount, agents}` |
| `im.subscribe` | `{}` | `{ok, since: '<ts>'}` —— client 第一次调，后续 host → client 推送 → client 增 since 调 |
| `im.recentMessages` | `{agentId?, limit?}` | `{ok, count, items}` |

### 4.2 host → client 事件

| 事件 | payload |
|---|---|
| `im.bind.changed` | `{agentId, status, ...}` |
| `im.message.received` | `{agentId, message:{messageId, chatId, messageType, content, senderId, senderType, createTimeMs}}` |
| `im.helper.health` | `{ready, pid}` |

### 4.3 模型工具

| 名称 | 用途 | 约束 |
|---|---|---|
| `im_send` | 用 Agent 自己的飞书发消息 | 自动去敏感：模型只能调给定的 agentId |
| `im_pull` | 读飞书最近消息 | 默认 redact 后给模型（chat_id → 群名 + open_id → 用户代号） |

### 4.4 错误分级

| 层级 | 例子 | 用户体验 |
|---|---|---|
| info | bind 成功 / send 成功 | 静默或 toast「✓ 已绑」|
| warn | bind 用户取消 / timeout / 网络抖动可重试 | modal 内「重试」按钮 |
| error | 无网络 / 飞书拒绝 / helper crash / token 失效 | IM 中心红叉徽标 + settings 内错误详情 |

### 4.5 安全

- 不在 client 暴露 secret（client 看不到 appSecret，只看到 appId 与群名）
- im_send 输入做长度限制（飞书 4KB 文本上限）
- helper 子进程只在需要时启动，broadcast 后尽量最小内存
- 拒绝路径 escape（path 不能含 `..\..`）
- 飞书消息 receive 到 host 只 cache 200 条最旧自动淘汰，不永久留存

## 5. 性能 / 容量

- IM 中心 overlay 打开 ≤ 200ms（缓存命中）
- 扫码 QR 渲染 ≤ 100ms（用公共 QR API https://api.qrserver.com）
- 飞书 bind 状态轮询间隔 4s（poll 飞书官方推荐）
- 长连接心跳 30s（飞书 SDK 默认）
- WSS 重连间隔 2s（崩了 2s 内起）
- token 自动换发 ≥ 提前 60s 过期前
- IM 中心最大列出 9999 个 Agent（实际场景 < 100）

## 6. 与 MCODE 5 张图的对应

| MCODE 视图 | 我们的实现 | 偏差说明 |
|---|---|---|
| 图 1 sidebar Agent 列表 + 旁标📱 | IM 中心 overlay 内 Agent 列表 | 路线 A 降级：DSH sidebar 无法加 additive UI |
| 图 2 聊天框顶部「连接 IM」按钮 | conversation.input.dock + 一次性 toast | 路线 A 降级 |
| 图 3 平台选项弹窗 | IM 中心 inline modal（飞书实 + 微信占位）| P0 仅飞书，未来 P3 加微信 |
| 图 4 扫码二维码 | BindWizardModal（QR + 倒计时 + 状态机）| 1:1 实现 |
| 图 5 绑定后图标变化 | IM 中心状态徽标（30s 自动 refresh）| 路线 A 降级，语义等价 |

## 7. 路线图

| 阶段 | 范围 | 状态 |
|---|---|---|
| **v0.1** (commit fa28e760) | 5 张图 P0 + 双形态 | ✅ shipped |
| **v0.2** (本规格 + DESIGN v2) | 全部对抗审查项落地（ROADMAP 25+ 项）| 进行中 |
| **P1** | 多 Agent 路由 + 富文本卡片 + 群聊 @ 路由 | 待 v0.2 后 |
| **P2** | sidebar 行级图标 + 聊天框顶部按钮（等 DSH 端开口）| 待 DSH 决策 |
| **P3** | 微信 / 钉钉 / Telegram 平台抽象 | 待 P1 后 |

## 8. 版本管理

- **SemVer**：`v0.x.y` 主版本 0 到 1.x 才 GA；当前 v0.2.0-pre
- **CHANGELOG.md**：每个版本一段（Added / Fixed / Removed）
- **commit message**：中文 `[dsh-feishu-link] <主题> · <细节>` + Tested-By

## 9. 退出条件（用户最终验收标尺）

12 节 ACCEPTANCE.md 全部勾选 + G3 DSH 最小路径真跑通 + G4 飞书真设备流端到端跑通。
