# scripts（可选）

本目录**不含必选脚本**。通用发布流程（`SKILL.md` §0-7）仅依赖 `npm` CLI，在任何交互终端即可完成，无需额外脚本。

## 为什么没有 publish-window.ps1？

历史版本曾提供 Windows 专用的 `publish-window.ps1` / `login-window.ps1`，通过 `schtasks /it` 把交互窗口投递到用户桌面，以解决 Agent 后台无 TTY 导致 `EOTP` 的问题。该做法：

- 仅适用于 Windows + 需要 Agent 代起窗口的特殊环境
- 强耦合 `schtasks`、PowerShell 编码（UTF-8 BOM）、以及特定桌面会话
- 对 macOS / Linux / 纯人工发布毫无价值，属于**硬编码干扰项**，已从通用技能中移除

通用解法（跨平台）已写入 `SKILL.md` §4 与 `references/pitfalls.md` 坑 8：

> **发布必须在人可直接操作的交互终端中执行**；Agent 只做前置检查与事后验证，不代跑 `npm publish`。

## 如果你仍需要 Windows 交互窗口助手

按以下**原理**自行实现（不作为技能必选）：

1. 交互式 2FA 要求真实 TTY——后台重定向必 `EOTP`
2. `schtasks /create /tn <name> /tr "powershell.exe -NoProfile -File <脚本>" /sc once /st <time> /it /f` + `schtasks /run` 可将窗口投递到用户交互桌面（`Start-Process` 直接起的窗口对用户不可见）
3. 脚本内显式设置 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`，并以 UTF-8 (BOM) 保存，避免中文乱码
4. 脚本参数化：`-PackageDir <包目录>` 必填，`-Preview` 可选

示例骨架（自行保存为 `publish-window.ps1`，UTF-8 BOM）：

```powershell
param([Parameter(Mandatory=$true)][string]$PackageDir, [switch]$Preview)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location $PackageDir
if ($Preview) { npm pack --dry-run; exit 0 }
# 未登录时先引导登录（npm 10 未登录 publish 直接 ENEEDAUTH）
$whoami = npm whoami --registry=https://registry.npmjs.org 2>$null
if ($LASTEXITCODE -ne 0 -or -not $whoami) {
  npm login --auth-type=web --registry=https://registry.npmjs.org
  if ($LASTEXITCODE -ne 0) { Read-Host '登录失败，按回车关闭'; exit 1 }
}
npm publish --registry=https://registry.npmjs.org
Read-Host '按回车关闭窗口'
```

> 以上仅为**可选参考**，通用技能不依赖它。第三方用户/ AI 可直接忽略本目录。

## 新增：publish-auto.ps1（Agent 半自动 + 自动弹浏览器）

`publish-auto.ps1` 是本次 `1.6.19` 实战沉淀的**可选增强**：Agent 后台起 `npm publish`，轮询 `job_output` 命中 `https://www.npmjs.com/auth/cli/` / `https://www.npmjs.com/login?next=/login/cli/` 即用 `schtasks /it` 自动弹浏览器到用户桌面，支持二次 2FA 自动再弹。

```powershell
# 用法（交互式 PowerShell 窗口中，或由 Agent 调度到用户桌面的 schtasks 任务中）
powershell -ExecutionPolicy Bypass -File scripts/publish-auto.ps1 -PackageDir D:\path\to\package
# 可选：-Registry https://registry.npmjs.org -PollMs 1500
```

流程：`login 检查（显式官方源）→ 后台 publish → 轮询 `Receive-Job` → 命中链接即 `schtasks /it` 弹浏览器 → 监测 `+ <pkg>@<ver>` 成功标志 → 退出`。通用技能仍以 `SKILL.md §4` 的“人机各司其职”为主，此脚本仅为减少“复制链接→手动打开”一步的 Windows 便捷封装。
