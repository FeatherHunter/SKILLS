# 01 — 删除架构图.html + §07 死链 + HTML "6/8 通过"规则

**What to build:** 清除总纲里 3 类"不该存在的内容":(1) 架构图.html(孤儿文件 + 自身 3 处不一致——钩子数三处不一致 / 目录缩进错位 / 文件口径不一致)(2) §07 末尾两个死链(docs/superpowers/specs/ 和 plans/ 指向不存在的目录)(3) HTML 镜像的"6/8 通过才能动手"规则(无作者意图背书的污染,只存在于 HTML,.md 完全没有)。删除后 §07 末尾加声明"本章为 HELP 契约的唯一权威,不再引用外部设计稿"。这一步把"凭空冒出来的内容"全部清零,为后续计数修正扫清地基。

**Blocked by:** None — 可立即开始

**Status:** ready-for-agent

- [ ] git rm 架构图.html(文件不再存在于目录)
- [ ] grep "6/8 通过" 在所有文件 = 0 结果
- [ ] grep "docs/superpowers/specs" 在 §07 = 0 结果
- [ ] grep "docs/superpowers/plans" 在 §07 = 0 结果
- [ ] §07 末尾含"本章为 HELP 契约的唯一权威,不再引用外部设计稿"
