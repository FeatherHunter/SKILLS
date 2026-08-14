# npm-publish 技能

把本地包发布到 npm 官方源的**操作流程技能**——检查、打包预览、登录、发布、验证、版本迭代、撤回，一次跑通。

## 文件

| 文件 | 用途 |
|---|---|
| [SKILL.md](./SKILL.md) | 主契约：触发词表 + 发布流程（0-7 步）+ 8 条硬规则 + 软规则心法 |
| [references/pitfalls.md](./references/pitfalls.md) | 实测坑位表（镜像源/2FA/令牌泄露/版本冲突/72h 窗口） |
| [references/dsh-plugin-manifest.md](./references/dsh-plugin-manifest.md) | DSH 插件包的 package.json 骨架 + 浏览器 bundle 格式（附录） |

## 来历

2026-08-14 由 `dsh-opencode-tui-theme@1.0.0` 实盘发布沉淀：
https://www.npmjs.com/package/dsh-opencode-tui-theme

## 一句话心法

**发布 = 公开 + 几乎不可撤回；登录/发布永远走官方源；令牌像密码一样对待。**
