# 小龙虾CC交互

> Claude Code CLI 与 OpenClaw 协作框架

## 目录说明

- `SKILL.md` — 技能定义（桥接文件）
- `test-results.md` — 实测结果记录
- `references/` — 参考资料

## 技能定义

```yaml
name: 小龙虾CC交互
description: |
  OpenClaw 真哥 编排 Claude Code CLI 进行多轮代码协作的框架。
  适用场景：复杂代码生成、多文件项目构建、错误修复、多轮对话记忆。
  通过 exec 调用 claude CLI，使用 --session-id 和 --resume 实现多轮交互。
triggers:
  - "让 Claude Code 写代码"
  - "和 claude code 交互"
  - "多轮写代码"
  - "claude code 多轮"
tools:
  - exec
context:
  - 需要 Claude Code CLI 已安装（路径: /mnt/c/Users/辰辰洋洋/AppData/Roaming/npm/claude）
  - 需要 Node.js 环境
  - 建议为每次多轮任务生成独立 UUID session
```

## 核心用法

### 单次指令模式

```bash
claude -p "你的指令" \
  --session-id "$(python3 -c 'import uuid; print(uuid.uuid4())')" \
  --output-format text \
  --dangerously-skip-permissions
```

### 多轮续接模式

```bash
# 第1轮：创建 session
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
claude -p "任务1" --session-id "$SESSION_ID" --output-format text --dangerously-skip-permissions

# 第2轮：延续同一 session（用 --resume）
claude -p "任务2" --resume "$SESSION_ID" --output-format text --dangerously-skip-permissions

# 第3轮：继续...
claude -p "任务3" --resume "$SESSION_ID" --output-format text --dangerously-skip-permissions
```

### 关键约束

| 约束项 | 说明 |
|--------|------|
| Session ID 格式 | 必须是有效 UUID（用 `python3 -c "import uuid; print(uuid.uuid4())"` 生成） |
| 续命方式 | 后续轮次必须用 `--resume`，不能用 `--session-id` |
| Windows 路径 | 加 `--dangerously-skip-permissions` 绕过权限弹窗 |
| Timeout | 建议 15-20s/轮，复杂任务可 25-30s |

## 架构

```
用户 → 真哥（编排者）
   ↓ 解析需求、拆解任务
Claude Code CLI（执行者）
   ↓ 写文件、执行命令
真哥验收结果 → 用户
```