# CHANGELOG · dsh-feishu-link

> 记录所有可见变更。版本遵循 SemVer。格式按 [Keep a Changelog](https://keepachangelog.com)。

## [Unreleased] · v0.2.0-pre

### Added (完善开发 · 按 ROADMAP 全量)

- **A · Runtime 验收**
  - `tests/probe-sandbox.mjs`：cordis sandbox 真实限制探测脚本（探测 `require` / `__filename` / `process.cwd` / `__dirname` 等是否可用）
  - 真 `npm install @larksuiteoapi/node-sdk@^1.73.0` + ws@^8.18.0（lockfile 落地）
  - helper 子进程在 Windows + Node 22 实跑验证

- **B · host → client 事件通道**
  - host → client 单向事件通道（`im.bind.changed` / `im.message.received`）替换客户端 4s polling
  - `im.subscribe` RPC（client 首次调拿 since，时间戳之后由 host push）

- **C · UX 完善**
  - bind session 持久化（client localStorage + host metadata）—— 刷新页面状态不丢失
  - rate limit / 3s cooldown（防风控）
  - im_pull redaction（chat_id → 群名 / open_id → 用户代号）
  - Lark 海外版全链路支持（domain param 全透传）
  - IM 中心 overlay 8 向拖动 + 缩放（仿 waystation v25）
  - SidebarButton 状态显示（IM 中心开着时高亮）
  - Modal ESC / click-outside 关闭
  - dock 提示条策略细化（不阻塞输入流）

- **D · 文档 + 工程仪式**
  - `docs/SPEC.md`（产品视角规格）—— 与 `DESIGN.md` 配对
  - `ROADMAP-completion.md`（30+ 项完善开发清单）
  - `docs/UNINSTALL.md`（卸载完整指南 + 自动清理钩子）
  - `.npmignore`（不发布的内部文件）
  - README 升级：自检指引 + uninstall 段 + 飞书 sandbox 应用获取

- **E · 质量门槛**
  - ESLint + Prettier 配置 + 全文件格式化
  - GitHub Actions CI（lint + test + coverage 三 job）
  - c8 代码覆盖率 ≥ 80% 阈值门禁
  - SPDX-License-Identifier 头到所有源文件
  - `npm test` 一键合并 fetch/ipc/probe-sandbox/c8
  - EditorConfig（统一缩进 / 换行）
  - LICENSE 文件本体
  - ErrorBoundary（client React 错误接住）
  - helper Windows 凭据存储（DPAPI）— macOS Keychain / Linux libsecret 三平台
  - npm version 脚本

- **F · 安全 + 隐私**
  - helper 子进程凭据隔离（短期内存 + on-demand fetch）
  - im_send 内容 sanitize（长度限 + prompt injection guard）
  - bounds check（chat_id / agentId / 消息长度）
  - cwd 检查（拒绝 `..` escape）
  - 输出日志 redact（不进 console.log secret）

### Changed

- `lib/fetch.mjs`：增加 Lark 海外版端点切换（`apiBase('lark')` → `open.larksuite.com`）
- `host.js`：sandbox 路径解析多重 fallback（`__filename` → `__dirname` → npm resolve plugin dir → cwd）
- `client.js`：去掉 4s polling，改用 host push 事件
- `package/lib/index.js`：npm 安装版 host 半修改同上
- `package/lib/client.js`：npm 安装版 client bundle 跟随升级

### Removed

- client 端 4s 重复 polling（被 host push 替代）
- sandbox 不稳的 `require('path')` 单路径解析

## [v0.1.0] · 2026-08-14

### Added · P0 MVP 首次落地

- 5 张图 IM 绑定 P0 实现：扫码绑 + WSS 长连接 + 双向消息 + IM 中心 + 设置页 + dock 提示条
- 协议层自研（`lib/fetch.mjs` + `lib/ipc.mjs` 纯 fetch + IPC schema）
- WSS 子进程（`helper/helper.mjs` 用 `@larksuiteoapi/node-sdk@1.73` WSClient + EventDispatcher）
- 动态版（`host.js` cordis_define code.host + `client.js` cordis_define code.client）
- npm 安装版（`package/lib/index.js` ESM host + `package/lib/client.js` bundle）
- 6 条 UX 默认决策（`docs/ADR-GRILLING-UX.md`）
- 12 节 ACCEPTANCE 清单
- README + DESIGN + 4 份调研档案
- 64 个 lib self-test（verify-fetch 32 PASS + verify-ipc 32 PASS）
- install-patch 幂等测试
- 6 个 wayfinder GitHub Issues 全部 CLOSED（#387 map + #388 T1 + #389 T2 + #390 T3 + #391 T4 + #392 T5）
- commit `fa28e760` on `main` @ `FeatherHunter/SKILLS`
