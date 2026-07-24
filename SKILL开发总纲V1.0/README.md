# SKILL 开发总纲 V1.0 · 人类阅读版

> 这是 SKILLS 仓库的**元规范**。开发新 Skill 或改造现有 Skill 之前必读。

## 何时用

- ✅ 写新 Skill 之前
- ✅ 改造 / 重构现有 Skill 之前
- ✅ 评审他人 Skill 改动
- ❌ 写单条脚本 / CRUD / 数据采集(这些不需要 Skill 化)

## 文件清单

| 文件 | 一句话 | 何时读 |
|---|---|---|
| [01-第一性原理.md](./01-第一性原理.md) | Skill 是什么 + 为什么分层 | 第一次接触 |
| [02-5层骨架.md](./02-5层骨架.md) | 5 层结构 + 6 特性 + 8 反模式 + 自检 | **任何 Skill 设计的起点** |
| [03-触发词设计v2.md](./03-触发词设计v2.md) | v2 矩阵触发词方案(4 元组 + 8 ≤ N) | 设计 SKILL.md 触发词 |
| [04-可视化与注入v2.md](./04-可视化与注入v2.md) | HTML 模板 + 注入 + 10 原则 + 单工铁律 | 设计 / 改造 HTML 模板 |
| [05-工程仪式.md](./05-工程仪式.md) | 改动 3 问 + 自检 + hooks | 动手前最后一道防线 |

## 3 个可加载资产(总纲 v2 的关键)

| 资产 | 何时用 |
|---|---|
| [_assets/style.css](./_assets/style.css) | HTML 模板设计令牌(Apple 风) |
| [_assets/injector.py](./_assets/injector.py) | 占位符注入函数 |
| [_assets/template_skeleton.html](./_assets/template_skeleton.html) | 4 段式骨架 + 5 状态 |

## 5 个不可违背的钩子

见 [SKILL.md](./SKILL.md) 底部。

## 视觉版

[SKILL开发总纲V1.0.html](./SKILL开发总纲V1.0.html) — Apple 风可视化镜像,可在浏览器翻阅。
