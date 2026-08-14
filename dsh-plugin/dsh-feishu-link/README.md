# dsh-feishu-link

> **DSH（DeepSeek Harness）插件 — 给 DSH Agent 接入飞书/Lark IM 的能力**
>
> 仿 MCODE（MiniMax Code）的"侧栏 Agent 列表 + 扫码绑飞书机器人 + 长连接实时沟通"体验。
> 落地为**路线 A**（IM 中心 overlay + 设置页 + input.dock 提示条），核心技术栈：
> 飞书 OAuth 设备流（`oauth/v1/app/registration`）+ WebSocket 长连接（`@larksuiteoapi/node-sdk@^1.73.0`）+ DSH `credentials` 服务。

## 路径速记

- 工作目录：`D:\2Study\StudyNotes\SKILLS\dsh-plugin\dsh-feishu-link\`
- 调研档案：`D:\2Study\StudyNotes\SKILLS\dsh-plugin\RESEARCH-im-binding.md` (v3)
- 设计决策：`D:\2Study\StudyNotes\SKILLS\dsh-plugin\dsh-feishu-link\docs\ADR-GRILLING-UX.md`
- Wayfinder 地图：[#387 [dsh-feishu-link] v1 实施 map · ...](https://github.com/FeatherHunter/SKILLS/issues/387)
- 兄弟插件（参考模板）：
  - `D:\2Study\StudyNotes\SKILLS\dsh-plugin\dsh-waystation\`（v25/v26 全栈范例）

## 功能

| 模块 | 表现 | 实现 |
|---|---|---|
| 飞书扫码绑 | 用户在 IM 中心点「扫码绑定」→ 弹出 QR → 手机飞书 App 扫 → 自动建 PersonalAgent 应用 → 进入 DSH Agent 对话 | `lib/fetch.mjs` 4 个 fetch 调用飞书设备流（`oauth/v1/app/registration`） |
| WSS 长连接 | 绑定成功后 helper 子进程拉 WSClient 连飞书长连接，host 通过 stdio JSON RPC 调度 | `helper/helper.mjs` + `@larksuiteoapi/node-sdk@1.73.0` |
| 双向消息 | 手机飞书消息 → 长连接 → helper → host → DSH Agent 会话（带 im.message.received 事件）；DSH Agent 输出 → host 发消息 → 飞书消息通道 | host.js 7 RPC + 2 model tools（im_send / im_pull） |
| IM 中心 overlay | shell.overlay 主面板：Agent 列表 + 状态徽标 + 扫码绑定 + 解绑 | `shell.overlay` slot 注册 |
| 侧栏入口 | sidebar.footer.action 入口图标 + n>0 时显示红点 | `sidebar.footer.action` slot 注册 |
| 设置页 | settings.plugins.tab「飞书 IM」配置页（健康状态 + Agent 列表） | `settings.plugins.tab` slot 注册 |
| Dock 提示条 | conversation.input.dock 显示未绑提示（可关闭） | `conversation.input.dock` slot 注册 |
| 凭证持久化 | DSH `credentials` 服务按 `{ns:'im-lark', id:agentId}` 分 Agent 存 | host.js `credentials.set/resolve/unset` |

## 文件清单

```
dsh-feishu-link/
├── README.md                          (本文件)
├── DESIGN.md                          [TODO · 与 RESEARCH-im-binding §10.6 合并定稿]
├── ACCEPTANCE.md                      [TODO · 仿 waystation ACCEPTANCE.md 范式]
├── package.json                       npm metadata
├── host.js                            cordis_define code.host (RPC + 状态机 + credentials + helper 管理)
├── client.js                          cordis_define code.client (5 组件 + styles.insert + 4 slot 注册)
├── lib/
│   ├── fetch.mjs                      5 纯 fetch 函数 (beginBind / pollBind / initBind / getTenantAccessToken / sendImMessage)
│   └── ipc.mjs                        IPC schema + writeLine / parseLines / createHelperProcess
├── helper/
│   └── helper.mjs                     WSS 子进程入口 (WSClient + EventDispatcher + 6 命令 + 心跳)
├── tests/
│   └── verify-fetch.mjs               lib/fetch.mjs 自检 (不需要 DSH)
└── docs/
    └── ADR-GRILLING-UX.md             6 条 UX 默认决策
```

## 使用方式

### 动态加载（零安装 · 会话级 · 重启失效）

DSH 会话中由 Agent 通过 Cordis 工具链加载：

1. `cordis_define` —— plugin 用 `kind: new`、`idPrefix: feishu`（3–6 小写字母语义前缀），code.host 填入 `host.js` 源码、code.client 填入 `client.js` 源码。
2. `cordis_run` —— 首次运行需在界面批准（Client 代码要在页面执行）。
3. 生效后输入区 dock 显示绑定提示；点击侧栏底部「⛓ 飞书 IM」打开 IM 中心 overlay。

### 正式安装（推荐 · 开机自启 · 一次性）

按 waystation npm 正式版的同款流程 —— 详见后续 R4 包发：

```bash
# 待 R4 完成（package/ 目录补全后可用）：
npx --yes @deepseek-ai/dsh plugin --profile web add dsh-feishu-link
```

安装完在 `~/.dsh/profiles/web/cordis.patch.yml` 应有：

```yaml
- insert:
    - id: dsh-feishu-link
      name: 'dsh-feishu-link'
```

刷新浏览器页面（http://127.0.0.1:3080）即生效。

> ⚠ **勿用 `npm install --prefix ~/.dsh/profiles/`** —— 那会把 DS H没声明的包 prune 掉（waystation README 实测事故过）。

## UI 路线（第一性原理）

| 用户场景（MCODE 5 张图）| 我们的方案（路线 A） |
|---|---|
| 图 1 · Agent 列表 + 旁标📱 | IM 中心 overlay 内 Agent 列表视图 + 状态徽标 |
| 图 2 · 聊天框顶部"连接 IM"按钮 | conversation.input.dock 提示条 + 一次性 toast（用户可关） |
| 图 3 · 平台选项弹窗 | IM 中心主面板内"扫码绑定"按钮 + Modal 流程 |
| 图 4 · 扫码二维码 | BindWizardModal · QR + 状态机（scan/waiting/success/failed/timeout）|
| 图 5 · 绑定后图标变化 | IM 中心状态徽标实时更新（30s 自动 refresh）|

**未来升级**：待 DSH 端开口给 `conversation.toolbar.action` / `sidebar.item.action` 等 additive 子 slot 后，可升级到"产品内嵌行级图标"（路线 B）。

## 协议层（已钉死技术栈）

### 我们自己的依赖
- `@larksuiteoapi/node-sdk@^1.73.0`（npm latest，飞书官方 SDK + `WSClient` + `EventDispatcher`）
- `ws@^8.18.0`（Node 直连 WSS 用，被 SDK 间接依赖；显式声明）
- 不复用 `dsh-feishu-connect` npm 包（致命绑定 + 版本缺口 + 无 LICENSE —— 见 `RESEARCH-feishu-connect-health.md`）

### 飞书端点
- `POST https://accounts.feishu.cn/oauth/v1/app/registration` —— 设备流 init/begin/poll
- `POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal` —— token 自动换发
- `POST https://open.feishu.cn/open-apis/im/v1/messages` —— 发消息

### PersonalAgent 应用
绑定时传 `archetype: 'PersonalAgent'`，飞书自动识别为「个人代理机器人应用」并允许用户无须先去开发者后台建 App。

## 测试

```bash
npm run test:fetch        # 自检 lib/fetch.mjs 5 个函数
```

完整验证包括 host 协议层（7 RPC + helper 进程通讯）和 client UI 实操 —— 见后续 R4 的 verify-*.js + ACCEPTANCE.md。

## 路线图

- **P0 ✅ 当前**：单飞书 + 单 Agent + 5 张图完整流程 + 双向消息 + IM 中心（~2300 行代码）
- **P1**：多 Agent 路由 + 富文本卡片（interactive card）+ 群聊 @ 路由
- **P2**：sidebar 行级图标 + 聊天框顶部按钮（待 DSH 端开口）
- **P3**：微信 / 钉钉平台抽象

## License

MIT
