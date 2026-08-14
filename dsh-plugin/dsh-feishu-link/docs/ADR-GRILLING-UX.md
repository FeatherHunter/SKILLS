# ADR · dsh-feishu-link grill 决策（自决 6 条 UX）

> ADR = Architecture Decision Record
> 决策方：父会话（用户授权"没有参考的你拿最优质推荐方案"）
> 决策日：2026-08-14
> 对应：wayfinder #391 (T4 grilling)

---

## 决策 1 · BindHint 触发时机

**默认：A. dock 提示 + 不自动展开；首次 toast 一次性提示，可关闭**

- 路径：用户进入未绑 IM 的 Agent 会话
- 行为：
  1. `conversation.input.dock`（`dsfl-dock` 组件）显示一行提示条：「Agent X 尚未绑定飞书 [打开 IM 中心] [×]」
  2. 同时一次性 toast：「该 Agent 未绑飞书 IM，可点 IM 中心开始绑定」+ 复选框「不再提醒」（localStorage 持久化）
  3. 不自动展开 shell.overlay（避免用户的 IM 中心被打断）
- 兜底：如果用户关掉了 toast，本提示条仍在 dock 显示，直到 Agent 绑上
- **为什么不用 B（自动展开）**：DSH 主对话区是「用户的 Agent 思考/写作」流，自动展开 IM 中心会强行夺焦。MCODE 也是 dock 提示模式（不抢输入框）

## 决策 2 · IM 中心 overlay 形态

**默认：B. 480×600 浮动窗（仿 waystation v25/v26 范式）**

- 路径：`shell.overlay` 注册 `id: 'dsfl-overlay'`
- 默认大小：width 480px × height 600px；位置默认左上 (24, 80)
- 8 向缩放（min 340×240 / max 900×920）—— 与 waystation 完全一致
- 标题栏：「dsh-feishu-link」+ repo 状态徽标 + 关闭按钮 + 「置右停靠」/「悬浮」切换（沿用 waystation v26 风格）
- 内容：单视图 = Agent 列表（不像 waystation 的三视图那么复杂，因为 dsh-feishu-link 单一职责）

## 决策 3 · 状态徽标颜色（YIQ 感知亮度自适应）

**默认：5 色 + YIQ 自适应（沿用 waystation v16-17）**

| 状态 | 颜色（light/dark） | 自适应规则 |
|---|---|---|
| **已绑成功** | `#3fb950` | YIQ > 0.6 时文字用白，否则用黑 |
| **重连中** | `#f0883e` | 同上 |
| **失败** | `#f85149` | 同上 |
| **扫码中** | `#f1c40f` | 同上 |
| **未绑** | `#8b8b95` | 同上 |

- 主题色固定（不依赖 alias CSS variable）—— waystation v14-5 教训：dark 主题下 alias 变量会解析成深色导致黑底黑字
- 文字色按 `getComputedStyle(theme)` + YIQ 公式自适应

## 决策 4 · 侧栏入口红点

**默认：D. n>0 显示数字徽标；n=0 不显示（避免红点噪音）**

- 路径：`sidebar.footer.action` 注册 `id: 'dsh-feishu-link'`
- 图标：🪢（链条 emoji，呼应 "link" 主题）；旁加红点（n>0）
- 红点形式：
  - n=0：不显示（避免噪音）
  - 1≤n≤9：圆形红点 + 数字（白色）
  - n>9：圆形红点 + 「9+」
- 鼠标悬停 tooltip：「n 个 Agent 未绑飞书」

## 决策 5 · 解绑确认弹窗

**默认：B. 单按钮「解绑」主按钮 + 「取消」次按钮 + 「重新扫码」小链接**

- 弹窗 modal（复用 shell.overlay 居中）
- 标题：「解绑 Agent X 的飞书机器人？」
- 描述：「解绑后该 Agent 的飞书消息将不再自动转入 DSH 会话。需要重新扫码绑定才能继续接收飞书消息。」
- 按钮：左 [取消] | 右 [解绑]（红色次按钮）
- 右下角小字：[重新扫码绑定]（链接，不解绑直接启动 wizard）

## 决策 6 · P0 vs P1 切割

**默认：**

| 阶段 | 包含 | 不包含 |
|---|---|---|
| **P0**（本次实施） | 扫码绑 + 长连接 + 双向单消息 + 单 Agent + 5 组件 shell.overlay + 设置页 + 提示条 + npm 双形态发布 | 多 Agent / 富文本卡片 / 群聊路由 / 跨平台 / Webhook 兜底 |
| **P1**（下一阶段） | 多 Agent + 多 IM 池 + 富文本卡片（interactive card） + 群聊 @ 路由 + 自动重连 | webhook event 兜底（Electron 长连接崩溃场景） |
| **P2**（远期） | sidebar 行级图标 + 聊天框顶部按钮（**等 DSH 端开口给 additive 子 slot**） | — |
| **P3**（更远） | 微信 / 钉钉 / Telegram 平台抽象 | — |

- **为什么这样切**：把"快闭环 + 能用"放 P0（~2300 行）；增量改进放 P1；DSH 端产品决策驱动的功能放 P2；多平台放 P3

---

## ADR 结论

6 条全部按 waystation 范式 + 第一性原理拍板，所有默认值已落地到 #391 的 resolution comment。

**此 ADR 在实施中如遇具体 UX 抉择，仍可在 #391 内 reopen 讨论或新开 grill 子票。**
