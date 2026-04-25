---
name: skill-symlink
description: 将Windows端的Hermes skill软链接到WSL的hermes skills目录
---

# Skill 软链接工具

把 Windows 上的 skill 文件同步到 WSL 的 `~/.hermes/skills/` 目录。

## 使用场景

用户说：
- "帮我软链接XXX skill"
- "创建XXX的软链接"
- "同步XXX到WSL"

## 规则

| 项目 | 值 |
|------|-----|
| **Windows 源目录** | `D:\2Study\StudyNotes\SKILLS` |
| **WSL 目标目录** | `/home/feather/.hermes/skills` |
| **链接方式** | 单文件软链接 `SKILL.md` |

## 执行流程

```
1. 解析 skill 名称
   - 用户说 "daily-checkin" → 目录名相同
   - 用户说 "XXX skill" → 去掉空格，尝试匹配

2. 确认源文件存在
   - 检查 `D:\2Study\StudyNotes\SKILLS\{skill-name}\SKILL.md`
   - 如果不存在，列出相似名称供用户选择

3. 确认目标目录存在
   - 检查 `~/.hermes/skills/{skill-name}/`
   - 不存在则创建

4. 执行软链接
   - 命令: `ln -sf {源文件} {目标文件}`
   - 验证链接是否成功

5. 反馈结果
   - 成功：显示链接路径
   - 失败：显示错误原因
```

## 命令模板

```bash
# 1. 创建目标目录（如不存在）
mkdir -p /home/feather/.hermes/skills/{skill-name}

# 2. 创建软链接
ln -sf /mnt/d/2Study/StudyNotes/SKILLS/{skill-name}/SKILL.md \
       /home/feather/.hermes/skills/{skill-name}/SKILL.md

# 3. 验证
ls -la /home/feather/.hermes/skills/{skill-name}/SKILL.md
```

## 示例

### 用户："帮我软链接 daily-checkin"

```bash
mkdir -p /home/feather/.hermes/skills/daily-checkin
ln -sf /mnt/d/2Study/StudyNotes/SKILLS/daily-checkin/SKILL.md \
       /home/feather/.hermes/skills/daily-checkin/SKILL.md
ls -la /home/feather/.hermes/skills/daily-checkin/SKILL.md
```

输出：
```
✅ daily-checkin/SKILL.md → /mnt/d/2Study/StudyNotes/SKILLS/daily-checkin/SKILL.md
```

## 错误处理

| 错误 | 原因 | 处理 |
|------|------|------|
| 源文件不存在 | skill名称拼写错误 | 列出相似名称供选择 |
| 目标目录无写权限 | 权限问题 | 提示用户 |
| 软链接已存在 | 重复执行 | 覆盖更新，告知用户 |

## 审计：检查同步状态

用户说：
- "检查skill同步状态"
- "哪些skill还没同步"
- "查看同步情况"

### 审计方法

用以下 Python 脚本自动分类：

```python
import os

wsl_base = "/home/feather/.hermes/skills"
win_base = "/mnt/d/2Study/StudyNotes/SKILLS"

win_skills = [d for d in os.listdir(win_base)
              if os.path.isdir(os.path.join(win_base, d)) and not d.endswith('.zip')]

wsl_has_dir = set(d for d in os.listdir(wsl_base)
                  if os.path.isdir(os.path.join(wsl_base, d)) and not d.startswith('.'))

synced, not_synced, missing = [], [], []

for name in sorted(win_skills):
    if name in wsl_has_dir:
        skill_md = os.path.join(wsl_base, name, "SKILL.md")
        if os.path.islink(skill_md):
            synced.append(name)
        else:
            not_synced.append(name)
    else:
        missing.append(name)

# 打印结果
```

### 四类结果及含义

| 类别 | 含义 | 处理 |
|------|------|------|
| ✅ 已同步 | WSL有目录 + SKILL.md是软链接 | 无需操作 |
| ⚠️ 有目录但未软链接 | WSL有目录但SKILL.md不是链接 | 补充软链接 |
| 🔲 WSL有目录但无SKILL.md | 系统内置skill | 不处理 |
| ❌ Windows有但WSL没有 | 需要新建目录+软链接 | 创建同步 |

### 当前状态（2026-04-22）

| 类别 | 数量 | 详情 |
|------|------|------|
| ✅ 已同步 | 6个 | daily-checkin, daily-schedule, real-assistant, skill-symlink, study-planner, hermes-openclaw-bridge |
| ❌ 待同步 | 8个 | find-skills-skill-1.0.0, glm-ocr-to-en-word, hermes-agent-install-1.0.0, hourly-care, iflytek-ocr-to-en-word, minimax-skills, openclaw-update-1.0.0, pdf-to-en-word |

### 待同步的命令模板

```bash
# 格式：目录名与Windows源名相同（不要-1.0.0后缀）
mkdir -p /home/feather/.hermes/skills/{skill-name}
ln -sf /mnt/d/2Study/StudyNotes/SKILLS/{windows-dir-name}/SKILL.md \
       /home/feather/.hermes/skills/{skill-name}/SKILL.md
```

注意：Windows源目录名可能带版本号（如 `find-skills-skill-1.0.0`），WSL目标目录名通常不带版本号。

## 注意事项

- 软链接是符号链接，删除Windows源文件会导致链接失效
- 修改Windows文件后，WSL立即生效（无需重启）
- 如果要快速查看当前已配置的软链接，执行：
  ```bash
  ls -la ~/.hermes/skills/ | grep "\.md ->"
  ```
