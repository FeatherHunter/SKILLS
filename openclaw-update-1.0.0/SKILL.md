---
name: openclaw-update
description: "在 WSL2 环境中升级 OpenClaw npm 全局包，处理 sudo npm registry 独立配置、代理环境变量传递、Git SSH 重定向等常见问题。当用户需要升级 openclaw、npm install -g 卡死或报错时使用。"
homepage: https://github.com/nicepkg/openclaw
metadata: { "emoji": "⬆", "requires": { "bins": ["npm", "wsl"], "platform": "windows" } }
---

# OpenClaw Update Skill

在 WSL2 环境中升级 OpenClaw npm 全局包，处理 sudo npm registry 独立配置、代理环境变量传递、Git SSH 重定向等常见问题。

## When to Use

✅ **USE this skill when:**

- "升级 openclaw"
- "openclaw update"
- "npm install -g openclaw 卡死"
- "npm install -g openclaw 报错 EACCES / ETIMEDOUT / ENOTEMPTY"
- "sudo npm 超时"
- "禁用源码型 OpenClaw"

## When NOT to Use

❌ **DON'T use this skill when:**

- 首次安装 OpenClaw → 用官方安装命令
- 源码型 OpenClaw 的 git pull 更新 → `cd ~/OpenClaw && git pull && pnpm install && pnpm build`
- OpenClaw 配置问题 → `openclaw config`

## 核心概念：两种安装形态

| 形态 | 位置 | 特点 | 升级方式 |
|------|------|------|---------|
| **源码型** | `~/OpenClaw/`（git clone） | 可改源码、体积大、需构建 | `git pull` + `pnpm install` + `pnpm build` |
| **非源码型** | `/usr/local/node22/lib/node_modules/openclaw/`（npm -g） | 即装即用、不可改源码 | `npm install -g openclaw@latest` |

> 💡 本 SKILL 专注于**非源码型（npm 全局包）**的升级。

## 完整升级流程

### Step 1：确认当前版本与最新版本

```bash
# 当前版本
npm list -g openclaw

# 最新版本（需要代理）
export http_proxy=http://<代理地址>:<端口>
export https_proxy=http://<代理地址>:<端口>
npm view openclaw version
```

### Step 2：禁用源码型安装（如有）

源码型目录可能干扰 npm 全局包的路径解析。如果存在源码型安装，建议禁用：

```bash
# 重命名即可，不删除，随时可恢复
mv ~/OpenClaw ~/OpenClaw.disabled

# 恢复方式：mv ~/OpenClaw.disabled ~/OpenClaw
```

### Step 3：处理 sudo npm registry 问题（关键！）

> ⚠️ **这是最容易踩坑的地方**。`sudo npm` 使用的是 root 用户的 `.npmrc`，与当前用户的 npm 配置**完全独立**。

```bash
# 检查当前用户的 registry
npm config get registry
# 可能是：https://mirrors.cloud.tencent.com/npm/

# 检查 sudo 的 registry（可能不同！）
sudo npm config get registry
# 可能是：https://registry.npmmirror.com/

# 如果 sudo 的 registry 是国内镜像，在 WSL 代理环境下反而会超时
# 解决：将 sudo 的 registry 切到官方源（走代理）
sudo npm config set registry https://registry.npmjs.org/
```

**核心洞察**：

| 场景 | registry 选择 | 原因 |
|------|-------------|------|
| 有代理 | `registry.npmjs.org` | 代理可直连官方源，国内镜像反而可能超时 |
| 无代理 | 国内镜像（npmmirror / tencent） | 无法直连官方源，必须走镜像 |

### Step 4：传递代理环境变量给 sudo

> ⚠️ `sudo` 默认重置环境变量，不会继承当前 shell 的 `http_proxy`/`https_proxy`。

```bash
# ❌ 错误：sudo 不继承代理
export http_proxy=http://<代理地址>:<端口>
sudo npm install -g openclaw@latest  # 会超时！

# ✅ 正确：显式传递代理给 sudo
sudo http_proxy=http://<代理地址>:<端口> \
     https_proxy=http://<代理地址>:<端口> \
     npm install -g openclaw@latest
```

### Step 5：处理 Git SSH 依赖问题

OpenClaw 的某些依赖通过 SSH 协议引用 GitHub 仓库（如 `ssh://git@github.com/...`），WSL 中无 SSH key 会导致 `Permission denied (publickey)`。

```bash
# 临时将 git SSH 重定向为 HTTPS（安装完记得还原）
git config --global url."https://github.com/".insteadOf "ssh://git@github.com/"
git config --global url."https://github.com/".insteadOf "git@github.com:"
```

> ⚠️ 这只是临时配置，Step 9 会清理。

### Step 6：清理上次失败安装的残留

如果之前 `npm install` 失败过，会留下临时目录导致 `ENOTEMPTY` 错误：

```bash
# 清理残留
sudo rm -rf /usr/local/node22/lib/node_modules/.openclaw-*
sudo rm -rf /usr/local/node22/lib/node_modules/openclaw
```

### Step 7：执行升级

```bash
export http_proxy=http://<代理地址>:<端口>
export https_proxy=http://<代理地址>:<端口>
sudo http_proxy=http://<代理地址>:<端口> \
     https_proxy=http://<代理地址>:<端口> \
     npm install -g openclaw@<目标版本>
```

> 💡 如果 GnuTLS 问题导致 git 依赖拉取失败，可临时关闭 SSL 验证：
> `git config --global http.sslVerify false`（安装完务必还原！）

### Step 8：验证升级

```bash
npm list -g openclaw
# 期望：openclaw@<目标版本>

node /usr/local/node22/lib/node_modules/openclaw/openclaw.mjs --version
# 期望：OpenClaw <版本号>
```

### Step 9：清理临时配置

```bash
# 还原 git SSL 验证
git config --global http.sslVerify true

# 移除 SSH→HTTPS 重定向（逐条移除，可能有多条）
git config --global --unset url."https://github.com/".insteadOf
# 重复执行直到没有输出
```

### Step 10：启动验证

```bash
# 方式一：直接启动 gateway
node /usr/local/node22/lib/node_modules/openclaw/openclaw.mjs gateway --port 18789

# 方式二：使用启动脚本
# Windows 端双击 启动OpenClaw.bat
```

## 故障排查速查表

| 问题 | 原因 | 方案 |
|------|------|------|
| `EACCES: permission denied` | npm 全局目录需 root 权限 | 用 `sudo npm install -g` |
| `ETIMEDOUT` 连接 npmmirror | sudo 的 registry 是国内镜像，代理下反而超时 | `sudo npm config set registry https://registry.npmjs.org/` |
| `Permission denied (publickey)` | npm 依赖用 git SSH 协议 | 配置 git URL 重写：SSH→HTTPS |
| `ENOTEMPTY: directory not empty` | 上次失败安装残留 | `sudo rm -rf .../node_modules/.openclaw-* .../node_modules/openclaw` |
| `GnuTLS recv error` | WSL git GnuTLS 与代理不兼容 | 临时 `git config --global http.sslVerify false` |
| `EBADENGINE` undici 警告 | Node.js 版本稍低于依赖要求 | 通常可忽略，不影响运行 |
| 升级后 `npm list` 显示旧版本 | 残留目录未清理 | 先 Step 6 清理再安装 |

## 升级流程决策树

```
npm install -g openclaw@latest
│
├─ 成功 → 验证版本 → 完成
│
├─ EACCES → 加 sudo 重试
│   │
│   ├─ 成功 → 完成
│   │
│   ├─ ETIMEDOUT (npmmirror) → 切 sudo registry 到 npmjs.org → 重试
│   │
│   ├─ Permission denied (publickey) → 配 git SSH→HTTPS → 重试
│   │
│   ├─ ENOTEMPTY → 清理残留目录 → 重试
│   │
│   └─ GnuTLS error → 临时关 sslVerify → 重试 → 还原
│
└─ 其他 → 检查网络/代理/Node版本
```

## WSL 中 sudo npm 的三大陷阱

### 陷阱 1：sudo 的 npm 配置独立

```
~/.npmrc          → 当前用户的配置
/root/.npmrc      → sudo (root) 的配置
```

**症状**：用户配了 tencent 镜像，sudo 用的是 npmmirror 镜像，两者可能都不适合当前网络环境。

**解决**：`sudo npm config set registry <正确源>`

### 陷阱 2：sudo 不继承代理环境变量

```bash
# 当前 shell 有代理
export http_proxy=http://<代理地址>:<端口>

# sudo 后环境变量丢失
sudo npm install -g openclaw  # 超时！

# 必须显式传递
sudo http_proxy=http://<代理地址>:<端口> npm install -g openclaw
```

### 陷阱 3：国内镜像 ≠ 更快

在有代理的 WSL 环境下：

| 场景 | 推荐源 | 原因 |
|------|--------|------|
| 有代理 | `registry.npmjs.org` | 代理已打通外网，官方源最稳定 |
| 无代理 | 国内镜像 | 无法直连官方源，必须走镜像 |

## Related Skills

- `hermes-agent-install` - Hermes Agent 安装（同样涉及 WSL 代理问题）
