# DSH-Waystation · P0 验收清单（ACCEPTANCE）

> 用途：本插件开发已完成（代码 + host 逻辑层测试 43/43 PASS），**运行时验收尚未执行**——
> 需要带 cordis 工具（`cordis_define` / `cordis_run` / `cordis_inspect_self`）的会话加载插件后逐项打勾。
> 全部 PASS → map #342 正式收尾；任一项 FAIL → 记录现象与修复后重跑。
> 对应：map #342 Destination 验收段 + ticket #361（新会话增强）。

## 0. 前置

- [ ] 在带 cordis 工具的会话中 `cordis_define` + `cordis_run` 加载 `dsh-plugin/dsh-waystation`（pluginId 前缀 `wfst`）
- [ ] 工作目录 = 本仓库（D:\2Study\StudyNotes\SKILLS）

## 1. 前置就绪绿点检查（#344）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 1.1 | 查看输入区上方状态条 | 显示「● 就绪 n/8」+ 更新时间 + 标签「真数据」 | ☐ |
| 1.2 | 展开面板「⚙ 就绪」页 | 8 项绿点：1-6 应 🟢（仓库定位 FeatherHunter/SKILLS、setup、tracker=GitHub、gh CLI 路径、登录、API 200）；7/8 应 🟡「已安装但未挂载到当前会话」+ 修复提示「用 /wayfinder 加载」 | ☐ |
| 1.3 | 点「↻ 重新检查」 | 刷新成功，时间戳更新 | ☐ |
| 1.4 | （可选）临时目录场景 | 无 issue-tracker.md 时 1-3 显示 🔴 + 琥珀横幅「帮我执行 /setup-matt-pocock-skills」按钮 | ☐ |

## 2. GitHub wayfinder 面板（#346）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 2.1 | 侧栏脚部「Waystation」入口 / 点状态条「● 就绪」 | 面板开合正常（可拖动、可调大小） | ☐ |
| 2.2 | 地图列表页 | 显示全部开放 wayfinder:map（动态枚举，非硬编码）；每行：标题 + Destination（缺省显示「未填写」）+ 进度 n/N + 可接数 | ☐ |
| 2.3 | 进入 map #342 详情 | Destination/Notes 常显；Decisions so far / 战雾 / Out of scope 折叠块可展开；✅已关闭组默认折叠（#348 Q1 拍板） | ☐ |
| 2.4 | 票务分组核对 | 与 GitHub 页面一致：🟢可接（open+无阻塞+未认领）/ 🔵已认领 / 🔒被阻塞（列阻塞来源名）/ ✅已关闭 | ☐ |
| 2.5 | 点「↻ 刷新」 | 全量重建成功，时间更新 | ☐ |

## 3. 开始此 Issue（#347 + 新会话增强 #361）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 3.1 | 任一张可接票点「▶ 开始此 Issue」 | 确认框：类型 chip + 标题 + 推荐技能 + 认领开关 + 新会话提示条 + 「同时在新会话中打开」开关（默认开） | ☐ |
| 3.2 | 勾选认领 + 新会话，点确认 | GitHub assignee 更新为当前用户；**新会话创建**（cwd = 当前仓库）→ **自动命名** `[dsh-waystation] <标题> #<号>` → 切换/提示切换；指令已就绪（剪贴板或输入框） | ☐ |
| 3.3 | 注入文本内容 | 含 `/wayfinder` + issue 链接 + 「⚠️ 本 ticket 应在独立的新会话中执行」提醒 + 命名建议 | ☐ |
| 3.4 | 新会话中发送指令 | 新会话按 wayfinder 流程工作（工作目录 = 仓库） | ☐ |
| 3.5 | （降级路径）sessions 不可用 | 提示手动开新会话 + 命名建议；注入文本仍含提醒 | ☐ |

## 4. 平台契约实测（#361 运行时项）

| # | 项 | 预期 | 结果 |
|---|---|---|---|
| 4.1 | `ctx.get('sessions')` 注入 | client 插件可取到 ISessions（create/open/scope/sessionOf） | ☐ |
| 4.2 | `sessions.create({cwd})` | 新会话 cwd = 当前仓库目录（不带 cwd 走 host 默认项目目录——已显式传） | ☐ |
| 4.3 | `rename` 规范化 | `[dsh-waystation] <标题> #<号>` 被接受；超长标题的截断/拒绝行为记录 | ☐ |
| 4.4 | `sessions.open(sid)` | UI 实际切换到新会话（或确认需手动切换） | ☐ |
| 4.5 | 切换后指令传递 | 剪贴板兜底生效（新会话输入框粘贴可用） | ☐ |

## 5. 结论

```
PASS 数：____ / 全部
FAIL 项：
  现象：
  处理：
验收人：
日期：
```

---

> 关联：map #342（[实施 map · DSH-Waystation P0 落地](https://github.com/FeatherHunter/SKILLS/issues/342)）
> 测试：node dsh-plugin/dsh-waystation/tests/verify-status.js && node dsh-plugin/dsh-waystation/tests/verify-panel.js（host 逻辑层，可随时重跑）