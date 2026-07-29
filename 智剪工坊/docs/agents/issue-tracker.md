# Issue 跟踪:本地 Markdown

本仓库的 Issue 与 spec(你可能称之为 PRD)以 markdown 文件形式存放在 `.scratch/` 下。

## 约定

- 每个功能一个目录:`.scratch/<功能名-slug>/`
- spec 文件为 `.scratch/<功能名-slug>/spec.md`
- 实现类 Issue 每张工单一文件,放在 `.scratch/<功能名-slug>/issues/<NN>-<slug>.md`,从 `01` 开始编号 —— 不要把多张工单合并到一个文件
- Triage 状态以文件顶部附近的 `Status:` 行记录(角色字符串见 `triage-labels.md`)
- 评论与对话历史追加到文件底部,置于 `## Comments` 标题之下

## 当技能要求「发布到 issue 跟踪」时

在 `.scratch/<功能名-slug>/` 下新建文件(如目录不存在则创建)。

## 当技能要求「获取相关工单」时

读取所引用路径的文件。用户通常会直接传入路径或 issue 编号。

## Wayfinder 操作

供 `/wayfinder` 使用。**map(地图)** 是一个文件,每个 **child(子工单)** 各占一文件。

- **Map**:`.scratch/<effort>/map.md` —— 包含 Notes / Decisions-so-far / Fog 主体。
- **Child 工单**:`.scratch/<effort>/issues/NN-<slug>.md`,从 `01` 开始编号,正文中写明问题。用 `Type:` 行记录工单类型(`research`/`prototype`/`grilling`/`task`);用 `Status:` 行记录 `claimed`/`resolved`。
- **阻塞**:文件顶部附近的 `Blocked by: NN, NN` 行。当它列出的每个文件都为 `resolved` 时,该工单即解除阻塞。
- **Frontier**:扫描 `.scratch/<effort>/issues/`,找出处于 open、未阻塞、未认领状态的文件;编号最小者优先。
- **认领(Claim)**:开始任何工作前,先置 `Status: claimed` 并保存。
- **解决(Resolve)**:在 `## Answer` 标题下追加答案,置 `Status: resolved`,然后把上下文指针(gist + 链接)追加到 `map.md` 的 Decisions-so-far 中。
