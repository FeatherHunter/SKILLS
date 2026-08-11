---
name: 技能互联
description: >
  跨技能数据契约层 Base Skill · Skill Link。
  让各技能通过 skilllink-read 命令对外暴露/读取数据（注册表 + 统一信封）。
  提供 skill_registry / check_public_contract 校验器 / 互联总览。
  任何技能开发联动功能时必读本技能（基础设施，不直接对用户开放）。
disable-model-invocation: true
---

# 技能互联（Skill Link）· Base Skill

> 基础设施型技能：系统加载时存在，不自动唤起、不在用户手动触发列表（对标 wayfinder）。
> 中文名：技能互联 · 英文名：Skill Link · 命令：`skilllink-read`

## 定位

跨技能数据契约层。与公共组件平级：

| Base | 职责 |
|---|---|
| 公共组件 | 渲染层（注入管线 + 控件库）—— HTML 长什么样 |
| **技能互联（本）** | 数据层（数据契约）—— 技能之间怎么拿数据 |

**目标**：卡路里 / 饼干记账 / 作息管家 / 居家管家 / 备忘录 / 私家大厨 6 技能全部打通（每技能既是提供方也是消费方）。

## 核心概念

- **执行者 = AI**：用户复制 prompt → AI 执行；AI 读契约 → 调 skilllink-read → 理解/合并 → 注入 HTML
- **注册表**：每技能声明「我能提供什么」（域名称/中文名/一句话说明/字段列表）
- **统一信封**：所有技能返回同一盒子（办成了/来自哪个技能/查的什么/查询情况/数据）
- **字段类型 4 种**：数字 / 日期 / 文字 / 自由文本（text，AI 读黑盒 + 用户确认）
- **命令**：`skilllink-read --skill <技能> --domain <域> --from <开始> --to <结束>`（--what 问能力）
- **命令真身住本 Base**：各技能只放 PUBLIC_DOMAINS 注册表，不重复实现

## 资产

- `docs/契约规范-v1.md` — 数据契约规范 v1（定稿 · 2026-08-11 · 用户逐条拍板）
- `skilllink.py` — 命令实现（待 #271 开发）
- `skill_registry.yaml` — 技能名 → 路径 + DB 路径（待 #271）
- `check_public_contract.py` — 校验器（待 #273）

## 开发状态（2026-08-11）

- ✅ #272 契约规范 v1 定稿（closed）
- ⏳ #271 Base 骨架设计（frontier · 可认领）
- ⏳ #273 校验器（阻塞 01）
- ⏳ #274 作息管家试点（契约已闭 → 可认领）
- ⏳ #275 组合表落库（frontier · 可认领）
- ⏳ #276 互联总览（阻塞 01/03/04）
- ⏳ #277-#282 六技能消费方开发（阻塞 #272 → 已解锁，逐个 grilling）

## 决策地图

wayfinder 决策地图 = GitHub #270（本技能 `.scratch/map-body.md` 为本地草稿镜像）。
