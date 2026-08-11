---
name: 技能互联
description: >
  跨技能数据契约层 Base Skill · Skill Link。
  让各技能通过 skilllink-read 命令对外暴露/读取数据（注册表 + 统一信封）。
  提供 skill_registry / check_public_contract 校验器 / 互联总览。
  任何技能开发数据联动（提供/消费）前必须先装本基础包（强制依赖）。
disable-model-invocation: true
---

# 技能互联（Skill Link）· Base Skill v0.1（骨架定稿）

> 基础设施型技能：系统加载时存在，不自动唤起、不在用户手动触发列表（对标 wayfinder）。
> 中文名：技能互联 · 英文名：Skill Link · 命令：`skilllink-read`
> 骨架定稿：2026-08-11 · #271 用户逐条拍板（目录结构 / 强制依赖 / 注册表形态 / 校验机制）

## 定位

跨技能数据契约层。与公共组件平级：

| Base | 职责 |
|---|---|
| 公共组件 | 渲染层（注入管线 + 控件库）—— HTML 长什么样 |
| **技能互联（本）** | 数据层（数据契约）—— 技能之间怎么拿数据 |

**目标**：卡路里 / 饼干记账 / 作息管家 / 居家管家 / 备忘录 / 私家大厨 6 技能全部打通（每技能既是提供方也是消费方）。

## 强制依赖（#271 拍板）

- **语义**：任何技能**开发数据联动（提供/消费）前，必须先装本基础包**。纯单机技能（无联动）不强制。
- **闸门**：`check_public_contract` 校验器进各技能 pytest——未装/未接入 = 测试红 = commit 被拒（硬约束，AI 不可能无视）。
- **发现机制（三层探测）**：
  1. 探测 Base 本身：`技能互联/` 目录 + `skilllink.py` + `skill_registry.yaml` 存在？缺失 → 红：「未安装技能互联，先装本基础包」
  2. 探测已接入技能：registry 列出的技能，`PUBLIC_DOMAINS` 注册表存在且符合契约？缺失 → 红
  3. 运行时（skilllink-read 被调用）：查未接入技能 → 信封 ok=false「未接入」→ AI 降级（契约 v1 §6）

## 核心概念

- **执行者 = AI**：用户复制 prompt → AI 执行；AI 读契约 → 调 skilllink-read → 理解/合并 → 注入 HTML
- **注册表**：每技能声明「我能提供什么」（域名称/中文名/一句话说明/字段列表）—— 技能侧只放 `PUBLIC_DOMAINS.py`
- **统一信封**：所有技能返回同一盒子（办成了/来自哪个技能/查的什么/查询情况/数据）
- **字段类型 4 种**：数字 / 日期 / 文字 / 自由文本（text，AI 读黑盒 + 用户确认）
- **命令**：`skilllink-read --skill <技能> --domain <域> --from <开始> --to <结束>`（--what 问能力）
- **命令真身住本 Base**：`skilllink.py`（公共 runner：参数解析 + 统一信封 + --what/--contract），各技能只填注册表，不重复实现

## 目录结构（#271 定稿）

```
技能互联/                    # Base Skill（与公共组件平级）
  SKILL.md                  # 本文件（Base 定义：定位 + 资产清单 + 接入步骤 + 强制依赖表述）
  README.md                 # 使用手册（接入步骤 + 校验器 + 总览）【待 #271 产出后建】
  CHANGELOG.md              # 版本变更记录（对齐公共组件）【待建】
  skilllink.py              # 命令真身（公共 runner）：参数解析 + 统一信封 + --what/--contract【待 #274 试点实现】
  skill_registry.yaml       # 技能名 → 路径 + 注册表模块（Base 侧单一真相源）【待建】
  scaffolds/
    PUBLIC_DOMAINS.py.template  # 模板脚手架：新技能接入时复制改名 + 填注册表【待 #274 试点建】
  templates/
    overview.html           # 互联总览 HELP（#276 落地，骨架先占位）【待 #276】
  docs/
    契约规范-v1.md           # 数据契约规范 v1（定稿 · 2026-08-11 · 用户逐条拍板）
  tests/
    test_skilllink.py       # 命令/信封守卫测试（temp_db 隔离约定）【待 #274 试点建】
```

> 注册表约定（#271 拍板）：`skill_registry.yaml` **只存技能名 → 路径 + 注册表模块**，不存 DB 路径——skilllink 查询数据时各技能自己 `find_db_path` 动态解析（尊重 `SKILLS_DB_PATH` 环境变量，测试天然隔离，绝不写死生产路径）。yaml 由新技能接入时手工登记，校验器双向检查（技能存在没登记 / 登记了没注册表 → 都红）。

## 接入步骤（新技能）

1. 复制 `scaffolds/PUBLIC_DOMAINS.py.template` 到 `<技能>/PUBLIC_DOMAINS.py`，填自己的注册表
2. 在 `skill_registry.yaml` 登记：技能名 → 路径 + 注册表模块
3. 校验器跑绿（`check_public_contract`，进 pytest）
4. 技能提供方就绪；消费方开发见各技能 ticket

## 开发状态（2026-08-11）

- ✅ #272 契约规范 v1 定稿（closed）
- ✅ #271 Base 骨架设计（closed · 本文件 = 骨架定稿）
- ⏳ #273 校验器（01/02 已闭 → **可认领**）
- ⏳ #274 作息管家试点（契约已闭 → **可认领**）
- ⏳ #275 组合表落库（frontier · 可认领）
- ⏳ #276 互联总览（阻塞 03/04）
- ⏳ #277-#282 六技能消费方开发（#272 已闭 → 解锁，逐个 grilling）

## 决策地图

wayfinder 决策地图 = GitHub #270（本技能 `.scratch/map-body.md` 为本地草稿镜像）。
