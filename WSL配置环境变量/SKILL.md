# WSL 配置环境变量

> 本技能用于在 WSL 中配置全局环境变量，确保在所有场景下（交互式 shell、非交互式 shell、systemd 服务、WSLENV 不生效等）都能被读取。

---

## 🎯 根因总结（必读）

**为什么环境变量传不到 OpenClaw？**

| 方案 | 失败原因 |
|------|---------|
| `~/.bashrc` | 只在交互式 non-login shell 生效 |
| `~/.profile` | 只在 login shell 生效 |
| `/etc/environment` | PAM 模块加载，systemd 服务不经过 PAM |
| WSLENV | 只在"Windows 启动 WSL 程序"时生效，WSL 内部 systemd 服务触达不到 |
| systemd --user | WSL 默认不支持完整的 user systemd 和 D-Bus session |

**唯一有效方案**：`systemd service override` + `EnvironmentFile=/etc/environment`

---

## 需要设置的变量清单

| 变量名 | 值 |
|--------|-----|
| SKILLS_DB_PATH | /mnt/d/2Study/StudyNotes/.db |
| HOME_PHOTOS_DIR | /mnt/d/2Study/StudyNotes/.db/HomeHub/photos |
| MEDAL_RESOURCE_PATH | /mnt/d/2Study/StudyNotes/.db/MedalHub |
| CHEF_OUTPUT_DIR | /mnt/d/2Study/StudyNotes/.db/CookHub |
| MEMO_DB_PATH | /mnt/d/2Study/StudyNotes/.db/MemoHub |
| MEMO_MEDIA_DIR | /mnt/d/2Study/StudyNotes/.db/MemoHub/media |

---

## 完整配置步骤（必须全部执行）

### Step 1：写入 /etc/environment（用户 shell 层 + systemd 源文件）

```bash
sudo tee /etc/environment << 'EOF'
SKILLS_DB_PATH=/mnt/d/2Study/StudyNotes/.db
HOME_PHOTOS_DIR=/mnt/d/2Study/StudyNotes/.db/HomeHub/photos
MEDAL_RESOURCE_PATH=/mnt/d/2Study/StudyNotes/.db/MedalHub
CHEF_OUTPUT_DIR=/mnt/d/2Study/StudyNotes/.db/CookHub
MEMO_DB_PATH=/mnt/d/2Study/StudyNotes/.db/MemoHub
MEMO_MEDIA_DIR=/mnt/d/2Study/StudyNotes/.db/MemoHub/media
EOF
```

---

### Step 2：创建 systemd service override（⭐关键步骤）

**原理**：systemd 支持 `xxx.service.d/` 目录存放增量配置文件（drop-in override），会自动合并到原始 service 文件中，**不修改原始文件**。

```bash
sudo mkdir -p /etc/systemd/system/openclaw-gateway.service.d
sudo tee /etc/systemd/system/openclaw-gateway.service.d/override.conf << 'EOF'
[Service]
EnvironmentFile=/etc/environment
EOF
```

---

### Step 3：验证 systemd 加载成功

```bash
systemctl show openclaw-gateway --property=Environment
```

**期望输出**：应包含 `HOME_PHOTOS_DIR=/mnt/d/2Study/StudyNotes/.db/HomeHub/photos` 等变量

---

### Step 4：Windows 重启验证

```
1. Windows 完全重启（不是 WSL reconnect）
2. WSL 启动后，OpenClaw 自动运行
3. 验证命令：
   python3 -c "import os; print(os.environ.get('HOME_PHOTOS_DIR'))"
   期望输出：/mnt/d/2Study/StudyNotes/.db/HomeHub/photos
```

---

## 前置要求

### 需要有 sudo 密码

如果没有设置过 sudo 密码，在 Windows 管理员 PowerShell 中执行：

```powershell
wsl -u root -- passwd feather
```

然后输入新密码并确认。

---

## 验证清单

| 验证场景 | 命令 | 期望输出 |
|---------|------|---------|
| /etc/environment 内容 | `cat /etc/environment` | 应包含所有变量 |
| override 文件存在 | `cat /etc/systemd/system/openclaw-gateway.service.d/override.conf` | 应包含 `EnvironmentFile=/etc/environment` |
| systemd 环境注入 | `systemctl show openclaw-gateway --property=Environment` | 应包含所有变量 |
| 交互式 shell | `python3 -c "import os; print(os.environ.get('HOME_PHOTOS_DIR'))"` | `/mnt/d/2Study/StudyNotes/.db/HomeHub/photos` |

---

## 方案对比

| 方案 | 适用场景 | 生效范围 | 关键限制 |
|------|---------|---------|---------|
| `/etc/environment` | 交互式 shell | 用户所有进程 | systemd 服务**不生效** |
| `~/.bashrc` | 交互式 shell | 当前用户 | 非交互式/shell 脚本**不生效** |
| `~/.profile` | login shell | login 会话 | 服务/脚本**不生效** |
| WSLENV | Windows → WSL 调用 | Windows 启动的程序 | WSL 内部服务**不生效** |
| `systemd override` + `EnvironmentFile` | systemd 服务 | OpenClaw 等系统服务 | ✅ **唯一有效方案** |

---

## 常见问题

### Q: 为什么要用 override.conf？不直接改 service 文件？
A: override.conf 是 systemd 官方推荐的"增量修改"方式，不修改原始文件，安全且易于管理。直接改原始 service 文件在 OpenClaw 更新时会被覆盖。

### Q: daemon-reload 什么时候需要？
A: 如果是 Windows 完全重启，不需要（systemd 重启时自动重新加载）。如果只是 WSL reconnect，需要：`sudo systemctl daemon-reload`

### Q: 为什么 WSLENV 对 systemd 服务无效？
A: WSLENV 是 Windows 和 WSL 之间的桥接机制，只在 Windows 启动 WSL 程序时生效。OpenClaw 是 WSL 内部通过 systemd 启动的，完全在 Windows 上下文之外。

### Q: /etc/environment 有什么限制？
A: 只支持 `VAR=value` 格式，不支持 `VAR=$(cmd)` 命令替换。

### Q: 改完发现变量还是读不到？
A: 按以下顺序排查：
   1. `cat /etc/environment` — 确认文件内容正确
   2. `cat /etc/systemd/system/openclaw-gateway.service.d/override.conf` — 确认 override 存在
   3. `sudo systemctl daemon-reload` — 重新加载 systemd 配置
   4. `sudo systemctl restart openclaw-gateway` — 重启服务
   5. `systemctl show openclaw-gateway --property=Environment` — 确认变量已注入

---

## 涉及路径

| 路径 | 用途 | 是否被修改 |
|------|------|----------|
| `/etc/environment` | 系统级环境变量（用户 shell + systemd 源文件） | 新增变量 |
| `/etc/systemd/system/openclaw-gateway.service` | OpenClaw 原始 service 文件 | **未修改** |
| `/etc/systemd/system/openclaw-gateway.service.d/override.conf` | systemd 增量配置（OpenClaw 用） | **新增文件** |

---

## 更新记录

- 2026-05-25：首次完整探索，发现 OpenClaw 是 systemd 服务，必须通过 `override.conf` + `EnvironmentFile` 机制注入环境变量。补充了根因总结、验证步骤、方案对比和排查路径。
