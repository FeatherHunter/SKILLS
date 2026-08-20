# awesome-dsh-plugin-submit

把 DSH 插件收录到 **awesome-dsh-plugin** 官方策展注册表（https://awesome-dsh-plugin.com）的全流程技能。

## 一句话

一个 YAML 文件 + 一个 PR = 收录完成。README 由脚本生成，**禁止手工编辑**。

## 适用场景

- 让你的 DSH 插件出现在 https://awesome-dsh-plugin.com 的公开列表里
- 让 `dsh-market` / `dsh-plugin-manager` / `dsh-plugin-hub` 等市场插件能搜到并一键安装你的插件
- 维护已收录的条目（改描述 / 改分类 / 加截图 / 移除）

## 不适用

- 写插件代码本身（不在本技能范围内）
- 发布到 npm 官方源（请用 `npm-publish` 技能先发布）
- 非 DSH 插件 / 私有仓库 / 仅本地使用的插件

## 30 秒上手

把你本地的 DSH 插件包（已有 `dsh.bundle` 声明 + `cordis.patch.yml`，GitHub 仓库 ≥1 天 + ≥10 提交）告诉 AI：

> "**把我的插件 `<owner>/<repo>` 收录到 awesome-dsh-plugin**"

AI 会自动执行本技能 §流程 1-6：自检 → fork → 写 YAML → 重生成 README → commit → 开 PR。

## 关键文档

- [`SKILL.md`](./SKILL.md) — AI 主读本（触发词 / 流程 / 硬规则 / 坑位 / 自检）
- [`references/pitfalls.md`](./references/pitfalls.md) — 9 条高频坑位 + CI 报错速查表

## 实战案例（FeatherHunter/dsh-mattpocock-skills-deck · 2026-08-18 自检）

| 项 | 状态 | 说明 |
|---|---|---|
| `dsh.bundle` 声明 | ✓ | `dsh.bundle.patch: ./cordis.patch.yml` |
| `cordis.patch.yml` | ✓ | 位于 `package/cordis.patch.yml` |
| 真实代码 | ✓ | `lib/` 已有 |
| 仓库 ≥1 天 | ? | 需 gh CLI 查 `createdAt` |
| 提交数 ≥10 | ? | 需 gh CLI 查 |
| `dsh-plugin` topic | ? | 需到 GitHub 仓库 → About → Topics 加 |
| 描述准确 | ⚠ | 当前 `package.json` description 含"npm 标准安装"等"怎么装"内容 + "25 个技能"需 grep 验证 |
| 分类 | `skill` | 主因：核心是把 skills 注入 DSH |

**下一步推荐**：先用 `gh repo view` 查元数据 → 必要时打 `dsh-plugin` topic → 重写 description → 走 §流程 2-6 开 PR。

## 触发词示例

- "收录到 awesome-dsh-plugin"
- "提交插件到插件市场"
- "让插件进 awesome-dsh-plugin 列表"
- "生成 awesome-dsh-plugin 收录 PR"
- "dsh plugin 入 awesome 列表"

## License

MIT，与 `FeatherHunter/SKILLS` 仓库保持一致。