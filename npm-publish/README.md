# npm-publish 技能

把本地目录发布到 npm 官方源（`https://registry.npmjs.org`）的**通用操作流程技能**——检查、打包预览、登录、带 2FA 发布、验证、版本迭代、撤回，一次跑通。零硬编码，开箱即用于任何 npm 包（不限框架）。

## 文件

| 文件 | 用途 |
|---|---|
| [SKILL.md](./SKILL.md) | 主契约：触发词表 + 发布流程（0-7 步）+ 硬规则 + 坑位速查 |
| [references/pitfalls.md](./references/pitfalls.md) | 通用坑位表（镜像源/2FA/令牌泄露/版本冲突/72h 窗口/非交互 EOTP） |
| [references/package-checklist.md](./references/package-checklist.md) | 通用 `package.json` 发布清单与 `files` 白名单建议（可选附录） |

## 适用人群

- 第一次发 npm 包的个人开发者
- 需要 AI 助手代为检查但由人完成 2FA 的发布流程
- 任何框架的 JS/TS 包（框架特定 manifest 字段见附录说明）

## 一句话心法

**发布 = 公开 + 几乎不可撤回；登录/发布永远走官方源；令牌像密码一样对待。**

## 快速开始

```bash
# 1. 查占用与登录态
npm view <包名> --registry=https://registry.npmjs.org
npm whoami --registry=https://registry.npmjs.org

# 2. 预览包内容
npm pack --dry-run

# 3. 登录（推荐网页授权）
npm login --auth-type=web --registry=https://registry.npmjs.org

# 4. 发布（需在交互终端完成 2FA 网页审批）
npm publish --registry=https://registry.npmjs.org

# 5. 验证
npm view <包名> version --registry=https://registry.npmjs.org --prefer-online
```
