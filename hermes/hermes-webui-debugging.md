
---

## 关键发现（补充）：wsl 命令的 PATH 问题

### 问题现象

在 Windows CMD 里执行 `wsl hermes-web-ui status` 报错：
```
/bin/bash: line 1: hermes-web-ui: command not found
```

但在 WSL 终端里直接执行 `hermes-web-ui status` 是正常的。

### 根因

`wsl <command>` 以**非交互式 shell** 执行，不会加载登录 shell 的 profile，导致 `/home/feather/.local/bin` 不在 PATH 中。

`wsl bash -l -c "<command>"` 使用登录 shell，能正确加载 PATH。

### 验证

```bash
# 失败（PATH 不完整）
wsl hermes-web-ui status

# 成功（加载登录 shell）
wsl bash -l -c "hermes-web-ui status"
```

### 最终脚本（简化版，能正常工作）

```bat
@echo off
echo Starting Hermes Web UI...
echo.
wsl bash -l -c "hermes-web-ui status"
if %errorlevel% neq 0 (
    echo Starting service...
    wsl bash -l -c "hermes-web-ui start"
)
echo Waiting for server...
timeout /t 5 /nobreak
echo Opening browser...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8648"
echo Done!
pause
```

## 工具踩坑

### write_file 工具缓存问题

发现 `write_file` 工具写入后文件内容没更新（可能是缓存问题），但终端显示成功。

**Workaround**：使用 terminal 的 heredoc 方式写入：
```bash
cat > /path/to/file << 'EOF'
content here

---

## 关键发现（补充）：wsl 命令的 PATH 问题

### 问题现象

在 Windows CMD 里执行  报错：


但在 WSL 终端里直接执行   ✗ hermes-web-ui is not running 是正常的。

### 根因

 以**非交互式 shell** 执行，不会加载登录 shell 的 profile，导致  不在 PATH 中。

 使用登录 shell，能正确加载 PATH。

### 验证



### 最终脚本（简化版，能正常工作）

Starting Hermes Web UI...

## 工具踩坑

### write_file 工具缓存问题

发现  工具写入后文件内容没更新（可能是缓存问题），但终端显示成功。

**Workaround**：使用 terminal 的 heredoc 方式写入：


## 经验总结（更新）

1. **不要静默丢弃关键输出** - 启动脚本应该显示启动日志，方便排查问题
2. **用健康检查替代固定等待** - 循环检查端口可用性，比  更可靠
3. **不要重复造轮子** - 严格按照官方文档的启动方式，不要自行添加额外的初始化逻辑
4. **认证是可选的** - hermes-web-ui 的 token 认证可以禁用，直接访问首页即可
5. **PATH 问题排查顺序** -  命令找不到时，先用 /home/feather/.local/node_modules/lib
├── hermes-web-ui@0.4.7
├── mmx-cli@1.0.11
└── openclaw@2026.4.22 确认包是否存在，再用 /home/feather/.local/node_modules/lib/node_modules 确认安装路径，最后检查软链接
6. **Windows bat 调用 WSL 命令要用 ** - 确保加载完整的 PATH 环境变量
7. **工具写入失败时换用 terminal heredoc** - write_file 可能有缓存问题


---

## 关键发现（补充）：wsl 命令的 PATH 问题

### 问题现象

在 Windows CMD 里执行 `wsl hermes-web-ui status` 报错：
```
/bin/bash: line 1: hermes-web-ui: command not found
```

但在 WSL 终端里直接执行 `hermes-web-ui status` 是正常的。

### 根因

`wsl <command>` 以非交互式 shell 执行，不会加载登录 shell 的 profile，导致 `/home/feather/.local/bin` 不在 PATH 中。

`wsl bash -l -c "<command>"` 使用登录 shell，能正确加载 PATH。

### 验证

```bash
# 失败（PATH 不完整）
wsl hermes-web-ui status

# 成功（加载登录 shell）
wsl bash -l -c "hermes-web-ui status"
```

### 最终脚本（简化版，能正常工作）

```bat
@echo off
echo Starting Hermes Web UI...
echo.
wsl bash -l -c "hermes-web-ui status"
if %errorlevel% neq 0 (
    echo Starting service...
    wsl bash -l -c "hermes-web-ui start"
)
echo Waiting for server...
timeout /t 5 /nobreak
echo Opening browser...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8648"
echo Done!
pause
```

## 工具踩坑

### write_file 工具缓存问题

发现 write_file 工具写入后文件内容没更新（可能是缓存问题），但终端显示成功。

Workaround：使用 terminal 的 heredoc 方式写入，但要注意特殊字符避免被 shell 解释。

## 经验总结（更新）

1. 不要静默丢弃关键输出 - 启动脚本应该显示启动日志，方便排查问题
2. 用健康检查替代固定等待 - 循环检查端口可用性，比 sleep 3 更可靠
3. 不要重复造轮子 - 严格按照官方文档的启动方式，不要自行添加额外的初始化逻辑
4. 认证是可选的 - hermes-web-ui 的 token 认证可以禁用，直接访问首页即可
5. PATH 问题排查顺序 - which 命令找不到时，先用 npm list -g 确认包是否存在，再用 npm root -g 确认安装路径，最后检查软链接
6. Windows bat 调用 WSL 命令要用 wsl bash -l -c - 确保加载完整的 PATH 环境变量
7. 工具写入失败时换用 terminal heredoc - write_file 可能有缓存问题
