# dsh-Opencode TUI 主题

> 一个为 DSH（DeepSeek Harness）Web 界面开发的主题插件（Client 端），
> 让整个对话界面的文字样式复刻 opencode TUI 的观感。
> 这不是 TUI 插件，只是一个改字体、颜色、字号、代码风格的主题插件。

- **插件包名**: `dsh-opencode-tui-theme`（可分发 npm 包，见 `package/`，当前 v1.1.0）
- **动态版 pluginId**: `ocode-2`，显示名 `dsh-Opencode TUI 主题`
- **平台**: Client（浏览器页面）
- **两种形态**: ① 动态插件（进程内，会话级）；② 正式安装的本地插件（开机自启，推荐）

## 功能

| 维度 | 效果 |
|---|---|
| 背景 | 统一为截图背景色 `#0a0a0a`（像素采样确认，所有表面层同色） |
| 正文颜色 | 浅灰 `#d4d4d4`，次级 `#a1a1aa`，弱化 `#8b8b95` |
| 标题 | 淡紫 `#c084fc`（h1–h6，含字号层级 16/15/14px） |
| 内联代码 | 翠绿 `#4ade80` 等宽（`code:not(pre code)`），无背景芯片（opencode TUI 同款） |
| 代码块 | 柔和浮起 `#131316` + 横幅（复制按钮模块）`#19191d`，无硬边框，12px 圆角，One Dark 语法高亮（shiki token） |
| 字号 | 正文 13px、行高 22px（可切换 12/14px） |
| 字体 | 正文无衬线（忠实模式）/ 全等宽（终端模式），代码等宽 5 种预设 |
| 状态色 | 成功翠绿、警告琥珀、错误红 |

## 使用方式

### 方式一：正式安装（推荐 · 开机自启 · 一次性）

把 `package/` 目录作为标准 npm 包安装进 DSH profile（本机已装好）：

1. 复制 `package/` 全部内容到 `~/.dsh/profiles/node_modules/dsh-opencode-tui-theme/`
   （`~/.dsh` 即 `$DSH_HOME`；新用户在自己的机器上做同样一步）。
2. 在 `~/.dsh/profiles/web/cordis.patch.yml` 追加注册行（**无需重启 DSH**，
   配置文件热加载；刷新浏览器页面即生效）：

   ```yaml
   - insert:
       - id: opencode-tui-theme
         name: 'dsh-opencode-tui-theme'
   ```

3. 刷新浏览器页面。之后每次 DSH 启动主题自动生效，**无需任何审批**。
4. 卸载：删掉 patch 里的 insert 行 + 删除 `node_modules/dsh-opencode-tui-theme/`。

> **v1.1.0 起正式安装版自带控制面板**：设置 → 插件 → 「Opencode 主题」标签页，
> 提供 ● 已启用/○ 已停用 状态、启用/停用开关、正文模式/字号/代码字体调节，
> 以及一行「实测 body → …」生效自检（getComputedStyle 实测背景/字体/字号）。
> 若该标签页能打开，说明插件已在本浏览器挂载。

> 原理：DSH 的 `dsh.client` 插件机制（`dsh-client-modules`）会扫描组合里声明了
> `dsh.client: { platform: 'web' }` 的包，把 `exports["./client"]` 指向的 bundle
> 伺服为 `/plugins/<id>/client.js` 并注入 `window.__DSH_BOOT__`，浏览器内核在启动
> 时自动挂载该插件条目。包内的 `dsh.client.inject` 保证 `theme` 服务（由
> `@deepseek-ai/dsh-client-ui-theme` 提供）先于本插件加载。

### 方式二：动态加载（零安装 · 会话级 · 重启失效）

在 DSH 会话中由 Agent 通过 Cordis 工具链加载：

1. `cordis_define` —— plugin 用 `kind: new`、`idPrefix: ocode`，code.client 填入
   [client.js](./client.js) 的内容（即本仓库 `client.js` 文件的函数体）。
2. `cordis_run` —— 首次运行需在界面批准（安全机制，Client 代码要在页面执行）。
3. 生效后 Run 卡片内出现「🖥 Opencode TUI 主题」控制面板：
   - 正文模式：无衬线（忠实）/ 全等宽（终端）
   - 字号：12 / 13 / 14 px
   - 代码字体：JetBrains Mono / Cascadia Code / Fira Code / SF Mono / Consolas
   - 启停按钮：随时还原默认外观

## 实现原理

- **颜色 token**：`theme.overrideTokens(source, tokens)` 覆盖 13 个注册主题 token
  （`--dsw-alias-*`），light/dark 均为深色终端值。
- **CSS 层变量**：`styles.insert(css)`（动态版）/ `<style>` 标签（安装版）注入：
  - 文字层级 `--dsw-alias-label-tertiary/caption/dimmed`
  - 代码风格 `--dsw-alias-markdown-code-block(-banner)`、`markdown-inline-code`
  - 语法高亮 `--shiki-token-*`（One Dark 配色）
  - 字号层级 `--dsw-font-markdown-*`（h1/h2/h3/base/small）
  - 字体根变量 `--dsw-font-family` / `--ds-font-family-code`
- **标题紫色**：DSH markdown 容器只给标题设字号不设颜色（继承正文白色），
  故用 `body h1..h6 { color: #c084fc }` 显式覆盖。
- **代码块分层（opencode TUI 风格）**：无硬边框、无芯片——靠柔和亮度阶梯
  L0 聊天画布 `#0a0a0a` < L1 代码块 `#131316` < L2 横幅 `#19191d` + 12px 圆角定义模块。
- **内联代码无芯片**：`--dsw-alias-markdown-inline-code: transparent`，
  纯翠绿文字，去掉产品默认的圆角背景块（刺眼来源）。
- **内联代码绿色**：`code:not(pre code) { color: #4ade80 !important }`
  （`pre code` 保持 shiki 语法高亮）。

## 文件

- `client.js` —— 动态版源码（cordis_define 的 `code.client` 函数体，含控制面板）
- `package/` —— **可分发插件包**（正式安装用，标准 npm 包结构）
  - `package.json` —— 包声明：`dsh.client`（platform web / immediately / inject ui-theme）
  - `lib/index.js` —— 宿主半（no-op，保证 loader 条目可挂载）
  - `lib/client.js` —— 浏览器半 bundle（`window.__ModuleLoader__.load` 注册格式，
    v1.1.0 起 = 主题核心 + 设置面板；默认全等宽 13px JetBrains Mono）
- `README.md` —— 本说明

## 备注

- **v1.0.0 已知 bug（已修复）**：旧 `lib/client.js` 把卸载清理写进
  `ctx.effect(fn)` 的函数体，而 cordis 语义是 fn 立即执行、返回值才是清理器，
  导致样式注入后立即被移除（清单里 active 但界面无变化）。v1.1.0 已修复；
  npm 上若仍是 1.0.0，请用本仓库 `package/` 覆盖安装。
- 要改默认参数直接编辑 `package/lib/client.js` 顶部的 `mode / size / fontKey`；
  安装版面板可实时调节，无需改文件。
- 若动态版（方式二）与正式安装版同时生效，两者 token 层不同源、互不冲突，
  视觉一致；建议保留正式安装版即可，动态版 `cordis_stop` 掉。
- pnpm 下次重装 profile 依赖时可能清理 `node_modules` 下手动放入的包，
  届时按「方式一」第 1 步重新复制即可（或把 `package/` 加入 workspace）。
- 选择器均为通用 HTML 元素级（h1/h2/code/body），未触碰产品私有 DOM class。
- 配色基准来自用户提供的 opencode TUI 截图（mmx 视觉分析）+ One Dark 语法高亮。
