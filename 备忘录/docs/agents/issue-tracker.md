# 问题追踪：本地 Markdown

本仓库的问题（issue）与规格（spec，即 PRD）以 Markdown 文件形式存放在 `.scratch/` 目录下。

## 约定

- 每个功能一个目录：`.scratch/<功能名>/`
- 规格文件为：`.scratch/<功能名>/spec.md`
- 实施问题每个问题一个文件，位于 `.scratch/<功能名>/issues/<NN>-<slug>.md`，从 `01` 开始编号 —— 不要合并成单个 tickets 文件
- Triage 状态记录在文件顶部附近的 `Status:` 行（角色字符串见 `triage-labels.md`）
- 评论与对话历史追加到文件底部 `## Comments` 标题之下

## 当技能说「发布到问题追踪器」时

在 `.scratch/<功能名>/` 下新建一个文件（如目录不存在则创建）。

## 当技能说「获取相关 ticket」时

读取被引用路径的文件。用户通常会直接给出路径或问题编号。

## Wayfinding 操作

供 `/wayfinder` 使用。**map（地图）** 是一个文件，每个 ticket 对应一个子文件。

- **Map**：`.scratch/<功能名>/map.md` —— 包含 Notes / Decisions-so-far / Fog 正文。
- **子 ticket**：`.scratch/<功能名>/issues/NN-<slug>.md`，从 `01` 起编号，正文写明问题。`Type:` 行记录 ticket 类型（`research`/`prototype`/`grilling`/`task`）；`Status:` 行记录 `claimed`/`resolved`。
- **阻塞关系**：文件顶部附近的 `Blocked by: NN, NN` 行。当列出的每个文件都为 `resolved` 时，该 ticket 即被解除阻塞。
- **Frontier（前沿查询）**：扫描 `.scratch/<功能名>/issues/` 下所有处于 open、未阻塞、未 claimed 的文件；编号最小者胜出。
- **Claim（认领）**：设 `Status: claimed` 并保存，之后再开始任何工作。
- **Resolve（解决）**：在 `## Answer` 标题下追加答案，设 `Status: resolved`，然后向 `map.md` 的 Decisions-so-far 追加一个上下文指针（gist + 链接）。
