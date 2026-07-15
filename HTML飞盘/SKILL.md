---
name: HTML飞盘
description: >
  将本地 HTML 文件上传到飞书云盘，返回飞书链接。
  触发词：飞盘、上传、推 HTML、HTML 上飞书、HTML 到云盘、HTML 飞书、上传 HTML、HTML 上传、HTML 飞盘。
  底层：lark-cli drive +upload（飞书官方 CLI）。
  输入：本地 HTML 文件路径。
  输出：飞书云盘链接（https://*.feishu.cn/file/<token>）。
metadata:
  openclaw:
    emoji: 🛸
    requires:
      lark-cli: ">=1.0.59"
      oauth: user scope drive:file:upload, drive:drive.metadata:readonly
---

# HTML飞盘

> 把本地 HTML 文件"飞"到飞书云盘。

## 强制规定（最高优先级）

1. **一条命令搞定** — `Set-Location` 与 `lark-cli drive +upload` 必须位于**同一条** PowerShell 命令中，以 `;` 分隔。
2. **避免 junction 路径** — 当前工作目录不得位于 Windows JUNCTION 路径之后。
3. **使用相对路径** — `--file` 参数必须为 `./文件名` 形式。
4. **核心命令不可变** — 优先使用本技能定义的命令模板，禁止随意修改。

---

## 触发词

| 触发词 | 动作 |
|---|---|
| 飞盘、HTML飞盘 | 上传 HTML 到飞书 |
| 上传 HTML、HTML 上传 | 同上 |
| HTML 上飞书、HTML 到云盘 | 同上 |
| 推 HTML | 同上 |
| 把 x.html 飞盘 | 上传指定文件 |

---

## 输入

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | path | 是 | 本地 HTML 文件绝对路径 |

## 输出

| 字段 | 说明 |
|---|---|
| `data.url` | 飞书云盘直链（https://*.feishu.cn/file/<token>）|
| `data.file_token` | 飞书云盘文件 token |
| `data.file_name` | 上传后的文件名 |
| `data.size` | 文件大小（bytes）|
| `data.version` | 文件版本号 |

---

## 执行步骤

### 步骤 1：环境检查

```powershell
lark-cli --version
lark-cli auth status --verify
Test-Path <HTML 文件绝对路径>
```

**判定标准：**
- `lark-cli --version` 输出版本号 ≥ 1.0.59
- `lark-cli auth status --verify` 返回 `identity=user`、`tokenStatus=valid`、`verified=true`、`scope` 含 `drive:file:upload` 与 `drive:drive.metadata:readonly`
- `Test-Path <文件路径>` 返回 `True`

**失败处理：**
- lark-cli 未安装：`npm install -g @larksuite/cli`
- 认证失败：`lark-cli auth login --scope "drive:file:upload drive:drive.metadata:readonly"`
- 文件不存在：中止，提示用户提供有效路径

### 步骤 2：junc 排查（仅 Windows）

```powershell
cmd /c "dir /AL C:\Users\<user>"
```

若输出含 `<JUNCTION>` 行，且当前工作目录路径包含该 junction 入口，必须改用其指向的真实目录。

### 步骤 3：单命令上传

```powershell
$file = "<HTML 文件绝对路径>"
$dir = Split-Path $file
$name = Split-Path $file -Leaf
Set-Location $dir; lark-cli drive +upload --as user --file "./$name" --name $name --format pretty
```

**约束：**
- `Set-Location` 与 `lark-cli drive +upload` 必须位于同一条 PowerShell 命令中（mavis bash 工具的 `workdir` 参数跨调用不持久）
- `--file` 参数为相对路径 `./<文件名>` 形式

### 步骤 4：结果验证

返回 JSON 中 `ok == true` 且 `data.url` 非空，则任务完成。`data.url` 即为飞书云盘链接。

`ok != true` 时按错误信息进入对应故障分支。

---

## 故障分支

| 错误信息片段 | 根因 | 修复 |
|---|---|---|
| `command not found` | lark-cli 未装 | `npm install -g @larksuite/cli` |
| `missing_scope` / `tokenStatus: invalid` | 未登录或权限不足 | `lark-cli auth login --scope "drive:file:upload drive:drive.metadata:readonly"` |
| `unsafe file path: cannot resolve symlinks` | cwd 位于 Windows junction 路径下 | `cmd /c "dir /AL C:\Users\<user>"` 定位 junction，切换至其指向的真实目录后重试 |
| `must be a relative path` | `--file` 传入绝对路径 | 使用 `./文件名` 相对路径，并保证 `Set-Location` 已切至文件目录 |
| `file not found` / `cannot read file` | 文件路径错误或 cwd 未切换 | `Test-Path <路径>` 验证文件存在并重做步骤 3 |
| `network error` | 网络中断或飞书服务不可用 | 等待后重试，或验证 `https://feishu.cn` 可达 |

---

## 关键约束

1. **workdir 不持久** — mavis bash 工具每次调用是新 PowerShell 进程，`workdir` 参数和 `Set-Location` 跨调用不生效。`Set-Location` 与 `lark-cli` 必须用 `;` 串联为单条命令。
2. **避免 junction 路径** — Windows 上 `.mavis` 这类 junction 路径会让 Go 的 `EvalSymlinks` 解析失败，必须用真实目录。
3. **必须用相对路径** — `--file` 不接受绝对路径，先切目录再用 `./文件名`。
4. **三项检查全部通过** — lark-cli 安装、OAuth 授权、文件存在，三者缺一不可。

---

## 完整脚本

```powershell
# ========== 配置区 ==========
$file = "C:\path\to\test.html"
# ============================

# 步骤 1：环境检查
if (-not (Get-Command lark-cli -ErrorAction SilentlyContinue)) {
    Write-Error "lark-cli 未安装，请先跑: npm install -g @larksuite/cli"
    exit 1
}

$auth = lark-cli auth status --verify | ConvertFrom-Json
if ($auth.identity -ne "user" -or $auth.tokenStatus -ne "valid") {
    Write-Error "lark-cli 未登录或 token 过期，请跑: lark-cli auth login --recommend"
    exit 1
}

if (-not (Test-Path $file)) {
    Write-Error "文件不存在: $file"
    exit 1
}

# 步骤 3：单命令上传
$dir = Split-Path $file
$name = Split-Path $file -Leaf
Write-Host "文件: $file ($((Get-Item $file).Length) bytes)"

$result = Set-Location $dir; lark-cli drive +upload --as user --file "./$name" --name $name --format pretty | ConvertFrom-Json

# 步骤 4：结果验证
if ($result.ok -eq $true) {
    Write-Host "上传成功"
    Write-Host "文件名: $($result.data.file_name)"
    Write-Host "飞书链接: $($result.data.url)"
    Write-Host "file_token: $($result.data.file_token)"
} else {
    Write-Error "上传失败: $($result.error.message)"
    Write-Host "请参考 SKILL.md 故障分支段定位"
    exit 1
}
```

---

## 已知限制

1. **首次 OAuth 需用户交互** — `lark-cli auth login --recommend` 需要用户在浏览器完成授权，agent 无法在非交互 shell 中完成。
2. **文件大小限制** — `drive +upload` 单次上传 ≤ 20MB 自动使用 multipart，超过此上限走分片上传流程。
3. **文件名特殊字符** — 文件名含 `&`、`%` 等 shell 特殊字符时需先转义或重命名。
4. **个人空间权限** — 飞书 app 需在后台开通 `drive:file:upload` 与 `drive:drive.metadata:readonly` 两个 scope，且当前用户对个人云盘有写权限。
5. **跨平台差异** — Windows junction 路径陷阱仅在 Windows 平台出现，macOS/Linux 不受影响。