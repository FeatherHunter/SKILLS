# Issue tracker:本地 Markdown

本仓库的 issues 和 specs(你可能称之为 PRD)以 markdown 文件形式存于 `.scratch/` 目录。

## 约定

- 每个 feature 一个目录:`.scratch/<feature-slug>/`
- spec 文件:`.scratch/<feature-slug>/spec.md`
- 实施 issue 每条一个文件:`.scratch/<feature-slug>/issues/<NN>-<slug>.md`,从 `01` 开始编号——绝不合并成单个 tickets 文件
- triage 状态记录在每个 issue 文件顶部的 `Status:` 行(角色字符串见 `triage-labels.md`)
- 评论和对话历史追加到文件底部 `## Comments` 标题下

## 当 skill 说"发布到 issue tracker"

在 `.scratch/<feature-slug>/` 下新建文件(必要时创建目录)。

## 当 skill 说"拉取相关 ticket"

读取被引用路径的文件。用户通常直接传路径或 issue 编号。

## 寻路操作(wayfinding)

供 `/wayfinder` 使用。**map** 是一个文件,对应每个 ticket 一个 **child** 文件。

- **Map**:`.scratch/<effort>/map.md` — Notes / Decisions-so-far / Fog 正文
- **Child ticket**:`.scratch/<effort>/issues/NN-<slug>.md`,从 `01` 编号,正文写问题。`Type:` 行记录 ticket 类型(`research`/`prototype`/`grilling`/`task`);`Status:` 行记录 `claimed`/`resolved`
- **阻塞**:`Blocked by: NN, NN` 行靠近顶部。当它列出的每个文件都 `resolved` 时,ticket 解除阻塞
- **Frontier**:扫描 `.scratch/<effort>/issues/`,找开放、未阻塞、未认领的文件;编号最小者胜
- **认领**:开工前先设 `Status: claimed` 并保存
- **解决**:在 `## Answer` 标题下追加答案,设 `Status: resolved`,然后把上下文指针(gist + 链接)追加到 map.md 的 Decisions-so-far
