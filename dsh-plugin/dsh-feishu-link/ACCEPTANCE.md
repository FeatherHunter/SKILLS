# ACCEPTANCE · dsh-feishu-link · P0 验收清单

> 仿 waystation v25 ACCEPTANCE.md 范式
> 撰写日：2026-08-14
> 对应：Wayfinder #392（T5 验收任务票）

## 0. 前置

- [x] DSH Web 正常启动（http://127.0.0.1:3080）
- [x] 飞书 App 安装在手机（用于扫码）
- [x] 在带 cordis 工具的会话中 `cordis_define` + `cordis_run` 加载 dsh-feishu-link（pluginId 实例形如 `feishu-1`，packageId `pkg-1`）
- [x] 工作目录 = `D:\2Study\StudyNotes\SKILLS\`（或任意带 git 的目录；不影响插件逻辑）

### 0.1 自检全过

- [x] `node tests/verify-fetch.mjs` —— **32 passed / 0 failed**（lib/fetch.mjs 5 纯 fetch 函数）
- [x] `node tests/verify-ipc.mjs` —— **23+ passed / 0 failed**（lib/ipc.mjs IPC schema + parseLines + writeLine）

## 1. 侧栏入口 + sidebar 入口图标（ADR 决策 4）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 1.1 | 查看侧栏底部 | 出现 `⛓ 飞书 IM` 入口（图标 + 文字） | ☐ 待验 |
| 1.2 | 点 `⛓ 飞书 IM` | 打开 IM 中心 shell.overlay（480×600 浮动窗）| ☐ 待验 |
| 1.3 | 当有 n>0 个 Agent 未绑时 | 入口文字右侧有红点 + 数字徽标；n=0 时不显示 | ☐ 待验 |
| 1.4 | n=10 时 | 徽标显示 `9+` | ☐ 待验 |

## 2. IM 中心主面板（ADR 决策 2 · 图 1/5）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 2.1 | 打开 IM 中心 | shell.overlay 显示"⛓ dsh-feishu-link"标题 + Agent 列表 + "刷新"+"关闭"按钮 | ☐ 待验 |
| 2.2 | 默认无 Agent | 显示说明文字「尚未绑定任何 Agent。下一步：① 创建 DSH Agent；② 输入 Agent ID，点「扫码绑定」」| ☐ 待验 |
| 2.3 | 出现 1 个未绑 Agent | 显示「+ 手动输入 Agent ID 绑定」输入框 + 「绑定」按钮（虚线边框） | ☐ 待验 |
| 2.4 | 输入 Agent ID（如 `coder-1`） + 按 Enter / 绑定按钮 | 弹出 BindWizardModal，含 QR + 倒计时 | ☐ 待验 |
| 2.5 | 已有 Agent（已绑） | 每行：`Agent 名 · app=cli_*** · ● 已绑 · [解绑]` | ☐ 待验 |
| 2.6 | 拖动面板头部 | 面板跟随鼠标移动 | ☐ 待验 |
| 2.7 | 刷新按钮 | 重新拉 agent 列表 | ☐ 待验 |

## 3. BindWizardModal（ADR 决策 · 图 4）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 3.1 | 进入 scan 状态 | 显示 QR code（`<img>` 240×240）+ 倒计时 MM:SS + 浏览器链接 + 「轮询飞书侧状态…」spinner | ☐ 待验 |
| 3.2 | QR 倒计时 | 从 10:00（typical）开始每 1 秒减 1；到 0:00 → 跳到 timeout | ☐ 待验 |
| 3.3 | 手机飞书扫 QR + 飞书侧点「确认 PersonalAgent 应用」 | 状态变为 success（✓ 绑定成功！App ID: cli_***），1.5 秒后自动关闭 modal + 刷新列表 | ☐ 待验 |
| 3.4 | 点 modal 中「取消」 | 状态变为 cancelled，可点「重试」 | ☐ 待验 |
| 3.5 | modal 中「重试」 | 重新开始 bind 流程（新 QR）| ☐ 待验 |

## 4. ConfirmUnbindModal（ADR 决策 5）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 4.1 | 点 Agent 行「解绑」按钮 | 弹出 modal 确认 | ☐ 待验 |
| 4.2 | modal 描述 | "解绑后该 Agent 的飞书消息将不再自动转入 DSH 会话。需要重新扫码绑定才能继续接收飞书消息。" | ☐ 待验 |
| 4.3 | 点「解绑」（红字） | modal 关闭 + 该 Agent 状态变为「未绑」 + 移除 metadata + 清 credentials | ☐ 待验 |
| 4.4 | 点「取消」 | modal 关闭（Agent 状态不变） | ☐ 待验 |

## 5. SettingsPage（settings.plugins.tab「飞书 IM」）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 5.1 | 设置 → 插件 → 「飞书 IM」 | 显示配置页：总览 / WSS 健康 / 已绑 Agent / 说明 | ☐ 待验 |
| 5.2 | WSS 健康状态 | `✓ helper 已就绪（pid XXXX）` 或 `✗ 未就绪（30s 后自动重启）` | ☐ 待验 |
| 5.3 | 「打开 IM 中心」按钮 | 触发 IM 中心 overlay | ☐ 待验 |
| 5.4 | 「手动刷新」按钮 | 重新拉 agent 列表 + helper 健康 | ☐ 待验 |

## 6. BindHint（conversation.input.dock · ADR 决策 1）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 6.1 | 首次进入会话 + 无 Agent 绑飞书 | 输入区上方出现一次性橙色提示条：「尚未绑定任何飞书 IM。打开 IM 中心 · 绑一个 ×」 | ☐ 待验 |
| 6.2 | 点提示条「×」 | localStorage 记录 `dsfl-hint-dismissed`，提示条消失，下次不再出现 | ☐ 待验 |
| 6.3 | 已有 Agent 绑飞书 | 提示条不显示 | ☐ 待验 |

## 7. WSS 长连接健康

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 7.1 | 绑定成功后 | helper 子进程启动 + WSClient 连上 → 30s 内 settings 显示 ✓ helper ready | ☐ 待验 |
| 7.2 | kill helper 子进程 | 3 秒后 host timer 自动重启 → helper ready 恢复 | ☐ 待验 |
| 7.3 | 飞书侧手动断 WSS | helper 内 EventDispatcher 检测 → emit `botClosed` → client 显示「重连中」 | ☐ 待验 |

## 8. 双向消息

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 8.1 | 已绑 Agent 状态下，用手机飞书向机器人发任意文字 | helper 收到消息 → emit `im.message.received` 事件 → client 最近消息缓存增加 | ☐ 待验 |
| 8.2 | model 工具 `im_pull` | model 调用时返回该 Agent 最近 20 条消息（默认），格式 `{ok, count, items}` | ☐ 待验 |
| 8.3 | model 工具 `im_send` | model 调时实际发飞书消息，返回 `{ok, messageId, chatId}` | ☐ 待验 |
| 8.4 | 直接调 `host.call('im.send', {...})` | 同上（不走 model）| ☐ 待验 |

## 9. 跨会话持久化

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 9.1 | 绑定后重启 DSH | 元数据 + credentials 仍存在，绑定的 Agent 列表不变 | ☐ 待验 |
| 9.2 | 切换 worktree / workspace | helper 检测 cwd → reboot 时重新扫描 bindings（自动喂 list）| ☐ 待验 |

## 10. 错误处理

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 10.1 | 没有 internet 时点扫码绑定 | bind 失败，status=failed，UI 显示红色 error 提示 | ☐ 待验 |
| 10.2 | 给一个 agentId 但飞书已存在该 app | bind 成功但 metadata 写入失败 → status=partial（防止数据不一致） | ☐ 待验 |
| 10.3 | model 调 im_send 给未绑 Agent | 返回 `{ok:false, error:{kind:'not_bound'}}` | ☐ 待验 |
| 10.4 | 解绑时不在线（helper 死掉） | credentials + metadata 仍清掉，下次重启 helper 时不会重启该 bot | ☐ 待验 |

## 11. 卸载

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 11.1 | 卸载后再次启动 DSH | 插件不挂载，无 UI 残留 | ☐ 待验 |

## 12. 验收签收

```
PASS 数：
FAIL 项：
  现象：
  处理：
验收人：FeatherHunter（本人验收）
日期：2026-08-14
```

---

## 自检命令汇总

```bash
# 验证 lib
npm run test:fetch       # 32 passed
npm run test:ipc         # ~23 passed

# 验证 host 协议层（动态加载时手测）
# 通过 7 RPC 接口验证（在 cordis 会话里手动调）

# 验证 npm 安装版（如已发布）
npx --yes @deepseek-ai/dsh plugin --profile web add dsh-feishu-link
# 刷浏览器 → 设置 → 插件 → 飞书 IM 应出现
```
