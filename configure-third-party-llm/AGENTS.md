# AGENTS · configure-third-party-llm

本技能的 Agent 协作入口。仓库级别约定见 `D:\2Study\StudyNotes\SKILLS\AGENTS.md` 与对应 DSH 项目根的 AGENTS.md（如有）。

## 文件清单

| 文件 | 角色 |
|---|---|
| `SKILL.md` | AI 主读本（触发词 / 协议分支 / 配置模板 / 流程 / 硬规则 / 坑位 / 自检） |
| `README.md` | 人类阅读版入口（一句话 / 适用场景 / 30 秒上手） |
| `AGENTS.md` | 本文件 |

## 部署形态

- 真实源在 `D:\2Study\StudyNotes\SKILLS\configure-third-party-llm\`
- DSH 通过 **目录 junction**（`mklink /J`）把它挂到 `C:\Users\辰辰洋洋\.dsh\skills\configure-third-party-llm`
  - DSH 的 `dsh-skill-filesystem` provider rank 400 扫 `<dshHome>/skills`
  - `watchFollowSymlinks: true` → junction 跟随
- 修改 SKILL.md 不必手工重链；junction 一旦建好就是同一个 inode

junction 建立命令（`mklink /J` 跨盘可、无需管理员）：

```powershell
# 删旧链（如存在）
cmd /c rmdir "C:\Users\辰辰洋洋\.dsh\skills\configure-third-party-llm" 2>nul
# 建新链
cmd /c mklink /J "C:\Users\辰辰洋洋\.dsh\skills\configure-third-party-llm" "D:\2Study\StudyNotes\SKILLS\configure-third-party-llm"
```

## 与 DSH 项目根的边界

- DSH 项目本身（`C:\Users\辰辰洋洋\AppData\Roaming\DSH Desktop\agent\`）的 AGENTS.md **对本技能不直接相关**——本技能改的是用户态的 `~/.dsh/settings.yaml`，不动 DSH 平台代码
- 平台代码的 schema / catalog / provider 配置如果升级，DSH 重启 DSH 进程即可，不需要重链本技能

## 边界声明

- 本技能**只管 settings.yaml 中 `llm-pi-ai.providers.<route>` 这一个段**
- 不管 `~/.dsh/credentials.yaml`（DSH 的 key 存储；本技能只写 env var 名）
- 不管 `agent-default-model`（用户后续人工选）
- 不管 DSH 内置 catalog 的 `minimax` / `minimax-cn` / `openai` / `anthropic` 等（**已经存在的工作路径不要在本技能里再写一遍**）
- 不管 WSL Hermes / OpenCode 等其它 agent 系统的模型配置

## 改动前 3 问

1. 影响哪个文件？→ 只 `SKILL.md`（AGENTS.md / README.md 偶尔调整）
2. 有没有数据迁移？→ 无
3. 回滚方案？→ `rmdir` junction + 删除 `D:\2Study\StudyNotes\SKILLS\configure-third-party-llm\`（也支持 git revert，如果源目录在 git 仓里）

## 来源声明

本技能 2026-08-21 创建，基于：

- DSH 实测调查：`@deepseek-ai/dsh-llm-pi-ai` (v0.1.0-rc.7) 的 schema（`catalog.d.ts` / `config.d.ts`） + `dsh-settings-file` 行为
- pi-ai v0.x 的 wire 协议源码（`@earendil-works/pi-ai/dist/api/openai-completions.js` 第 560-640 行）
- 用户实战案例：`xianyu-minimax` 路由（OpenAI-completions 协议），通过本技能首次完整跑通
- 既有的 settings.yaml 状态（C:\Users\辰辰洋洋\.dsh\settings.yaml）

## commit 规范

源目录 `D:\2Study\StudyNotes\SKILLS\configure-third-party-llm\` 目前不在 git 仓（用户 StudyNotes 主仓是另一回事）。如未来加入 git，提交规范参考根仓 AGENTS.md：
- 中文主题
- Tested-By: exempt(纯模板技能，无 fresh agent)
