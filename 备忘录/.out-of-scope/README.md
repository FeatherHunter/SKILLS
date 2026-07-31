# .out-of-scope/

`/triage` 拒绝 enhancement 请求时把"为什么拒绝"写入本目录下的 markdown 文件，供未来 `/triage` 在做"prior rejection"检查时回看。

## 写入规则

- **触发条件**：某个 GitHub issue 被 `/triage` 判定为 `wontfix`，且分类为 `enhancement`（非 `bug` 且非"已实现"）。
- **写入位置**：本目录下 `<slug>.md`，slug 取 issue 标题去除 `[备忘录]` 前缀后的归一化形式（小写、空格转 `-`、去除标点）。
- **必填 frontmatter**：

  ```yaml
  ---
  Title: <原 issue 标题>
  Issue: <#编号>
  Skill: 备忘录
  Date: <YYYY-MM-DD>
  ---
  ```

- **正文必含**：`## 拒绝理由` 与 `## 参考证据` 两个二级标题。

## 不写 .out-of-scope 的情形

- **bug 被拒绝**：只在 GitHub issue 评论里说明，**不**写到本目录。
- **enhancement 已实现**：直接指向代码位置，**不**写到本目录。
- **wontfix enhancement 但理由可复用**：写入并 link 到 issue 评论。

## 历史兼容性

本目录在仓库初始化时为空。`/triage` 首次拒绝 enhancement 时如发现目录不存在，会自动 `mkdir -p`。

## 与 GitHub issue 的关系

每次写入都必须在对应 GitHub issue 评论里留链接，例如：

> 已记录拒绝理由到 `备忘录/.out-of-scope/<slug>.md`，未来同类请求将引用此条。