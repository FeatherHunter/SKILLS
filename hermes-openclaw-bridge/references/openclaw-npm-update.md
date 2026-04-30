# OpenClaw npm Update

更新 OpenClaw 全局 npm 包并重启 PM2 管理的 Gateway 进程。

## 问题背景

OpenClaw 通过 npm 全局安装，但有两个不同的安装位置：
- **新位置**（npm 默认）：`~/.local/node_modules/lib/node_modules/openclaw/`
- **旧位置**（系统 node）：`/usr/local/node22/lib/node_modules/openclaw/`

PM2 管理的 `openclaw-gateway` 进程通过 `/home/feather/start-gateway.sh` 启动，其中 hardcode 了旧路径。

## 更新步骤

### 1. npm 全局更新
```bash
npm update -g openclaw
```

### 2. 验证新版本
```bash
openclaw --version
# 或
openclaw gateway --version
```

### 3. 检查 PM2 启动脚本路径
```bash
pm2 show openclaw-gateway | grep script path
cat /home/feather/start-gateway.sh | grep "node.*openclaw"
```

### 4. 更新启动脚本（如果指向旧路径）
编辑 `/home/feather/start-gateway.sh`，将旧路径替换为新路径：
```diff
- exec /usr/local/node22/bin/node /usr/local/node22/lib/node_modules/openclaw/openclaw.mjs gateway --port 18789
+ exec /usr/local/node22/bin/node /home/feather/.local/node_modules/lib/node_modules/openclaw/openclaw.mjs gateway --port 18789
```

### 5. 重启 PM2 进程
```bash
pm2 restart openclaw-gateway --update-env
```

### 6. 验证 Gateway 版本
```bash
# 方法1：检查 PM2 日志中的启动标志
grep "🦞\|v2026" ~/.pm2/logs/openclaw-gateway-out.log | tail -5

# 方法2：确认进程加载的模块路径
cat /proc/<PID>/maps | grep openclaw | head -3
```

## 验证清单
- [ ] `openclaw --version` 显示新版本
- [ ] PM2 日志中 Gateway 启动时间为你重启的时间
- [ ] 微信通道（openclaw-weixin）正常在线

## 相关命令速查
```bash
# 查看 OpenClaw 相关进程
ps aux | grep openclaw | grep -v grep

# 查看 PM2 进程状态
pm2 list | grep openclaw

# 查看 Gateway 日志
tail -20 ~/.pm2/logs/openclaw-gateway-out.log

# 查看 Hermes Gateway 状态（注意：这是独立进程，和 PM2 管理的 openclaw-gateway 不是同一个）
hermes gateway status
```

## 关键发现

**双 Gateway 架构：**
- `hermes gateway run` — Hermes Agent 自己的 gateway（`hermes gateway status` 显示的 PID）
- `openclaw-gateway`（PM2 管理）— 独立的 OpenClaw 进程，两者在不同端口运行

两者都叫 "gateway"，容易混淆。更新 openclaw npm 包只需重启 PM2 这边的即可。
