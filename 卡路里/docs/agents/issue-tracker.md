# Issue tracker: 本地 Markdown

本仓库的 issues 和 specs(即 PRD)以 markdown 文件形式存放在 `.scratch/` 目录下。

## 约定

- 每个功能一个目录:`.scratch/<feature-slug>/`
- spec 文件为:`.scratch/<feature-slug>/spec.md`
- 实现类 issues 为每张票一个文件,路径为 `.scratch/<feature-slug>/issues/<NN>-<slug>.md`,从 `01` 开始编号 —— 不要把多张票合并成一个文件
- Triage 状态以 issue 文件顶部附近的 `Status:` 行记录(具体角色字符串见 `triage-labels.md`)
- 评论和对话历史追加到文件底部的 `## Comments` 标题下

## 当 skill 说"发布到 issue tracker"时

在 `.scratch/<feature-slug>/` 下新建一个文件(必要时创建该目录)。

## 当 skill 说"取回相关 ticket"时

读取被引用路径下的文件。用户通常会直接传路径或 issue 编号。

## Wayfinding 操作

供 `/wayfinder` 使用。**map(地图)** 是一个文件,每个 **child(子票)** 对应一个文件。

- **Map**:`.scratch/<effort>/map.md` —— 包含 Notes / Decisions-so-far / Fog 主体内容。
- **Child ticket**:`.scratch/<effort>/issues/NN-<slug>.md`,从 `01` 开始编号,正文中写明问题。用 `Type:` 行记录 ticket 类型(`research`/`prototype`/`grilling`/`task`);用 `Status:` 行记录 `claimed`/`resolved`。
- **Blocking**:文件顶部附近的 `Blocked by: NN, NN` 行。当所列的每个文件都为 `resolved` 时,ticket 即解除阻塞。
- **Frontier**:扫描 `.scratch/<effort>/issues/` 下处于 open、未阻塞、未 claimed 的文件;按编号最小的优先。
- **Claim**:开始任何工作前,先设置 `Status: claimed` 并保存。
- **Resolve**:在 `## Answer` 标题下追加答案,设置 `Status: resolved`,然后把上下文指针(gist + 链接)追加到 `map.md` 的 Decisions-so-far 中。
