# dsh-harness-desktop · DSH 桌面版

> DSH（DeepSeek Harness）的**桌面壳**：像普通桌面应用一样使用 DSH —— 双击打开，
> 关窗后 DSH 继续在右下角托盘后台运行，随时点开秒回。**无需安装 Node.js**。

- **npm 主页**: <https://www.npmjs.com/package/dsh-harness-desktop>
- **源码目录**: `dsh-plugin/dsh-desktop/`
- **平台**: Windows 10/11（Linux/macOS 可自行构建，见开发者专区）

## ✨ 特性（30 秒看懂）

- ✅ **双击即用、零依赖**——不用装 Node.js / npm，应用内置一切
- ✅ **首次运行自动安装 DSH 本体**（需联网几分钟），之后**离线秒开**
- ✅ **关窗不退出**——关闭窗口，DSH 继续在后台运行（右下角托盘常驻），随时点开秒回
- ✅ **退出才停**——托盘菜单「退出」（带确认弹窗）才会真正停止后台服务
- ✅ **开机自启（可选）**——登录后自动后台常驻，双击图标即开（托盘右键勾选）
- ✅ 沉浸式无边框界面 + DeepSeek 官方鱼形图标
- ✅ 一条命令生成**桌面快捷方式**
- ✅ 你手动开着的 DSH **不会被误杀**（识别到已有实例就直接连上）

## 🚀 怎么用（二选一）

### 方式 A：便携 exe（普通用户，推荐）

1. **下载** `dsh-harness-desktop-1.0.2-x64.exe`（87MB 单文件）：
   - 官方下载页：[GitHub Releases](https://github.com/FeatherHunter/SKILLS/releases)
     （直接链接：https://github.com/FeatherHunter/SKILLS/releases/download/v1.0.2/dsh-harness-desktop-1.0.2-x64.exe ）
   - 或向维护者索取；也可以自己打包（见开发者专区）
2. **双击**它 → 首次等待几分钟（自动下载安装 DSH 本体）→ 自动进入界面
3. 之后**双击即秒开**；关掉窗口它仍在右下角托盘**后台运行**，随时点开秒回

想要桌面快捷方式？在 exe 所在目录执行：

```powershell
.\dsh-harness-desktop-1.0.2-x64.exe --install-shortcut
# 桌面出现「桌面版」图标，以后双击它直接打开
```

> Windows 弹出「已保护你的电脑」？点 **更多信息 → 仍要运行** 即可
> （exe 未签名，本地构建产物，安全）。

**日常使用**：关窗后应用仍在右下角托盘后台运行（DSH 服务不停）。左键单击托盘图标打开窗口；
右键托盘图标可**退出**（带确认）或勾选**开机自启**（登录后后台常驻，双击图标即开）。

### 方式 B：npm 安装（有 Node 环境的开发者）

```bash
# ① 建个文件夹并进入
mkdir dsh-app && cd dsh-app

# ② 安装（npm 源，国内镜像也快；看到 added 1 package 即成功）
npm install dsh-harness-desktop

# ③ 进入包目录，补装 electron 运行时（必做：npm 默认不装对方包的开发工具）
cd node_modules/dsh-harness-desktop
npm install

# ④ 启动（首次自动下载 DSH 本体，之后秒开）
npm start
```

> ⚠️ **国内网络第 ③ 步大概率报 `TypeError: fetch failed`**（electron 二进制从
> GitHub 下载被挡）。解决：先设镜像再执行 `npm install`：
>
> ```powershell
> $env:ELECTRON_MIRROR='https://npmmirror.com/mirrors/electron/'
> npm install
> ```
>
> 若已经报错，设完镜像后执行 `node node_modules/electron/install.js` 即可补下成功。

桌面快捷方式（可选）：在包目录执行 `npx dsh-harness-desktop shortcut`。

## 🛠 开发者专区

```bash
cd dsh-plugin/dsh-desktop
npm install && npm start    # 源码运行
npm run dist                # 打包便携 exe → dist/dsh-harness-desktop-1.0.2-x64.exe
npm run pack                # 快速验证：不打安装包，直接跑 win-unpacked/
```

常用环境变量（可选）：

| 变量 | 默认 | 说明 |
|---|---|---|
| `DSH_DESKTOP_PORT` | `3080` | DSH 服务端口 |
| `DSH_DESKTOP_COMMAND` | 内置运行时 | 自定义启动命令（整行，shell 解析；设置后跳过内置运行时） |
| `DSH_DESKTOP_REGISTRY` | 自动测速选源 | 安装 DSH 时的 npm 源；默认并发测速官方源与 npmmirror 选快者，设置后强制用它 |
| `DSH_DESKTOP_REINSTALL=1` | 关 | 强制重装 DSH 运行时（升级用） |
| `DSH_DESKTOP_HIDDEN=1` | 关 | 隐藏启动：窗口不显示，右下角托盘常驻（服务化；`--hidden` 同效） |
| `DSH_DESKTOP_USER_DATA` | 默认 | 独立 userData 目录（测试隔离：单实例锁/设置按目录隔离，普通用户不需要） |

> 内部调试变量（`DSH_DESKTOP_SMOKE` / `DSH_DESKTOP_SHOT` / `DSH_DESKTOP_SIZE`）见 `main.js` 顶部注释。

## ❓ 常见问题

- **双击没反应 / 提示"已保护你的电脑"？** → SmartScreen 拦截，点「更多信息 → 仍要运行」。
- **首次启动等很久？** → 正在下载 DSH 本体（数百 MB），几分钟正常；装好后离线秒开。
  安装页会显示**真实进度**（已下载 MB / 包数 / 百分比）与当前源；若长时间无进展可点
  「切换镜像重试」（自动换 npmmirror 重装）。本机 npm 缓存里已有 DSH 时直接复制复用，免下载。
- **提示"端口 3080 被其他程序占用"？** → 有别的程序占了 3080，关掉它，
  或用 `DSH_DESKTOP_PORT` 换一个端口。
- **关窗后 DSH 还在跑吗？** → 在跑。关窗只是隐藏窗口（右下角托盘常驻），
  左键单击托盘图标随时打开；托盘「退出」才会真正停止后台服务。
- **怎么真正退出？** → 右下角托盘图标右键 → 「退出（停止后台 DSH）」→ 确认。
- **怎么开机自启？** → 托盘图标右键勾选「开机自启（登录时后台常驻）」；
  下次开机 DSH 自动后台运行（窗口不显示），双击图标即开。
- **怎么升级 DSH？** → 删除 `%APPDATA%\dsh-desktop\runtime` 目录后重新打开，
  或设置 `DSH_DESKTOP_REINSTALL=1` 启动。
- **需要装 Node.js 吗？** → exe 方式不需要（内置运行时）；npm 方式需要。
- **Linux 双击没反应？** → 桌面环境 PATH 可能不含所需命令，
  用 `DSH_DESKTOP_COMMAND` 指定完整启动方式。

## 🔧 原理速览（开发者选读）

- **进程管家**：主进程拉起 DSH → 监控 → **关窗 = 隐藏到托盘**（后台 DSH 继续运行），
  只有托盘「退出」（确认弹窗）或应用退出时才杀掉整棵进程树（含安装阶段的 npm），不留孤儿进程；
  只有"本次由桌面版拉起的 DSH"才会被杀，不误伤手动实例。
  托盘不可用（如部分 Linux 桌面无托盘）时自动退回「关窗即退」老行为。
- **内置运行时（零依赖）**：Electron 自带完整 Node（`ELECTRON_RUN_AS_NODE`）+ 捆绑
  npm（11MB）→ 首次运行自动安装 DSH 到 `%APPDATA%/dsh-desktop/runtime`，之后离线可用。
- **首次安装三优先**：① 本机 npm 缓存（`%LOCALAPPDATA%/npm-cache/_npx`）已有 DSH →
  直接复制复用（免联网下载）；② 否则并发测速官方源与 npmmirror，自动选快者下载；
  ③ 安装页显示真实进度（字节/包数/百分比），90 秒无进展提示可「切换镜像重试」。
- **标题栏带**：页面整体下移 40px 形成无边框标题区，窗口控制按钮悬浮其上；
  顶部事件走 DOM 层（面板/浮层拖拽不被吞），空白带手动拖拽移动窗口。
- **日志**：`%APPDATA%/dsh-desktop/dsh.log`（Linux/macOS 为 `~/.config/dsh-desktop/dsh.log`），
  出错页可直接查看尾部。
