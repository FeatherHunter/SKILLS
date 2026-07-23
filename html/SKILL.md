---
name: html
description: "AI 回复格式约束（全局生效）。当 agent 给用户回复时，遵循本 skill 规定的短答/长答判据与 HTML 触发条件，让回复层次清晰、重点突出。触发词：/html（用户显式要求按 HTML 风格回复时使用）、回复格式、AI 回复、消息格式。**不处理**回复格式之外的其他 HTML 任务（生成产品落地页、PPT 网页版等），那些是 visual-page 技能的事。"
---

# html — 回复格式约定

## 定位

**全局风格约束**。所有 agent 在生成给用户的回复时，默认应参考本 skill 决定"用文字还是用 HTML 文件"以及"HTML 长什么样"。

- **生效范围**：所有 agent 的所有回复（默认遵守）
- **显式触发**：用户说 `/html` 时强制加载确认
- **不归本 skill 管**：用户主动要求"生成一个产品落地页/数据看板/PPT 网页版"等**HTML 文件作为交付物**的任务——那些走 visual-page 技能

---

## 短答 vs 长答

### 短答（默认）
- 长度：≤ 3 句
- 形式：直接对话，不发 HTML 文件
- 适用：简单确认、提问、列表项 ≤ 2 个

### 长答
- 长度：对话里 5-10 句**重点摘要** + HTML 文件发完整内容
- 形式：对话里只写重点摘要和想问用户的问题；用 `<media src="..." type="file" />` 发 HTML
- 适用：以下任一条件触发

**HTML 触发条件**（满足任一即生成 HTML）：

| 条件 | 说明 |
|------|------|
| 表格 | 涉及多个并列项的结构化对比 |
| 列举 ≥ 3 | 一次回答里要列 3 个以上条目 |
| 流程 ≥ 3 步 | 涉及多步骤的操作/方法/路径 |
| 架构原理对比 | 需要解释概念差异、技术选型、方案对比 |
| 代码片段 | 包含可执行的代码示例 |
| 跨 session 存档 | 内容需要后续跨 session 继续接力时 |

**短文不抄 HTML 内容**——对话里的摘要只挑重点 + 待用户确认的问题。

## HTML 文件自动打开（长答交付时）

agent 生成 HTML 文件后，**应主动尝试在用户本地浏览器中打开**，不只是交付文件本身。

### 浏览器优先级

| 优先级 | 浏览器 | 探测路径 |
|---|---|---|
| 1 | **Chrome** | `C:\Program Files\Google\Chrome\Application\chrome.exe` 等 |
| 2 | Edge | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` |
| 3 | Firefox / Safari | 系统默认浏览器 |
| 4 | 默认浏览器 | OS 默认关联 |

### 跨平台推荐命令

**Windows（PowerShell，最稳）**：
```powershell
$chrome = Get-ChildItem 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
$url = 'file:///C:/Users/<encoded>/output/file.html'
if ($chrome) {
  Start-Process $chrome.FullName -ArgumentList $url
} else {
  Start-Process $url  # 退化: 默认浏览器
}
```

**macOS**：`open -a "Google Chrome" file:///...`

**Linux**：`google-chrome file:///...` 或 `xdg-open file:///...`

### 已知陷阱（自检清单）

- ❌ **`cmd.exe /c start chrome "..."`**：引号陷阱，URL 会被 URL-encode 进 `http://"..."` 乱码
- ❌ **把含中文的路径直接传给 shell**：PowerShell 中文参数 → Python subprocess 列表传参
- ❌ **`--no-sandbox`**：除非调试环境，否则有安全风险
- ✅ **用 `file:///` 协议**而非路径直传，确保浏览器解析本地文件
- ✅ **路径 URL-encode**：中文/空格必须编码

### 失败处理（必须实现）

- Chrome 未找到 → 退化到 Edge
- Edge 未找到 → 退化到默认浏览器（`start file.html`）
- 所有尝试失败 → 仅凭 `<media src="...">` 交付，告知用户"已生成 HTML，请手动打开"
- **不要报错阻塞对话**——浏览器打不开不应阻止用户拿到文件

### 与其他规则的关系

- `visual-page` 技能生成的落地页 **不要** 自动打开（用户可能还在设计阶段）
- `minimax-pdf` 生成的 PDF **不**走浏览器打开（用 PDF 阅读器）
- 只对**长答交付给用户阅读**的 HTML 触发自动打开

--

## HTML 视觉风格

### 设计基线
- **浅色 Apple 风**：白底为主
- **主色**：蓝色重点（链接、强调、按钮、关键数据）
- **形状**：圆角（按钮、卡片、徽章、引用块）
- **留白**：充足，不要堆得过密

### 允许使用的 HTML/CSS/JS 元素
让重点突出，**充分用**这些能力：

| 能力 | 适用场景 |
|------|----------|
| 目录（TOC） | 长内容首屏给用户看完整结构 |
| 折叠（details/summary） | 次要说明、可选步骤、补充信息 |
| 锚点（anchor） | 长内容跨章节跳转 |
| 回到顶部 | 滚动后方便用户回到目录 |

### 设计原则
- 风格上像**设计师做出来的页面**，不是把 Word 文档贴成 HTML
- 颜色不超过 3 个主色（白 + 蓝 + 灰阶）
- 字号层次清晰：标题、章节、正文、辅助 4 级足够
- 动效克制：能用 CSS 解决就别上 JS

### 设计师层面提示词（给 agent 的指引）
- 你是一位产品设计师 + 前端工程师的合体
- 给出的 HTML 要像 Apple 官网 / Linear 文档 / Stripe 文档那种克制感
- 优先使用系统字体（-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei"）
- 卡片用 box-shadow 表达层次，不要用粗边框
- 强调用蓝色（#007AFF 蓝或 #0A84FF 蓝），不要用大段彩色
- 表格用斑马纹或悬停高亮，让扫读更轻松
- 响应式：手机（375px）、平板（768px）、桌面（1024px+）都要正常显示

---

## 错误模式（agent 自我检查）

以下行为**违反**本约定，agent 写完应自查：

| 错误模式 | 怎么改 |
|---------|--------|
| 长答案用大段纯文字 | 拆成对话摘要 + HTML 文件 |
| HTML 里把对话内容原样抄一遍 | 对话只写摘要，HTML 才是完整版 |
| 用了红/绿/黄/紫等多种颜色 | 蓝色为主 + 灰阶辅助 |
| 边框粗、阴影重、配色杂 | 浅色 + 圆角 + 留白 |
| 列举 3+ 项没用 HTML | 转成 HTML 文件 |
| 表格内容塞在 markdown 里 | 转成 HTML 表格 |
| 跨 session 内容没有存档 HTML | 补一份 HTML 给用户 |
| 把"生成落地页"任务也按回复格式处理 | 那是 visual-page 技能，不归本 skill |

---

## 与其他技能的关系

| 技能 | 关系 |
|------|------|
| `visual-page` | 显式生成 HTML 交付物时用，本 skill 不管 |
| `humanizer` | 文风去 AI 味，与本 skill 互补（先格式后文风） |
| `minimax-pdf` | PDF 报告走它，HTML 走本 skill 或 visual-page |

---

## Stop 条件

- [ ] 确认回复属于"短答"还是"长答"
- [ ] 长答写了对话摘要（5-10 句）+ HTML 文件
- [ ] HTML 用 `<media src="..." type="file" />` 发送
- [ ] **主动尝试用本地浏览器打开 HTML（Chrome 优先）**
- [ ] HTML 视觉符合"浅色 Apple 风"基线
- [ ] 没用红绿黄紫等多色
- [ ] 没把"生成落地页"任务错误地按回复格式处理
