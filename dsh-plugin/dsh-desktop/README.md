# dsh-Desktop · 桌面版

> DSH（DeepSeek Harness）的**桌面壳**：双击打开，像桌面应用一样使用 DSH Web。
> 后台悄悄帮你执行 DSH 服务，你只看得到页面、看不到命令；
> 关掉窗口，后台服务和命令**随之关闭**。
> **零依赖**：无需安装 Node.js / npm —— 应用内置运行时，双击即用。

- **包名**: `dsh-desktop`（目录 `dsh-plugin/dsh-desktop/`）
- **显示名**: 桌面版
- **平台**: Windows / Linux / macOS（Electron 跨平台）
- **技术**: Electron 主进程 = 进程管家 + 内嵌浏览器窗口 + 内置 DSH 运行时

## 功能

| 需求 | 实现 |
|---|---|
| 双击打开，不见后台命令 | 用内置运行时直接拉起 DSH（无终端窗口），页面嵌进应用窗口 |
| **无需安装 Node.js** | 应用捆绑 npm（11MB），首次运行自动 `npm install @deepseek-ai/dsh` 到用户目录，之后用 Electron 内置 Node（ELECTRON_RUN_AS_NODE）直接运行 DSH；系统无需任何 Node 环境 |
| **首次自动安装** | 启动页显示"正在下载并安装 DSH 运行时…"（需联网，几分钟）；装好后**离线可用、秒开** |
| 只看到页面内容 | 窗口内直接加载 `http://127.0.0.1:3080`，菜单栏自动隐藏 |
| **无原生标题栏** | Windows 用 `titleBarStyle: hidden` + 深色悬浮窗口控制按钮（WCO），白色条带消失 |
| **按钮永不遮挡内容** | 页面内容（含 fixed 弹层、Session log 对话框）整体下移 40px 形成「标题栏带」，三个按钮悬浮在空白带上；顶部条带可拖拽移动窗口 |
| **DeepSeek 图标** | 图标取自官方仓库 `deepseek-ai/deepseek-harness` 的 `apps/web/public/favicon.svg`（鱼形 logo），深底白鱼，启动页同款 |
| 关掉应用 = 关掉服务 | 退出时 `taskkill /pid <pid> /T /F`（Windows）或杀进程组（Unix），DSH 整棵进程树一起带走 |
| 服务挂了有交代 | DSH 意外退出/安装失败/启动超时 → 错误页显示原因（中文）+ 最近日志，可一键「重新启动」 |
| 重复打开不打架 | 单实例锁（dev 与打包版共用 `%APPDATA%/dsh-desktop`）：再双击只聚焦已有窗口 |
| 你手动开过 DSH？ | 检测到端口上是真正的 DSH（页面指纹验证）时直接连上，退出时**不会**误杀你自己开的那份 |

## 使用方式

### 环境要求（全新用户必看）

| 要求 | 说明 |
|---|---|
| 系统 | Windows 10/11（Linux 出 AppImage，见下） |
| **无需安装 Node.js** | 应用内置运行时（捆绑 npm + Electron 自带 Node），**只双击 exe 即可** |
| 网络 | **仅首次运行**需联网（自动下载 DSH 运行时，几分钟）；装好后离线可用、秒开 |

### 快速开始（全新用户）

1. 双击 `dsh-desktop-1.0.0-x64.exe`（或 `npm start` 开发模式）
2. 首次运行：启动页显示「正在下载并安装 DSH 运行时…」，等几分钟
3. 自动进入 DSH 界面 —— 完成！之后双击即秒开

> 和官方 `npx @deepseek-ai/dsh web` 完全等价（DSH 官方 Run from npm 前提），
> 只是这一步被桌面版自动完成，不需要命令行。

### 开发 / 日常运行

```bash
cd dsh-plugin/dsh-desktop
npm install      # 安装 electron（首次较慢，~110MB）
npm start        # 启动桌面版
```

> 国内网络若 electron 二进制下载失败（`TypeError: fetch failed`），先设镜像再装：
>
> ```bash
> # PowerShell
> $env:ELECTRON_MIRROR='https://npmmirror.com/mirrors/electron/'
> $env:ELECTRON_BUILDER_BINARIES_MIRROR='https://npmmirror.com/mirrors/electron-builder-binaries/'
> npm install && npm start
> ```

### 打包成双击即用的安装包

```bash
npm run dist     # Windows → dist/dsh-desktop-1.0.0-x64.exe（便携版，双击即用）
```

- Windows 出便携 exe；在 Linux 上执行同一命令出 AppImage（各自平台构建各自的包）。
- 快速验证打包产物：`npm run pack`（`dist/win-unpacked/` 下直接跑 exe，不打安装包）。

## 实现原理

```
双击 exe
  └─ Electron 主进程 main.js
       ├─ 探测 http://127.0.0.1:3080 是否已是真正的 DSH（页面指纹 __DSH_BOOT__）
       │    ├─ 是 → 直接连接现有实例（退出时不杀）
       │    └─ 否（且端口无其他服务）→ 确保内置运行时
       │         ├─ 首次：捆绑 npm（resources/runtime/npm）执行
       │         │    npm install @deepseek-ai/dsh --prefix %APPDATA%/dsh-desktop/runtime
       │         │    （启动页显示安装进度，几分钟）
       │         └─ 已装：跳过安装
       ├─ 用「Electron 内置 Node」直接跑 DSH：
       │    ELECTRON_RUN_AS_NODE=1 <exe> --expose-internals <runtime>/node_modules/
       │        @deepseek-ai/dsh/lib/bin.js web --port 3080
       │    （无需系统 Node；--expose-internals 是 DSH 的 HMR 插件要求）
       ├─ 轮询端口直到就绪（10 分钟超时）→ BrowserWindow 加载页面
       └─ 关窗 → app.quit() → 退出前杀掉整棵子进程树
```

关键点：

- **生命周期耦合**：窗口 = 应用的唯一存在形式。`window-all-closed` 即退出，
  `before-quit`/`process.exit` 兜底杀进程树，没有托盘、没有残留。
  **安装阶段的 npm 子进程同样纳入「关窗即杀」**，任何状态下关窗都不会留下孤儿进程。
- **杀得干净**：Windows 用 `taskkill /T`（递归杀子进程）；Unix 用独立进程组
  `kill(-pid)` 整组击杀（内置运行时是单进程，更干净）。
- **不误杀**：只有「本次由桌面版拉起的 DSH」才在退出时被杀；
  连接的是你手动启动的实例时，退出只关窗口。
- **内置运行时**：Electron 自带完整 Node，`ELECTRON_RUN_AS_NODE=1` 时 exe 本身
  就是 node（实测 v24）；捆绑 npm（11MB）完成安装动作，DSH 原生模块均为
  N-API prebuild，兼容 Electron 内置 Node。
- **标题栏带**：`polishTargetPage` 注入 —— 对 `document.body` 整体
  `translateY(40px)` 并压缩高度，顶部形成 40px 空白带（与页面同色）；
  顶部注入 `-webkit-app-region: drag` 的透明条带供拖拽（`top: -40px`
  抵消位移）。**transform 作用于 body 而非 #root**：body 的 transform 建立新
  包含块，使 portal 到 body 的浮层（Modal 对话框 / 菜单 / Popover，如
  Session log 导出对话框）也统一下移，任何内容都不会被右上角按钮遮挡。
- **单实例锁**：dev（`npm start`）与打包版共用同一 userData 锁；自动化测试
  （`DSH_DESKTOP_SMOKE`/`DSH_DESKTOP_SHOT`）自动跳过锁。
- **日志**：DSH 输出与主进程事件都写入 `%APPDATA%/dsh-desktop/dsh.log`
  （Linux/macOS 为 `~/.config/dsh-desktop/dsh.log`），出错页可直接查看尾部。

## 环境变量（可选）

| 变量 | 默认 | 说明 |
|---|---|---|
| `DSH_DESKTOP_PORT` | `3080` | DSH 服务端口（传给内置 DSH 的 `--port` 与探测地址） |
| `DSH_DESKTOP_COMMAND` | 内置运行时 | 自定义启动命令（整行，按 shell 解析；设置后跳过内置运行时） |
| `DSH_DESKTOP_REGISTRY` | `https://registry.npmjs.org` | 安装 DSH 运行时用的 npm 镜像源（国内可设 `https://registry.npmmirror.com`） |
| `DSH_DESKTOP_REINSTALL=1` | 关 | 强制重新安装 DSH 运行时（用于升级 DSH） |
| `DSH_DESKTOP_SMOKE=1` | 关 | 冒烟模式：页面就绪后自动退出，供自动化验证 |
| `DSH_DESKTOP_SHOT=1` | 关 | 截图模式：页面就绪后做布局自检 + 存 PNG 再退出（`DSH_DESKTOP_SIZE=1280x820` 可调窗口尺寸） |

## 文件

- `main.js` —— Electron 主进程：进程管家（内置运行时安装/拉起/杀进程树）+ 窗口管理（无边框 + 悬浮按钮 + 页面打磨注入）+ 指纹识别与错误翻译
- `preload.js` —— 启动页与主进程的最小 IPC 桥（contextBridge）
- `boot.html` —— 启动中/安装中/错误页（深色风格 + 官方鱼形 logo；含「重新启动/退出」按钮）
- `runtime-resources/npm/` —— 捆绑的 npm（11MB，取自 Node 官方发行版），随应用打包到 `resources/runtime/npm`，负责首次自动安装 DSH
- `build/icon.png` —— 应用图标（官方 favicon 栅格化，electron-builder 自动转 .ico/.icns）
- `build/favicon-official.svg` —— 图标源文件（来自 deepseek-harness 官方仓库）
- `tools/icon-app.html` + `tools/rasterize-icon.js` —— 图标模板与栅格化脚本（`npm run icon` 重新生成）
- `test/smoke-server.js` —— 冒烟测试用假 DSH 服务（验证完整生命周期，不碰真实 DSH）
- `README.md` —— 本说明

## 常见问题

- **双击 exe 没反应 / 提示"已保护你的电脑"**：exe 未签名，Windows SmartScreen 会拦截。
  点「更多信息 → 仍要运行」即可（本地构建产物，安全）。
- **首次启动显示"正在安装 DSH 运行时"很久**：正在下载 DSH 包（数百 MB），
  国内网络可设 `DSH_DESKTOP_REGISTRY=https://registry.npmmirror.com` 用镜像；
  安装失败时错误页会提示原因，点「重新启动」重试。装好后**离线秒开**。
- **如何升级 DSH**：删除 `%APPDATA%\dsh-desktop\runtime` 目录后重新打开，
  或设置 `DSH_DESKTOP_REINSTALL=1` 启动（会重新下载安装最新版）。
- **提示"端口 3080 被其他程序占用（不是 DSH）"**：有别的程序占了 3080。
  关掉它，或用 `DSH_DESKTOP_PORT` 换端口。
- **Linux 双击没反应**：桌面环境（.desktop 启动）的 PATH 可能不含所需命令，
  可用 `DSH_DESKTOP_COMMAND` 指定完整启动方式。
- **不需要 Node.js**：桌面版内置运行时（捆绑 npm + Electron 自带 Node），
  系统无需安装任何 Node 环境。
- **端口上的服务验证**：应用会先验证端口上的服务是不是 DSH（页面指纹
  `__DSH_BOOT__`），不是 DSH 会明确提示，绝不乱连。

## 备注

- 与 `dsh-opencode-tui-theme`、`dsh-waystation` 不同，本插件**不是运行在 DSH 内部的
  Cordis 插件**，而是 DSH 外面的桌面外壳 —— 它管的是「DSH 进程的生死」，
  那两个管的是「DSH 页面长什么样 / 面板里有什么」。
- 冒烟验证：`DSH_DESKTOP_SMOKE=1 DSH_DESKTOP_PORT=3999
  DSH_DESKTOP_COMMAND="node test/smoke-server.js" npm start`，
  退出后检查 3999 端口应已关闭（证明子进程树被杀干净）。
