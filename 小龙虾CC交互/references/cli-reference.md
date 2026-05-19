# Claude Code CLI 参考资料

## 官方文档

- Claude Code CLI 安装：https://claude.com/code
- 官方 CLI Reference：https://docs.anthropic.com/en/docs/claude-code

## 关键 Flag 说明

| Flag | 作用 |
|------|------|
| `-p, --print` | 非交互模式，输出到 stdout |
| `--session-id <uuid>` | 创建新 session（仅首次） |
| `-r, --resume <uuid>` | 续接已有 session |
| `-c, --continue` | 继续当前目录最近一次 session |
| `--output-format text` | 输出纯文本（适合脚本解析） |
| `--dangerously-skip-permissions` | 跳过所有权限确认 |
| `--add-dir <path>` | 允许访问的额外目录 |
| `--allowed-tools <tools>` | 允许使用的工具白名单 |
| `--model <model>` | 指定模型 |
| `--no-session-persistence` | 不持久化 session（仅 --print 可用） |

## Session 生命周期

```
1. 创建: --session-id <UUID>
2. 续接: --resume <UUID>  （不是 --session-id！）
3. 查询: --resume（无参数则交互式选择）
4. 继续: -c（当前目录最近 session）
```

## 多轮模式对比

| 模式 | 命令 | 适用场景 |
|------|------|----------|
| 单次指令 | `claude -p "指令"` | 简单一次性任务 |
| 多轮同一 exec | `claude ... && claude ... --resume` | 复杂多步骤任务（推荐） |
| 持久 session | `claude` 进入交互模式 | 长时间开发 |
| tmux 模式 | `claude --tmux --worktree <name>` | 并行工作流 |

## 与 OpenClaw 协作架构

```
OpenClaw 真哥（编排层）
  ├─ 解析用户需求
  ├─ 拆解任务步骤
  ├─ 生成 session UUID
  └─ 通过 exec 调用 claude CLI

Claude Code CLI（执行层）
  ├─ 执行代码生成/修改
  ├─ 读写文件
  └─ 返回结果

真哥验收结果后交付用户
```

## 常见问题

**Q: `Session ID already in use`**
A: 同一 UUID 在不同命令中重复用了 `--session-id`，后续应该用 `--resume`

**Q: 多轮后文件没生成**
A: 大部分是权限弹窗问题，确认加 `--dangerously-skip-permissions`

**Q: 跨 exec session 续不上**
A: 已知 WSL 环境下跨进程 session 续接不稳定，解决方案是单次 exec 内完成多轮

**Q: timeout 设多少合适**
A: 简单任务 15s，复杂任务 20-25s，多文件生成建议 30s