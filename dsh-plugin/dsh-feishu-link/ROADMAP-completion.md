# dsh-feishu-link · 完善开发 ROADMAP

> 起始 commit: `fa28e760`（v1 基础版本）
> 起始日期: 2026-08-14
> 启动指令: 用户授权「不搞最小需求开发 · 搞最完善的开发 · 从第一性原理出发对抗式审查全部搞定」
> 状态: 工程铭文，标记每一项完成

按用户授权，本 ROADMAP 是对抗式审查（详见 commit `fa28e760` 期间的 chat REVIEW 报告）的全量执行清单，**不分 P0/P1/P2，全部都做，每项都做到可验证**。

---

## A · 真实环境验收（Runtime / 真测）

- [ ] **A1** `npm install` 实跑 @larksuiteoapi/node-sdk 真装一次（验证 lockfile + native deps）
- [ ] **A2** helper.mjs 真 spawn 在 Windows + Node 22 起 WSS（用 sandbox 飞书账号）
- [ ] **A3** cordis sandbox 真实限制探测（`tests/probe-sandbox.mjs` —— `require` / `__filename` / `process.cwd` 真能用列表）
- [ ] **A4** DSH 真实 API schema 核对（subprocess.spawn / credentials.set / harness.handleEvent / tools.register 真签名）

## B · host → client 事件通道

- [ ] **B1** 实现 host → client 单向事件（替代 client 端 polling）
- [ ] **B2** 砍 client 端 4s 重复 polling

## C · UX 完善

- [ ] **C1** bind session 客户端持久化（localStorage + host 端 SQLite-like metadata）
- [ ] **C2** rate limit / cooldown（按钮 + 服务端防爆）
- [ ] **C3** im_pull redaction（敏感字段屏蔽：open_id / chat_id / 内部 token）
- [ ] **C4** Lark 海外版全链路支持（domain 参数从 RPC 到 fetch.mjs 全透传）
- [ ] **C5** IM 中心 overlay 拖动 + 缩放（仿 waystation v25 范式）
- [ ] **C6** SidebarButton 状态显示（IM 中心开着时高亮）
- [ ] **C7** Modal 居中 / ESC 关闭 / click-outside 关闭
- [ ] **C8** dock 提示条插入策略细化（不阻塞输入流）

## D · 文档 + 工程仪式

- [ ] **D1** SPEC.md（产品视角规格 · vs DESIGN.md 实现视角）
- [ ] **D2** CHANGELOG.md（v0.x 变更轨迹）
- [ ] **D3** README 升级：自检指引 + 卸载段 + 飞书 sandbox 应用获取指引
- [ ] **D4** .npmignore（不发布的内部文件）
- [ ] **D5** uninstall 清理脚本（DSH plugin remove + 清 ~/.dsh/im-bindings + credentials + restart helper）
- [ ] **D6** docs/UNINSTALL.md（卸载完整指南）
- [ ] **D7** package.json `keywords` + `homepage` + `bugs` + `files` 精细

## E · 质量门槛

- [ ] **E1** eslint + prettier 配置（airbnb-base 或 standard）
- [ ] **E2** GitHub Actions CI（lint + test + coverage 三 job）
- [ ] **E3** code coverage 报告（c8 / istanbul ≥ 80% 阈值门禁）
- [ ] **E4** SPDX-License-Identifier 头到所有源文件
- [ ] **E5** 一键 `npm test`（合并 verify-fetch + verify-ipc + probe-sandbox + sandbox mock）
- [ ] **E6** cross-platform 注释（macOS / Linux 注意路径差异）
- [ ] **E7** client 端 React ErrorBoundary
- [ ] **E8** helper Windows 凭据存储（DPAPI）— macOS Keychain / Linux libsecret 三平台
- [ ] **E9** npm version 脚本（自动 bump + tag）
- [ ] **E10** LICENSE 文件本体（独立 LICENSE 文本）
- [ ] **E11** .editorconfig（统一缩进 / 换行）

## F · 安全 + 隐私

- [ ] **F1** helper 子进程凭据隔离（不要 secret 长期驻留 host 内存）
- [ ] **F2** im_send 内容 sanitize（prompt injection guard）
- [ ] **F3** 必要 bounds check（chat_id / agentId 长度 / 消息长度）
- [ ] **F4** cwd 检查（拒绝路径 escape）
- [ ] **F5** helper 子进程用户权限降级（run as less-privileged user）
- [ ] **F6** 输出日志 redact（不让 secret 进 console.log）

## G · 最终真实验收（用户驱动）

- [ ] **G1** `npm install` 一次性成功
- [ ] **G2** cordis sandbox 探测脚本真跑（用户提供 DSH 环境跑）
- [ ] **G3** DSH 会话最小路径验证（用户加载插件 + 调一次 im.health）
- [ ] **G4** 飞书真设备流端到端（用户在带 cordis 工具的 DSH 会话里扫码）
- [ ] **G5** ACCEPTANCE.md 12 节实物核对（用户在 DSH Web 界面跑）

---

## 进度追踪

- [x] R0: ROADMAP + lint config + SPEC + CHANGELOG + README 升级 + .npmignore + UNINSTALL + probe-sandbox + 部分 lib 改进
- [ ] R1: host.js 升级（sandbox 兜底 + Lark + cooldown + 持久化 + redaction）
- [ ] R2: client.js 升级（持久化 + cooldown + redaction + 拖动缩放 + Modal UX + 状态 + 砍 polling）
- [ ] R3: package/ 跟随升级（lib/index.js + lib/client.js + uninstall script）
- [ ] R4: helper.mjs 升级（Windows 凭据 DPAPI + 子进程身份降级）
- [ ] R5: CI（GitHub Actions workflow）+ c8 coverage + 一键 verify
- [ ] R6: G 验收（依赖用户 DSH runtime / 飞书账号配合）
- [ ] R7: 收尾 commit + 全程验收总结
