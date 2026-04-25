---
name: hermes-agent-install
description: "在 WSL2 环境中安装 Hermes Agent，自动处理代理网络、Git GnuTLS 兼容性等常见问题。当用户想在 WSL 中安装 hermes-agent、遇到 hermes 安装报错、或需要配置 WSL 代理访问 GitHub 时使用。"
homepage: https://github.com/NousResearch/hermes-agent
metadata: { "emoji": "⚕", "requires": { "bins": ["git", "wsl"], "platform": "windows" } }
---

# Hermes Agent Install Skill

在 WSL2 环境中安装 [Hermes Agent](https://github.com/NousResearch/hermes-agent)，自动处理 WSL 代理网络、Git GnuTLS 兼容性等常见问题。

## When to Use

✅ **USE this skill when:**

- "在 WSL 中安装 hermes agent"
- "安装 hermes-agent"
- "hermes install 报错"
- "WSL 无法访问 GitHub"
- "WSL git GnuTLS 错误"
- "curl install.sh 失败"
- "hermes API 超时"
- "hermes APITimeoutError"

## When NOT to Use

❌ **DON'T use this skill when:**

- 在原生 Linux/macOS 上安装（直接用官方命令即可）
- 配置 hermes 的 API Key → 用 `hermes setup`
- 使用 hermes 聊天 → 用 `hermes chat`

## 环境前提

| 依赖 | 说明 |
|------|------|
| Windows 10/11 + WSL2 | 必须已安装 WSL2 |
| WSL2 mirrored 网络模式 | `.wslconfig` 中 `networkingMode=mirrored`，这样 WSL 可用 `127.0.0.1` 访问 Windows 代理 |
| Windows 代理软件 | Clash/V2Ray 等在 Windows 侧监听（如 127.0.0.1:7890） |
| Windows 侧 Git | 用于从 Windows 端 clone 仓库（绕过 WSL Git GnuTLS 问题） |
| uv | WSL 中已安装 uv 包管理器（如未安装脚本会自动处理） |

## 核心问题与解决方案

### 问题 1：WSL 无法直接访问 GitHub

**现象**：`curl: (28) SSL connection timeout` 或 `curl: (56) OpenSSL SSL_read: error`

**原因**：WSL2 默认网络模式下无法直连外网，需要通过 Windows 代理

**解决方案**：配置 WSL 代理环境变量

```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
```

> ⚠️ 仅 mirrored 网络模式下可用 `127.0.0.1`。NAT 模式需用 Windows 宿主 IP（从 `/etc/resolv.conf` 获取）

### 问题 2：Git GnuTLS 与 Clash 代理不兼容

**现象**：`fatal: unable to access '...': GnuTLS recv error (-110): The TLS connection was non-properly terminated.` 或 `gnutls_handshake() failed`

**原因**：Ubuntu 22.04 自带 Git 使用 GnuTLS，与 HTTP 代理的 TLS 握手存在兼容性 bug

**临时方案**（不推荐，有安全风险）：
```bash
git config --global http.sslVerify false
```

**推荐方案**：从 Windows 侧 clone 仓库，再复制到 WSL：
```powershell
# Windows PowerShell 端
git clone --recurse-submodules https://github.com/NousResearch/hermes-agent.git "D:\hermes-agent"
```

```bash
# WSL 端
cp -r /mnt/d/hermes-agent ~/.hermes/hermes-agent
```

### 问题 3：install.sh 脚本内 git pull 失败

**现象**：安装脚本检测到已有安装，执行 `git pull` 时因 GnuTLS 问题失败

**解决方案**：跳过安装脚本，采用手动安装步骤

### 问题 4：hermes 启动后 API 调用超时

**现象**：`hermes` 启动后发送消息，报 `APITimeoutError`，显示 Provider/Model/Endpoint 信息，重试 3 次均失败

```
⚠️  API call failed (attempt 1/3): APITimeoutError
   🔌 Provider: xxx  Model: xxx
   🌐 Endpoint: https://api.xxx.com/...
   📝 Error: Request timed out or interrupted.
```

**根因分析思路**：

1. **确认是否为 WSL 网络问题**：安装阶段能访问 GitHub（因为配了代理），但 hermes 运行时是新的进程，不会继承安装时的代理环境变量
2. **验证连通性**：用 `curl` 带代理测试 API 端点是否可达
3. **核心洞察**：hermes 的网络请求走 Python httpx 库，该库读取 `HTTP_PROXY`/`HTTPS_PROXY` 环境变量（大写），而非 `http_proxy`/`https_proxy`（小写）。需要在 hermes 能读取到的地方配置代理

**解决方案：双重代理配置**

hermes 通过两种方式读取环境变量，因此需要在两处都配置代理：

1. **`~/.hermes/.env`**（hermes 自身的 dotenv 文件，启动时加载）
2. **`~/.bashrc`**（shell 启动时加载，确保终端环境也有代理）

```bash
# 写入 hermes 的 .env（hermes 进程会读取）
cat >> ~/.hermes/.env << 'EOF'
HTTP_PROXY=http://<代理地址>:<端口>
HTTPS_PROXY=http://<代理地址>:<端口>
http_proxy=http://<代理地址>:<端口>
https_proxy=http://<代理地址>:<端口>
EOF

# 写入 .bashrc（shell 环境也生效）
cat >> ~/.bashrc << 'EOF'
export http_proxy=http://<代理地址>:<端口>
export https_proxy=http://<代理地址>:<端口>
EOF
```

> 💡 **关键经验**：大小写都要写！`HTTP_PROXY`（大写，Python httpx 读取）和 `http_proxy`（小写，curl/wget 等工具读取）缺一不可。

**验证**：配置后用 curl 测试 API 端点连通性：
```bash
export http_proxy=http://<代理地址>:<端口>
export https_proxy=http://<代理地址>:<端口>
curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 https://<API端点>
# 返回任意 HTTP 状态码（非 000）即表示网络通了
```

然后重新启动 hermes：`source ~/.bashrc && hermes`

## 完整安装流程

### Step 1：检测环境与代理

```bash
# 检查 WSL 网络模式
cat /mnt/c/Users/*/\.wslconfig
# 期望看到 networkingMode=mirrored

# 测试代理连通性
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
curl -I --connect-timeout 10 https://raw.githubusercontent.com 2>&1
# 期望返回 HTTP/2 200 或 301

# 检查 Windows 代理端口（在 PowerShell 中）
netstat -an | findstr "LISTENING" | findstr "7890"
```

### Step 2：配置 Git 代理（WSL 端）

```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

### Step 3：从 Windows 端 Clone 仓库

由于 WSL Git 的 GnuTLS 问题，从 Windows 端执行 git clone：

```powershell
# PowerShell 端执行
git clone --recurse-submodules https://github.com/NousResearch/hermes-agent.git "D:\hermes-agent"
```

### Step 4：复制仓库到 WSL

```bash
# WSL 端执行
rm -rf ~/.hermes/hermes-agent
cp -r /mnt/d/hermes-agent ~/.hermes/hermes-agent
```

### Step 5：创建虚拟环境

```bash
cd ~/.hermes/hermes-agent
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
~/.local/bin/uv venv venv --python 3.11
```

> 如果 uv 未安装，先执行：`curl -LsSf https://astral.sh/uv/install.sh | sh`

### Step 6：安装 Python 依赖

```bash
export VIRTUAL_ENV="$(pwd)/venv"
~/.local/bin/uv pip install -e ".[all]"
```

> 仅安装核心功能（无 Telegram/Discord 等）：`~/.local/bin/uv pip install -e "."`

### Step 7：创建配置目录与文件

```bash
mkdir -p ~/.hermes/{cron,sessions,logs,memories,skills,pairing,hooks,image_cache,audio_cache,whatsapp/session}
cp ~/.hermes/hermes-agent/cli-config.yaml.example ~/.hermes/config.yaml
touch ~/.hermes/.env
```

### Step 8：创建全局命令链接

```bash
mkdir -p ~/.local/bin
ln -sf ~/.hermes/hermes-agent/venv/bin/hermes ~/.local/bin/hermes

# 确保 PATH 包含 ~/.local/bin
grep -q '.local/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### Step 9：验证安装

```bash
export PATH="$HOME/.local/bin:$PATH"
hermes --version
hermes doctor
```

### Step 10：配置运行时代理（关键！）

> ⚠️ **这是最容易被遗漏的步骤**。安装阶段配的代理只对当前终端会话生效，hermes 启动后是独立进程，必须单独配置代理才能访问 LLM API。

```bash
# 写入 hermes 的 .env 文件（大小写都写，确保 Python httpx 和 curl 都能读取）
cat >> ~/.hermes/.env << 'EOF'
HTTP_PROXY=http://<代理地址>:<端口>
HTTPS_PROXY=http://<代理地址>:<端口>
http_proxy=http://<代理地址>:<端口>
https_proxy=http://<代理地址>:<端口>
EOF

# 同时写入 .bashrc（确保终端环境也有代理）
grep -q 'http_proxy' ~/.bashrc || cat >> ~/.bashrc << 'EOF'
export http_proxy=http://<代理地址>:<端口>
export https_proxy=http://<代理地址>:<端口>
EOF
```

> 💡 其中 `<代理地址>:<端口>` 替换为你 Windows 代理的实际地址。mirrored 模式下为 `127.0.0.1:<端口>`，NAT 模式下为 Windows 宿主 IP。

### Step 11：安装后配置

```bash
# 配置 LLM 提供商 API Key
hermes model

# 或运行完整设置向导
hermes setup
```

### Step 12（可选）：安装可选子模块

```bash
cd ~/.hermes/hermes-agent
export VIRTUAL_ENV="$(pwd)/venv"
~/.local/bin/uv pip install -e "./tinker-atropos"  # RL 训练后端
```

### Step 13（可选）：安装 Node.js 依赖

```bash
cd ~/.hermes/hermes-agent
npm install  # 浏览器自动化 & WhatsApp bridge
```

### Step 14：清理

```bash
# 恢复 git SSL 验证（之前可能临时关闭了）
git config --global http.sslVerify true

# 清理 Windows 端临时 clone
# PowerShell: Remove-Item -Recurse -Force "D:\hermes-agent"
```

## 故障排查速查表

| 问题 | 命令/方案 |
|------|-----------|
| `curl: (28) SSL connection timeout` | 配置 `http_proxy`/`https_proxy` 环境变量 |
| `GnuTLS recv error (-110)` | 从 Windows 端 clone 仓库再复制到 WSL |
| `gnutls_handshake() failed` | 同上，或临时 `git config --global http.sslVerify false` |
| `hermes: command not found` | `source ~/.bashrc` 或检查 `~/.local/bin` 是否在 PATH |
| `APITimeoutError` | 在 `~/.hermes/.env` 和 `~/.bashrc` 中配置代理（大小写都要写） |
| `No API key found` | 运行 `hermes model` 或 `hermes setup` |
| `uv: command not found` | 安装 uv：`curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| 代理端口不确定 | PowerShell: `netstat -an \| findstr "LISTENING"` 查看监听端口 |
| WSL 网络模式检查 | `cat /mnt/c/Users/*/\.wslconfig` 查看是否 mirrored |
| 诊断命令 | `hermes doctor` |

## 代理端口参考

| 代理软件 | HTTP 端口 | SOCKS5 端口 |
|---------|----------|------------|
| Clash | 7890 | 7891 |
| V2RayN | 10809 | 10808 |
| Shadowsocks | 1080 | - |

> 💡 具体端口以你实际配置为准，上表仅供参考。可在 PowerShell 中用 `netstat -an | findstr "LISTENING"` 查看本机监听端口。

## WSL + hermes 代理配置的核心思路

WSL2 中的网络请求需要代理才能访问外网，但不同阶段、不同工具读取代理的方式不同，容易遗漏：

| 阶段 | 工具 | 读取方式 | 配置位置 |
|------|------|---------|--------|
| 安装时 curl | curl | `http_proxy`/`https_proxy`（小写）环境变量 | 终端 export |
| 安装时 git | git | `http.proxy`/`https.proxy` git config | `~/.gitconfig` |
| 运行时 API 调用 | Python httpx | `HTTP_PROXY`/`HTTPS_PROXY`（**大写**）环境变量 | `~/.hermes/.env` |
| 运行时终端工具 | curl/wget | `http_proxy`/`https_proxy`（小写）环境变量 | `~/.bashrc` |

**核心原则**：
1. **安装时代理 ≠ 运行时代理**——安装时 export 的环境变量不会持久化，hermes 进程启动后需要重新读取
2. **大小写都要写**——`HTTP_PROXY`（大写，Python 读取）+ `http_proxy`（小写，curl 等读取）
3. **两处都要配**——`~/.hermes/.env`（hermes 进程读取）+ `~/.bashrc`（shell 环境）
4. **网络模式决定代理地址**——mirrored 用 `127.0.0.1`，NAT 用宿主 IP

## WSL 网络模式差异

| 模式 | 代理地址 | 配置方式 |
|------|---------|--------|
| mirrored | `127.0.0.1:<端口>` | `.wslconfig` 中 `networkingMode=mirrored` |
| NAT | `<宿主IP>:<端口>`（从 `/etc/resolv.conf` 获取） | 默认模式 |

## Related Skills

- `glm-models` - 智谱 GLM 大模型 API 封装，可作为 hermes 的 LLM 提供商
