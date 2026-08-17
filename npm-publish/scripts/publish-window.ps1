# ============================================================
# publish-window.ps1 —— npm 发布窗口（Agent 启动，用户完成 2FA）
#
# 设计理念：
#   1. npm publish 的网页审批流要求【真实 TTY + 用户本人】：
#      Agent 后台环境直接跑会 EOTP，隔空传 OTP 必过期。
#   2. Agent 直接 Start-Process 的窗口开在用户不可见的会话
#      （实测 MainWindowHandle=0）——用 schtasks 交互式任务
#      （/IT）把窗口启动到用户交互桌面。
#   3. 系统代码页可能为 65001（UTF-8）：本脚本必须 UTF-8(BOM)
#      保存，脚本内显式设置输出编码；脚本路径避免中文。
#
# 用法（由 Agent 执行）：
#   schtasks /create /tn "DSHPublish" /tr "<powershell.exe 完整路径>
#     -NoProfile -ExecutionPolicy Bypass -File "<本脚本路径>"
#     -PackageDir "<包目录>" /sc once /st 23:59 /it /f
#   schtasks /run /tn "DSHPublish"
#   用户：看窗口 → 按回车开浏览器 → 2FA 审批 → 回车
#   收尾：schtasks /delete /tn "DSHPublish" /f
#
# 参数：
#   -PackageDir  待发布 npm 包目录（必填）
#   -Preview     预览模式：只显示横幅与目录，不执行 npm publish
# ============================================================
param(
    [Parameter(Mandatory = $true)]
    [string]$PackageDir,
    [switch]$Preview
)

$Host.UI.RawUI.WindowTitle = 'DSH npm 发布窗口'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ''
Write-Host '============================================================'
Write-Host '  DSH npm 发布窗口（Agent 已启动，由你完成 2FA 审批）'
Write-Host '============================================================'
Write-Host '  1. 看到 Auth URL 后按回车 → 浏览器打开授权页'
Write-Host '  2. 在浏览器完成登录 + 2FA 确认'
Write-Host '  3. 回到本窗口再按回车'
Write-Host '  成功标志: + <包名>@<版本>'
Write-Host '============================================================'
Write-Host ''
Write-Host ('发布目录: ' + $PackageDir)
Write-Host ''

if ($Preview) {
    Write-Host '[预览模式] 不执行发布，仅验证窗口与编码。'
    Read-Host '按回车关闭窗口'
    exit 0
}

Set-Location -Path $PackageDir

# ── 登录检测（2026-08-16 实测补丁）：npm 10 未登录时 publish 不发 Auth URL、直接 ENEEDAUTH ──
# 必须先登录拿到令牌（网页登录，浏览器完成 2FA），之后 publish 的 2FA 才走网页审批流。
$whoami = npm whoami --registry=https://registry.npmjs.org 2>$null
if ($LASTEXITCODE -ne 0 -or -not $whoami) {
    Write-Host ''
    Write-Host '============================================================'
    Write-Host '  未检测到登录（npm 10 未登录时 publish 会直接 ENEEDAUTH）'
    Write-Host '  接下来走【网页登录】：浏览器打开授权页 → 登录 + 2FA → 自动继续'
    Write-Host '============================================================'
    Write-Host ''
    npm login --auth-type=web --registry=https://registry.npmjs.org
    if ($LASTEXITCODE -ne 0) {
        Write-Host ''
        Write-Host '登录失败——请把本窗口内容完整告知 Agent'
        Read-Host '按回车关闭窗口'
        exit 1
    }
    Write-Host '登录成功，继续发布...'
    Write-Host ''
}

npm publish --registry=https://registry.npmjs.org

Write-Host ''
Write-Host '============================================================'
Write-Host ('发布命令已结束，退出码: ' + $LASTEXITCODE)
if ($LASTEXITCODE -eq 0) {
    Write-Host '  上方出现 "+ <包名>@<版本>" 即为发布成功'
} else {
    Write-Host '  发布失败——请把本窗口内容完整告知 Agent'
}
Write-Host '============================================================'
Read-Host '按回车关闭窗口'