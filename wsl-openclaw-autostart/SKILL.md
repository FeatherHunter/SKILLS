---
name: wsl-openclaw-autostart
description: 在WSL2中配置OpenClaw Gateway开机自启，使用systemd系统级服务替代PM2，通过VBS脚本+注册表保活WSL防止休眠中断。彻底解决PM2死循环、SIGTERM频繁kill、WSL自动休眠导致的服务中断问题。
homepage: https://github.com/nicepkg/openclaw
metadata:
  emoji: "🔄"
  requires:
    bins: ["wsl", "node", "systemctl"]
    platform: "windows"
---

# WSL OpenClaw 开机自启配置

在 WSL2 中配置 OpenClaw Gateway 作为系统级服务，实现 Windows 重启后全自动运行，无需手动操作。

> **适用场景**：已有 OpenClaw 实例，需要从 PM2 迁移到 systemd，解决重启循环和休眠中断问题。
> **冷启动场景**（全新电脑）：按本文从头执行，AI 需先完成「环境准备」再进入「前置条件」。

## 核心问题

| 问题 | 根因 | 表现 |
|------|------|------|
| Gateway 每~20秒被 SIGKILL | PM2 的 `pm2-feather.service`(systemd) 陷入死循环 stop/start，每次 stop 执行 `pm2 kill` | Gateway 不断重启，QQ Bot 无法回复 |
| 用户级 systemd 服务随 WSL 休眠而停 | WSL 没有交互式 bash 会话时自动休眠（默认~15秒） | 用户关闭终端后 Gateway 失联 |
| `vmIdleTimeout=-1` 可能不生效 | 依赖 Windows 版本和 `networkingMode=Mirrored` 兼容性 | WSL 持续休眠终止 |

## 最终架构

```
Windows 启动
  └─ 注册表 Run 键 → wscript.exe wsl-keepalive.vbs
       └─ WSL 内 bash 无限循环 sleep (保持 WSL 不休眠)
            └─ systemd (系统级) → openclaw-gateway.service
                 └─ node openclaw.mjs gateway --port 18795 --bind lan
```

## 环境准备（全新电脑必做）

如果以下任一项缺失，AI 必须先完成环境搭建，否则后续步骤会失败。

### 确认 WSL2 已安装

```powershell
wsl --status
```

如果报错 "WSL is not installed"，用户需要以管理员身份运行：
```powershell
wsl --install -d Ubuntu-22.04
```
安装后重启电脑。

### 确认 Node.js 已安装

```bash
wsl bash -c "node --version && npm --version"
```

如果失败，在 WSL 内安装：
```bash
wsl bash -c "curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -; sudo apt-get install -y nodejs"
```

### 确认 Python3 已安装

```bash
wsl bash -c "python3 --version"
```

如果失败：`wsl bash -c "sudo apt-get install -y python3"`

## 前置条件

```
Windows 启动
  └─ 注册表 Run 键 → wscript.exe wsl-keepalive.vbs
       └─ WSL 内 bash 无限循环 sleep (保持 WSL 不休眠)
            └─ systemd (系统级) → openclaw-gateway.service
                 └─ node openclaw.mjs gateway --port 18795 --bind lan
```

## 前置条件

在执行以下步骤前，AI 必须先确认或完成这些基础准备：

### 0.1 探测 WSL 用户名

```bash
wsl whoami
```

将输出结果记为 `<WSL_USER>`，替换后续所有 `<用户名>` 占位符。例如输出 `feather`，则 `/home/<用户名>` = `/home/feather`。

### 0.2 确认 npm 全局安装路径

```bash
wsl bash -c "npm prefix -g"
```

输出示例：`/usr/local/node22`。openclaw.mjs 的路径规律是 `{prefix}/lib/node_modules/openclaw/openclaw.mjs`。例如 prefix 是 `/usr/local/node22`，则路径为 `/usr/local/node22/lib/node_modules/openclaw/openclaw.mjs`。

验证入口文件确实存在：
```bash
wsl ls -la /usr/local/node22/lib/node_modules/openclaw/openclaw.mjs
```

如果不存在，用 `wsl find / -name "openclaw.mjs" 2>/dev/null` 寻找。

### 0.3 确认代理端口

```bash
# 在 WSL 中测试常见代理端口
wsl bash -c "curl -x http://127.0.0.1:7890 -s -o /dev/null -w '%{http_code}' https://registry.npmjs.org 2>/dev/null || echo '7890 failed'; curl -x http://127.0.0.1:7891 -s -o /dev/null -w '%{http_code}' https://registry.npmjs.org 2>/dev/null || echo '7891 failed'"
```

哪个端口返回 `200` 就用哪个。如果都不通，说明没有代理，后续跳过所有 `http_proxy` 环境变量即可。

### 0.4 确认 .wslconfig 存在并包含 networkingMode=Mirrored

```powershell
# PowerShell
$cfg = "$env:USERPROFILE\.wslconfig"
if (Test-Path $cfg) { 
    $content = Get-Content $cfg -Raw
    if ($content -notmatch "networkingMode\s*=\s*Mirrored") {
        Add-Content $cfg "`nnetworkingMode=Mirrored"
        Write-Host "Added networkingMode=Mirrored"
    }
    if ($content -notmatch "vmIdleTimeout") {
        Add-Content $cfg "`nvmIdleTimeout=-1"
        Write-Host "Added vmIdleTimeout=-1"
    }
} else {
    @"
[wsl2]
networkingMode=Mirrored
vmIdleTimeout=-1
"@ | Set-Content $cfg -Encoding ASCII
    Write-Host "Created .wslconfig"
}
```

必须有 `networkingMode=Mirrored`，否则 Windows 上 `127.0.0.1:18795` 无法访问 WSL 内的端口。

### 0.5 确认 OpenClaw 已安装

```bash
wsl bash -c "npm list -g openclaw 2>/dev/null | grep openclaw || echo 'NOT INSTALLED'"
```

如果未安装，执行：
```bash
# 有代理的情况
wsl bash -c "export http_proxy=http://127.0.0.1:<代理端口>; export https_proxy=http://127.0.0.1:<代理端口>; sudo npm install -g openclaw@latest"

# 无代理的情况
wsl bash -c "sudo npm install -g openclaw@latest"
```

### 0.6 确认 QQ Bot 凭证已配置

```bash
wsl bash -c "python3 -c \"import json; c=json.load(open('/home/<WSL_USER>/.openclaw/openclaw.json')); print('QQ Bot enabled:', c.get('channels',{}).get('qqbot',{}).get('enabled')); print('Has token:', 'token' in c.get('channels',{}).get('qqbot',{}))\""
```

如果未配置，提醒用户去 QQ 开放平台获取凭证后填入 `openclaw.json`。

### 0.7 确认 node 二进制路径

```bash
wsl bash -c "which node"
```

常见路径：`/usr/bin/node`、`/usr/local/bin/node`、`~/.nvm/versions/node/vXX/bin/node`。
将结果记为 `<NODE_PATH>`，后续 Step 6 的 `ExecStart` 需要使用。

## 配置步骤

### Step 1：禁用 PM2 systemd 服务

PM2 的 systemd 服务会导致 Gateway 反复被 kill（PM2 每~20秒会在 stop/start 间死循环）。

```bash
# 在 WSL 中执行（需要 root）
wsl -u root systemctl disable --now pm2-feather.service
```

验证 PM2 已死：
```bash
wsl systemctl status pm2-feather.service --no-pager
# 期望：Active: inactive (dead)
```

### Step 2：安装 OpenClaw（如 0.5 已确认安装则跳过）

> **AI 执行提示**：将 `<WSL_USER>` 和 `<NPM_PREFIX>` 替换为 0.1、0.2 探测到的实际值。

```bash
# 安装（有代理）
wsl bash -c "export http_proxy=http://127.0.0.1:<代理端口>; export https_proxy=http://127.0.0.1:<代理端口>; sudo npm install -g openclaw@latest"

# 安装（无代理）
wsl bash -c "sudo npm install -g openclaw@latest"

# 验证
wsl <NPM_PREFIX>/lib/node_modules/openclaw/openclaw.mjs --version
```

### Step 3：修复 OpenClaw 配置文件

如果 `openclaw.json` 已存在，清理陈旧插件条目；如果不存在（全新安装），创建基础配置。

```bash
wsl bash -c "
if [ -f /home/<WSL_USER>/.openclaw/openclaw.json ]; then
    python3 -c \"
import json
with open('/home/<WSL_USER>/.openclaw/openclaw.json') as f:
    config = json.load(f)
config['plugins']['entries'].pop('openclaw-qqbot', None)
config['plugins']['entries'].pop('openclaw-weixin', None)
config['plugins']['allow'] = ['qqbot']
with open('/home/<WSL_USER>/.openclaw/openclaw.json', 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
print('Config cleaned')
\"
else
    echo 'openclaw.json not found. Please ensure OpenClaw is installed and has been run at least once (openclaw init).'
fi
"
```

> 如果文件不存在，运行 `wsl openclaw init` 先初始化。

确保 QQ Bot 通道已启用（手动编辑 `openclaw.json` 或运行 `openclaw config`）：
```json
"channels": {
  "qqbot": {
    "enabled": true,
    "name": "QQ频道Bot",
    "token": "bot:v1_...",
    "allowFrom": ["*"],
    "appId": "你的AppID",
    "clientSecret": "你的ClientSecret"
  }
}
```

> QQ Bot 凭证需用户自行从 QQ 开放平台获取，填入 `openclaw.json` 的 `channels.qqbot` 段：
```json
"channels": {
  "qqbot": {
    "enabled": true,
    "token": "bot:v1_...",
    "appId": "...",
    "clientSecret": "..."
  }
}
```

### Step 5：确认 Gateway 入口文件路径

```bash
# 用 0.2 探测到的 prefix 拼接路径
wsl ls -la <NPM_PREFIX>/lib/node_modules/openclaw/openclaw.mjs
```

如果不存在，全局搜索：
```bash
wsl find / -name "openclaw.mjs" -type f 2>/dev/null
```

记下完整路径，后续 Step 6 的 `ExecStart` 需要使用。

### Step 6：创建系统级 systemd 服务文件

> **AI 执行提示**：必须先将以下变量替换为实际值，再执行脚本：
> - `<WSL_USER>` → 0.1 探测到的用户名（如 `feather`）
> - `<NODE_PATH>` → 0.7 探测到的 node 路径（如 `/usr/bin/node`）
> - `<OPENCLAW_ENTRY>` → Step 5 确认的 openclaw.mjs 完整路径
> - `<NPM_PREFIX>` → 0.2 的 npm prefix（用于拼接 PATH）
> - `<PROXY_PORT>` → 0.3 确认的代理端口；如果无代理，删除 4 行 `Environment=http*` 和 `Environment=HTTP*`

```bash
wsl -u root python3 -c "
content = '''[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target
StartLimitBurst=10
StartLimitIntervalSec=120

[Service]
Type=simple
User=<WSL_USER>
ExecStart=<NODE_PATH> <OPENCLAW_ENTRY> gateway --port 18795 --bind lan
Restart=always
RestartSec=10
TimeoutStopSec=30
TimeoutStartSec=90
SuccessExitStatus=0 143
KillMode=control-group
Environment=HOME=/home/<WSL_USER>
Environment=TMPDIR=/tmp
Environment=PATH=/home/<WSL_USER>/.local/bin:/usr/bin:/usr/local/bin:<NPM_PREFIX>/bin:/usr/local/sbin:/usr/sbin:/sbin:/bin
Environment=http_proxy=http://127.0.0.1:<PROXY_PORT>
Environment=https_proxy=http://127.0.0.1:<PROXY_PORT>
Environment=HTTP_PROXY=http://127.0.0.1:<PROXY_PORT>
Environment=HTTPS_PROXY=http://127.0.0.1:<PROXY_PORT>

[Install]
WantedBy=multi-user.target
'''
with open('/etc/systemd/system/openclaw-gateway.service', 'w') as f:
    f.write(content)
print('Service file written')
"
```

> **端口自定义**：如果需要使用其他端口（如 `8080`），修改 `--port 18795` 即可。确保后续访问地址同步修改。

### Step 7：启用并启动服务

```bash
# 重载 systemd 配置
wsl -u root systemctl daemon-reload

# 启用开机自启并立即启动
wsl -u root systemctl enable --now openclaw-gateway

# 检查状态
wsl systemctl status openclaw-gateway --no-pager
# 期望：Active: active (running)
```

### Step 8：禁止 WSL 自动休眠

编辑 Windows 端的 `.wslconfig` 文件（位于 `%USERPROFILE%\.wslconfig`）：

```ini
[wsl2]
networkingMode=Mirrored
vmIdleTimeout=-1
```

> `vmIdleTimeout=-1` 表示永不休眠。无需重启 Windows，但需要完全关闭 WSL 后重新打开。

```powershell
# PowerShell
wsl --shutdown
```

### Step 9：创建 WSL 保活脚本

此脚本通过维持一个 WSL 内的 bash 会话，防止 WSL 休眠：

`%USERPROFILE%\wsl-keepalive.vbs`：

```vbscript
Dim WshShell
Set WshShell = CreateObject("WScript.Shell")
Do
    WshShell.Run "wsl.exe -e bash -c ""while true; do sleep 86400; done""", 0, True
    WScript.Sleep 5000
Loop
```

> `0` = 隐藏窗口，`True` = 等待子进程结束（WSL 断线后自动重连），`86400` = 24小时循环 sleep。

### Step 10：添加到 Windows 开机启动

```powershell
# PowerShell（管理员不需要，普通用户即可）
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WSL KeepAlive" -Value "C:\Windows\System32\wscript.exe `"${env:USERPROFILE}\wsl-keepalive.vbs`""
```

验证注册表项：
```powershell
Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WSL KeepAlive"
```

### Step 11：立即启动保活脚本（本次）

```powershell
Start-Process "C:\Windows\System32\wscript.exe" -ArgumentList "`"${env:USERPROFILE}\wsl-keepalive.vbs`"" -WindowStyle Hidden
```

### Step 12：验证完整性

```bash
# 1. 确认 WSL 中有一个 bash 保活会话
wsl who
# 期望输出至少一行

# 2. 确认 Gateway 正在运行
wsl systemctl status openclaw-gateway --no-pager
# 期望：Active: active (running)

# 3. 测试 HTTP 端口
curl http://127.0.0.1:18795/
# 期望：返回 200 或 HTML 内容

# 4. 确认 PM2 已死
wsl systemctl status pm2-feather.service --no-pager
# 期望：Active: inactive (dead)
```

### Step 13：重启 WSL 验证自动恢复

```bash
# 完全关闭
wsl --shutdown

# 等待几秒

# 仅执行状态检查（不执行任何启动命令）
wsl systemctl status openclaw-gateway --no-pager
# 期望：Active: active (running) —— 自动启动
```

## 日常管理命令

| 操作 | 命令 |
|------|------|
| 启动 Gateway | `wsl -u root systemctl start openclaw-gateway` |
| 停止 Gateway | `wsl -u root systemctl stop openclaw-gateway` |
| 重启 Gateway | `wsl -u root systemctl restart openclaw-gateway` |
| 查看状态 | `wsl systemctl status openclaw-gateway --no-pager` |
| 实时日志 | `wsl journalctl -u openclaw-gateway -f` |
| 查看最近日志 | `wsl journalctl -u openclaw-gateway --no-pager -n 50` |
| Web 管理页面 | `http://127.0.0.1:18795/` |

## 故障排查

| 现象 | 排查步骤 |
|------|----------|
| Gateway 反复重启 | `wsl journalctl -u openclaw-gateway --no-pager -n 20` 查找 `SIGTERM`/`Stopping` |
| 端口被占用 | `wsl bash -c "ss -tlnp \| grep 18795"` 然后 `wsl bash -c "kill -9 <PID>"` |
| QQ Bot 无响应 | 查看日志中是否有 `Processing message` 和 `Gateway resumed` |
| WSL 保活不生效 | 检查 `wsl who` 是否有用户会话，重启保活 VBS |
| PM2 死灰复燃 | `wsl -u root systemctl disable --now pm2-feather.service` 再次确认 |

## 变量速查表（AI 执行前必读）

AI 在另一台电脑上执行时，首先完成以下探测，将结果填入变量列，然后按变量替换所有步骤中的占位符。

| 变量 | 探测命令 | 说明 |
|------|----------|------|
| `<WSL_USER>` | `wsl whoami` | WSL 用户名 |
| `<NODE_PATH>` | `wsl bash -c "which node"` | node 可执行文件路径 |
| `<NPM_PREFIX>` | `wsl bash -c "npm prefix -g"` | npm 全局安装前缀，如 `/usr/local/node22` |
| `<OPENCLAW_ENTRY>` | `wsl find / -name "openclaw.mjs" 2>/dev/null` | openclaw 入口文件完整路径 |
| `<PROXY_PORT>` | `wsl bash -c "curl -x http://127.0.0.1:7890 -s -o /dev/null -w '%{http_code}' https://registry.npmjs.org"` | 测试 7890/7891 等常见端口，200=可用，无代理则删 |
| `HAS_PROXY` | 上述测试 | `true`=保留代理环境变量，`false`=删除

## 环境变量说明（systemd service 内）

| 变量 | 值 | 说明 |
|------|-----|------|
| `http_proxy` | `http://127.0.0.1:7890` | HTTP 代理（按实际修改） |
| `https_proxy` | `http://127.0.0.1:7890` | HTTPS 代理（按实际修改） |
| `HOME` | `/home/<用户名>` | 用户主目录 |
| `PATH` | 包含 node22/bin | 确保 Node.js 可执行文件在 PATH 中 |
