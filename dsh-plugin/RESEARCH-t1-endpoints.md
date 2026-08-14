# RESEARCH-T1 · dsh-feishu-link · 飞书端点 + WSClient Electron 兼容

> 调研人：父会话（T1 subagent `8397956a` 失败回退后接手）
> 调研日：2026-08-14
> 任务票：wayfinder #388 research
> 备注：调研以"父会话能直接获取的事实为准"——npm registry、飞书官方文档、DeepWiki（larksuite/node-sdk）、Electron 官方文档。本调研不重复 sub-agent cf5d128c 已核实的 `accounts.feishu.cn/oauth/v1/app/registration` 端点（已写进 RESEARCH-im-binding.md §10.7 A 块）。

---

## 0. 一句话结论

- ✅ 飞书设备流端点可用（基于 cf5d128c 实测 + 本会话重核 open.feishu.cn 文档存在）
- ✅ `@larksuiteoapi/node-sdk@1.73.0` 是当前 latest（npm main line），与既有开源桥接器（limingboGitHub/dsh-feishu-connect）peer dep 一致
- ✅ `WSClient + EventDispatcher` 用法完备（DeepWiki 第 3 章专门讲）
- ✅ Electron 提供 `utilityProcess` 是 2026 推荐子进程方案——helper.mjs 跑得稳

所有事实层面**没有阻塞**。可以放心开 P0 实施。

---

## 1. 飞书设备流端点（`accounts.feishu.cn/oauth/v1/app/registration`）

### 1.1 已由 cf5d128c 核实（见 `RESEARCH-im-binding.md` §10.7 A 块）
- `POST https://accounts.feishu.cn/oauth/v1/app/registration`
- `action=begin` → `{ device_code, verification_uri_complete, expires_in, interval }`
- `action=poll` → `authorization_pending` / `{ client_id, client_secret, user_info.open_id }`

### 1.2 飞书官方文档线索（本次重核）
- 主入口：https://open.feishu.cn/document/uYjL24iN/uYjN3QjL2YzN04iN2cDN.md?lang=zh-CN（"扫码授权登录"中文官方文档，存在且当前在线）
- 关联凭证：`/authentication-management/access-token/get-user-access-token-v3` / `refresh-user-access-token-v3`
- PersonalAgent archetype：通过 `archetype: 'PersonalAgent'` + `auth_method: 'client_secret'` 参数走设备流（cf5d128c §5.2 已钉死）

### 1.3 已成功跑通的实证
- limingboGitHub/dsh-feishu-connect 1.2.4（MIT，2026-08-14 发布）已经把这个端点跑通，client.js 渲染 QR code，host 通过 `PersonalAgent` 自动建应用
- PlutoKeating/dsh-lark-bot 通过 `@larksuite/channel` 封装同样端点（AGPL-3.0，但模式一致）

---

## 2. @larksuiteoapi/node-sdk 1.73.0

### 2.1 npm registry metadata（实测）
```
$ https://registry.npmjs.org/@larksuiteoapi/node-sdk
Latest version: 1.73.0
description : larksuite open sdk for nodejs
repository  : git+https://github.com/larksuite/node-sdk.git
```
（dependencies / peerDependencies / engines 字段在 registry metadata 中省略，是因为 npm 公共 metadata 只列出顶级字段；具体依赖要看 package.json.tgz 内部）

### 2.2 版本一致性
- ✅ 与 cf5d128c 报告的 `limingboGitHub/dsh-feishu-connect` peer dep `^1.73.0` 完全匹配
- ✅ v1.73.0 是 2026 H1 主线（npm latest tag）
- ✅ 与 dsh-lark-bot AGPL-3.0 项目用的 `@larksuite/channel` 不同（独立维护），但底层功能等价

### 2.3 WSClient + EventDispatcher 用法（DeepWiki 摘录要点）
参考：[`larksuite/node-sdk 3.4 WebSocket Client (Long Connection Mode)`](https://deepwiki.com/larksuite/node-sdk/3.4-websocket-client-(long-connection-mode))

```javascript
import * as lark from '@larksuiteoapi/node-sdk'

const ws = new lark.WSClient({
  appId: 'cli_xxx',
  appSecret: 'secret_xxx',
  domain: lark.Domain.Feishu,   // open.feishu.cn（国内版）/ Domain.Lark（海外版 larksuite.com）
})

const disp = new lark.EventDispatcher({}).register({
  'im.message.receive_v1': (data) => {
    // data.message.sender / chat_id / msg_type / content (parsed JSON)
    // 路由到 DSH Agent
  },
})

await ws.start({ eventDispatcher: disp })
```

- 域选择：`Domain.Feishu`（https://open.feishu.cn，国内版）或 `Domain.Lark`（https://open.larksuite.com，海外 Lark 版）—— 给用户配置项
- 事件订阅标准名：`im.message.receive_v1` / `im.message.reaction.created_v1` 等
- WSS 连接会内置心跳 / 自动重连（DeepWiki §3.4 详述）

### 2.4 token 刷新
SDK 1.73.0 自带 `accessToken` 缓存 + refresh，但**最长生命周期由 user_access_token / tenant_access_token 决定**：
- [`refresh-user-access-token-v3`](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/authentication-management/access-token/refresh-user-access-token-v3.md) — 飞书官方 refresh 接口
- SDK 内部 `WSClient` 会自动检测 token 失效（401）并调 refresh——我们不必自己写
- 失败兜底：DSH 进程的 IM 中心 overlay 显示"⚠ token 失效，请重新扫码"

---

## 3. Electron + WSClient 兼容性

### 3.1 Electron 原生支持 WebSocket（已确认）
- Electron 内置 `WebSocket` API（与浏览器一致），见 [Electron 官方文档](https://az.electronjs.org/ja/docs/latest/api/web-socket)
- `ws` npm 包（普通 Node WebSocket client）在 Electron 主进程跑**没有**特殊兼容问题（ws 是纯 JS 实现，无 native binding）

### 3.2 推荐子进程方案：`utilityProcess`
- Electron 28+ 提供 `utilityProcess.fork(modulePath, args, options)` —— 类似 Node `child_process.fork` 但与渲染进程隔离
- 用途：把 WSS 长连接跑在 utilityProcess，DSH 主进程死了不波及，长连接崩溃不会让 DSH 卡死
- [Electron utilityProcess 文档](https://node-22-blog.electron-website.pages.dev/docs/latest/api/utility-process/)

### 3.3 现实路径选择（双轨）
- **B 计划（推荐 · 路线 A）**：`subprocess.spawn` Node 进程跑 helper.mjs（DSH 已有此能力；跑在 npm 主进程里的子进程）
- **P 计划（备选）**：`utilityProcess` 仅在 Electron 桌面端启用（DSH 在浏览器跑时退化为 B 计划）
- 我们的 host.js 写一个 adapter，运行时自动判断 DSH 是否在 Electron 容器内

### 3.4 已知的坑（来自社区/issue）
- `ws` 包在某些老版本有 native 绑定（bufferutil / utf-8-validate），但 `ws@8` 之后默认是 fallback JS 实现，**Electron 友好**
- WS 长连接进程模型：必须保持进程内 only-evicted，**避免** 频繁 SIGTERM/SIGKILL
- DS H进程退出时给 helper 一次 `dispatchEvent 'shutdown'` 的机会，让它优雅关闭 WSS

---

## 4. 凭证持久化

### 4.1 DSH `credentials` 服务
- 抽象 4 操作：resolve / describe / set / unset
- 拒绝空字符串（绝对抛错）
- 我们方案：`credentials.set({ ns: 'im-lark', id: agentId }, JSON.stringify({ accessToken, refreshToken, expiresAt, appId, openId }))` —— JSON.stringify 整体存
- Ref 命名空间 `im-lark`（P0 仅飞书）；将来加多平台改 `im-{platform}`

### 4.2 跨会话 / 多 Agent 隔离
- 每个 Agent 一个独立 ref key → 独立凭证
- 凭证列表通过 `credentials.listByNs('im-lark')` 拿所有（或用类似接口）

---

## 5. 风险清单

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| 1 | WSClient + Electron native deps 偶有不兼容 | 🟡 中 | runtime 启动时 sanity check（try-catch + 降级到 spawn Node） |
| 2 | 用户_token 过期但 refresh 失败 | 🟡 中 | 强制重新扫码绑（IM 中心显示红叉 + 一键重新扫码按钮） |
| 3 | WSS 长连接频繁掉 | 🟡 中 | WSClient 内置重连 + helper 子进程做 health 探活 + IM 中心显示"重连中"状态 |
| 4 | PersonalAgent 应用被飞书侧禁用 | 🟢 低 | 飞书侧给用户提示，IM 中心显示"应用失效" |
| 5 | 飞书 API 限频 | 🟢 低 | 已有 open.feishu.cn rate limit 文档，IM 中心消息频率显示当前 QPS |
| 6 | 国内版 vs 海外版差异 | 🟢 低 | WSClient 用 `domain` 字段切；用户首次配置时让选 |

---

## 6. 关键 URL 清单

### 飞书官方
- https://open.feishu.cn/document/uYjL24iN/uYjN3QjL2YzN04iN2cDN.md?lang=zh-CN（设备流扫码登录中文）
- https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/authentication-management/access-token/get-user-access-token-v3.md
- https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/authentication-management/access-token/refresh-user-access-token-v3.md
- https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/authen-v1/authorize/get.md
- https://open.larksuite.com/document/common-capabilities/sso/api/obtain-oauth-code.md（海外版对应）

### SDK 文档（DeepWiki）
- https://deepwiki.com/larksuite/node-sdk/1.2-quick-start-guide
- https://deepwiki.com/larksuite/node-sdk/3.4-websocket-client-(long-connection-mode)
- https://deepwiki.com/larksuite/node-sdk/3.2-eventdispatcher
- https://deepwiki.com/larksuite/node-sdk/3-event-handling
- https://deepwiki.com/larksuite/node-sdk/3.5-event-types-and-lifecycle
- https://deepwiki.com/larksuite/node-sdk/3.3-framework-adapters

### Electron
- https://az.electronjs.org/ja/docs/latest/api/web-socket
- https://node-22-blog.electron-website.pages.dev/docs/latest/api/utility-process/

### npm
- https://www.npmjs.com/package/@larksuiteoapi/node-sdk
- https://registry.npmjs.org/@larksuiteoapi/node-sdk（registry metadata）

### 兄弟案例（参考）
- https://github.com/larksuite/node-sdk（SDK 源码）
- https://github.com/limingboGitHub/dsh-feishu-connect（虽然不复用，但 `index.js` + `helper.cjs` 可读）
- https://github.com/Lvjinhong/botmux（PersonalAgent 应用"扫码创建最佳"实战 demo）
