# AGENTS · awesome-dsh-plugin-submit

本技能的 Agent 协作入口。仓库级别约定见根 `AGENTS.md`。

## 文件清单

| 文件 | 角色 |
|---|---|
| `SKILL.md` | AI 主读本（触发词 / 流程 / 硬规则 / 坑位 / 自检 / 工程记录） |
| `references/pitfalls.md` | 9 条高频坑位 + CI 报错速查表 + 调试流程 |
| `README.md` | 人类阅读版入口（一句话 / 适用场景 / 触发词） |
| `AGENTS.md` | 本文件 |

## 与根仓库的边界

- 仓库 `AGENTS.md` 的 **DB 隔离红线**对本技能**不适用**（本技能无 DB 读写）
- 仓库 `AGENTS.md` 的 **「需要用户视觉确认」**对本技能**不适用**（纯流程技能，无 HTML 输出）
- 仓库 `AGENTS.md` 的 **Delivery fidelity / Execution framework** 默认遵守：小事用手段 1；跨会话 / 跨 PR 流程用手段 1-3

## commit 规范

按根仓库 `AGENTS.md` 提交规范（全中文、Tested-By 末行、不用英文前缀）：

```
[awesome-dsh-plugin-submit] <主题> · <细节>
Tested-By: exempt(无 fresh agent · 纯流程技能，无 HTML 镜像)
```

## 改动前 3 问

1. 影响哪些文件？→ `SKILL.md` / `references/pitfalls.md` / `README.md`
2. 有没有数据迁移？→ 无
3. 回滚方案？→ `git revert` 提交；YAML / md 文件不会破坏外部系统

## 边界声明

- 本技能**只负责 awesome-dsh-plugin 收录流程**，不写插件代码
- 不负责 npm 发布（用 `npm-publish` 技能）
- 不负责 DSH 插件安装问题排查（找各 DSH 插件自己的 README）
- 不维护 awesome-dsh-plugin.com 网站本身（这是维护者的事）

## 来源声明

本技能 2026-08-18 创建，基于：
- 官方 `https://github.com/awesome-dsh-plugin/awesome-dsh-plugin/blob/main/contributing.md` 全量阅读
- 官方数据源 `https://awesome-dsh-plugin.com/plugins.json`（1283 个插件 / 827 个独立作者）调研
- 用户本地插件 `FeatherHunter/dsh-mattpocock-skills-deck` 自检实证

引用条款时均保留中英双语（官方 `contributing.md` 本身就是中英对照）。