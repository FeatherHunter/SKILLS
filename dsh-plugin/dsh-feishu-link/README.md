# dsh-feishu-link

> **DSH（DeepSeek Harness）插件 — 给 DSH Agent 接入飞书/Lark IM 的能力**
>
> 仿 MCODE（MiniMax Code）的"侧栏 Agent 列表 + 扫码绑飞书机器人 + 长连接实时沟通"体验。
> 落地为**路线 A**（IM 中心 overlay + 设置页 + input.dock 提示条），核心技术栈：
> 飞书 OAuth 设备流（`oauth/v1/app/registration`）+ WebSocket 长连接（`@larksuiteoapi/node-sdk@^1.73.0`）+ DSH `credentials` 服务。
>
> **v0.2.0-pre · 完善开发版（30+ 项 ROADMAP 全量落地）**

## 路径速记

- 工作目录：`D:\2Study\StudyNotes\SKILLS\dsh-plugin\dsh-feishu-link\`
- 调研档案：`D:\2Study\StudyNotes\SKILLS\dsh-plugin\RESEARCH-{im-binding,dsh-lark-bot,feishu-connect-health,t1-endpoints}.md`
- 产品规格：`docs/SPEC.md`
- 设计定稿：`DESIGN.md`
- 开发路线：`ROADMAP-completion.md`
- 变更日志：`CHANGELOG.md`
- 卸载指南：`docs/UNINSTALL.md`
- 验收清单：`ACCEPTANCE.md`
- UX 默认决策：`docs/ADR-GRILLING-UX.md`
- Wayfinder 地图：[#387](https://github.com/FeatherHunter/SKILLS/issues/387)（CLOSED）
- 兄弟插件（范式）：`D:\2Study\StudyNotes\SKILLS\dsh-plugin\dsh-waystation\`

## 功能

| 模块 | 表现 | 实现 |
|---|---|---|
| 飞书扫码绑 | 用户在 IM 中心点「扫码绑定」→ 弹出 QR → 手机飞书 App 扫 → 自动建 PersonalAgent 应用 → 进入 DSH Agent 对话 | `lib/fetch.mjs` 4 纯 fetch |
| WSS 长连接 | helper 子进程拉 WSClient 长连，host 通过 stdio JSON RPC 调度 | `helper/helper.mjs` + `@larksuiteoapi/node-sdk@1.73` |
| 双向消息 | 手机消息 → 长连接 → helper → host → DSH Agent 会话（im.message.received 事件）；DSH Agent 输出 → host 发消息 → 飞书消息通道 | host.js 7 RPC + 2 model tools (im_send/im_pull) |
| IM 中心 overlay | shell.overlay 主面板：Agent 列表 + 状态徽标 + 扫码绑定 + 解绑 + 拖动 + 缩放 | shell.overlay slot 注册 |
| 侧栏入口 | sidebar.footer.action 入口图标 + 状态高亮 + n>0 红点徽标 | sidebar.footer.action slot 注册 |
| 设置页 | settings.plugins.tab「飞书 IM」配置页（健康状态 + Agent 列表 + 高级设置） | settings.plugins.tab slot 注册 |
| Dock 提示条 | conversation.input.dock 显示未绑提示（可关闭 + localStorage 持久化） | conversation.input.dock slot 注册 |
| 凭证持久化 | DSH `credentials` 服务按 `{ns:'im-lark', id:agentId}` 分 Agent 存 | host.js `credentials.set/resolve/unset` |

## 文件清单

```
dsh-feishu-link/
├── README.md                          (本文件)
├── ROADMAP-completion.md              30+ 项完善清单
├── CHANGELOG.md
├── DESIGN.md                          实现视角设计
├── ACCEPTANCE.md                      12 节验收清单
├── LICENSE                            MIT
├── .editorconfig                      跨编辑器一致
├── .eslintrc.json                     静态检查
├── .prettierrc                        格式化
├── .npmignore                         npm publish 排除
├── .gitignore                         git 排除
├── package.json                       metadata + scripts
├── host.js                            cordis_define code.host (7 RPC + 2 model tools + bind state machine)
├── client.js                          cordis_define code.client (6 组件 + 4 slot + styles.insert)
├── lib/
│   ├── fetch.mjs                      5 纯 fetch + FeishuBindError
│   ├── ipc.mjs                        IPC schema + writeLine/parseLines/createHelperProcess
│   └── (后续追加：persistence / redaction / security)
├── helper/
│   └── helper.mjs                     WSS 子进程 (WSClient + EventDispatcher + 6 命令 + 心跳)
├── tests/
│   ├── verify-fetch.mjs               32 PASS lib/fetch
│   ├── verify-ipc.mjs                 32 PASS lib/ipc
│   └── probe-sandbox.mjs              cordis sandbox 探测
├── scripts/
│   ├── install-patch.cjs              npm postinstall · 幂等注册
│   └── uninstall-patch.cjs            npm uninstall · 移除 patch 段（v0.2+）
├── docs/
│   ├── SPEC.md                        产品视角规格
│   ├── UNINSTALL.md                   卸载完整指南
│   └── ADR-GRILLING-UX.md             6 条 UX 默认决策
└── package/                           npm 安装版
    ├── package.json
    ├── scripts/install-patch.cjs
    ├── lib/index.js                   ESM host 半（connection.rpc.handle '/dsfl'）
    └── lib/client.js                  browser bundle
```

## 使用方式

### 动态版（开发者用 · 零安装 · 重启失效）

DSH 会话中由 Agent 通过 Cordis 工具链加载：

1. `cordis_define` —— plugin `kind: new`、`idPrefix: feishu`（3–6 小写字母），code.host 填入 `host.js` 源码、code.client 填入 `client.js` 源码。
2. `cordis_run` —— 首次运行需在界面批准。
3. 生效后输入区 dock 显示绑定提示；点侧栏底部「⛓ 飞书 IM」打开 IM 中心 overlay。

### 正式安装版（生产用 · 推荐 · 开机自启）

```bash
# 安装
npx --yes @deepseek-ai/dsh plugin --profile web add dsh-feishu-link

# 升级
npx --yes @deepseek-ai/dsh plugin --profile web update dsh-feishu-link

# 卸载
npx --yes @deepseek-ai/dsh plugin --profile web remove dsh-feishu-link
```

安装完：
- 在 `~/.dsh/profiles/web/node_modules/dsh-feishu-link`
- 在 `~/.dsh/profiles/web/cordis.patch.yml` 应有 `dsh-feishu-link` insert 块
- 刷浏览器页面（http://127.0.0.1:3080）即生效

> ⚠ **勿用 `npm install --prefix ~/.dsh/profiles/`** —— 会 prune 掉 DSH 其它插件。

## 自检指引（必跑）

```bash
# lib 离线自检（必须 64 PASS / 0 FAIL）
npm run test:fetch      # 32 PASS
npm run test:ipc        # 32 PASS

# 一次性全跑（v0.2+）
npm test

# 装包完整性（v0.2 实跑过 1 次 = OK）
npm install --no-audit --no-fund
# 然后 node -e 'import("./lib/fetch.mjs").then(()=>console.log("OK"))'

# sandbox 实测（在带 cordis 工具的 DSH 会话）
node tests/probe-sandbox.mjs
```

## 飞书 sandbox 应用获取（首次必须）

v0.2 之后，用户**不需要先去开发者后台建 App**。流程：

1. 用户在 DSH IM 中心点「扫码绑定」
2. BindWizardModal 弹 QR
3. 用户用手机飞书 App 扫码 → 飞书侧自动弹「**创建机器人应用**」
4. 用户点确认 → PersonalAgent 应用自动创建 + 自动绑到 Agent
5. ✅ 完成

如果**想要用已有飞书应用**（而非新建 PersonalAgent），手动配置：
```bash
# 跳 im.beginBind，用 RPC 手动传 appId/appSecret
# 本插件默认走 PersonalAgent 设备流（archetype='PersonalAgent'），不暴露手动传 secret 接口
# 如需此能力，后续 P1 加
```

## Lark 海外版

v0.2 全链路支持 Lark 海外版。

调用方需传 `domain: 'lark'`：

```js
host.call('im.beginBind', { agentId: 'my-agent', domain: 'lark' })
// 否则默认 domain: 'feishu'
```

切换后：
- accounts.feishu.cn → accounts.larksuite.com
- open.feishu.cn → open.larksuite.com
- WSClient `Domain.Lark` vs `Domain.Feishu`

## UI 路线（第一性原理）

| MCODE 5 张图 | 我们的实现（路线 A）|
|---|---|
| 图 1 · Agent 列表 + 旁标📱 | IM 中心 overlay 内 Agent 列表视图 + 状态徽标 |
| 图 2 · 聊天框顶部"连接 IM"按钮 | conversation.input.dock 提示条 + 一次性 toast |
| 图 3 · 平台选项弹窗 | IM 中心 inline 入口 + Modal 流程 |
| 图 4 · 扫码二维码 | BindWizardModal · QR + 状态机（scan/waiting/success/failed/timeout）|
| 图 5 · 绑定后图标变化 | IM 中心状态徽标（30s 自动 refresh）|

**未来升级**：DSH 端开口给 `conversation.toolbar.action` / `sidebar.item.action` 等 additive 子 slot 后，可升级到"产品内嵌行级图标"（路线 B）。

## 协议栈

### 我们自己的依赖
- `@larksuiteoapi/node-sdk@^1.73.0` —— 飞书官方 SDK + WSClient + EventDispatcher
- `ws@^8.18.0` —— Node WSS 直连（被 SDK 间接依赖；显式声明）
- 不复用 `dsh-feishu-connect` npm 包（致命绑定 + 版本缺口 + 无 LICENSE）

### 飞书端点
| 用途 | 国内版 (feishu) | 海外版 (lark) |
|---|---|---|
| 设备流 begin/poll | `POST accounts.feishu.cn/oauth/v1/app/registration` | `POST accounts.larksuite.com/oauth/v1/app/registration` |
| 拿 token | `POST open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal` | `POST open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal` |
| 发消息 | `POST open.feishu.cn/open-apis/im/v1/messages` | `POST open.larksuite.com/open-apis/im/v1/messages` |

### PersonalAgent 应用
绑定时传 `archetype: 'PersonalAgent'`，飞书侧自动识别"扫码即建应用"。

## 路线图

- **v0.1.0** ✅ shipped commit fa28e760（P0 5 张图 + 双向消息）
- **v0.2.0-pre** 🛠 ROADMAP 全量 30+ 项（进行中）
- **P1**：多 Agent 路由 + 富文本卡片 + 群聊 @ 路由
- **P2**：sidebar 行级图标 + 聊天框顶部按钮（等 DSH 端开口）
- **P3**：微信 / 钉钉 / Telegram 平台抽象

## License

MIT — 见 [LICENSE](./LICENSE)。
