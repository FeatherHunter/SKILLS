# 依赖链审计报告

> 审计时间：2026-05-23
> 审计范围：view.md、shopping.md、add.md、SKILL.md 中所有外部依赖引用
> 审计环境：Windows 11 + Git Bash

---

## 外部技能依赖

| 技能 | 文档中引用的路径 | 存在？ | 实际可用路径 | 影响功能 |
|------|-----------------|--------|-------------|---------|
| Taste Skill | `~/.openclaw/skills/taste-skill/SKILL.md` (view.md:44) | ❌ | `D:/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md` | view.md - 查看食谱/做菜模式HTML生成 |
| Taste Skill | `/mnt/d/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md` (view.md:332) | ❌ | 同上 | view.md - 参考部分 |
| UI/UX Pro Max | `~/.openclaw/skills/ui-ux-pro-max/SKILL.md` (view.md:49) | ❌ | `D:/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md` | view.md - 查看食谱/做菜模式HTML生成 |
| UI/UX Pro Max | `/mnt/d/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md` (view.md:333) | ❌ | 同上 | view.md - 参考部分 |

**结论**：两个外部技能的实际文件均存在于Windows路径下，但文档中引用的4个路径全部无法访问：
- `~/.openclaw/skills/...` 格式：Windows下`~`解析为`/c/Users/辰辰...`，该目录不存在
- `/mnt/d/...` 格式：WSL路径在Git Bash中不可用

---

## 文件存储路径

| 路径 | 存在？ | 影响功能 | 出现位置 |
|------|--------|---------|---------|
| `/home/feather/.openclaw/media/qqbot/` | ❌ | view.md - 查看食谱HTML输出、做菜模式HTML输出 | view.md:106, 267, 269 |
| `/home/feather/.openclaw/media/qqbot/shopping/` | ❌ | shopping.md - 采购清单HTML输出 | shopping.md:135 |

**结论**：两个文件存储路径均使用Linux home目录格式，在Windows环境下不存在。这些路径是QQBot文件发送的存储位置，路径不可达将导致HTML文件无法保存，进而无法通过QQBot发送给用户。

---

## 脚本依赖

### 数据库配置

| 脚本 | 存在？ | 影响功能 |
|------|--------|---------|
| `scripts/db_config.py` | ✅ | SKILL.md - 数据库并发支持，所有manager脚本的底层依赖 |

### Manager脚本（view.md引用）

| 脚本 | 存在？ | 影响功能 |
|------|--------|---------|
| `scripts/recipe_manager.py` | ✅ | view.md - 查看食谱详情 |
| `scripts/category_manager.py` | ✅ | view.md - 分类查询 |
| `scripts/season_manager.py` | ✅ | view.md - 季节查询 |
| `scripts/cooking_method_manager.py` | ✅ | view.md - 烹饪方式查询 |
| `scripts/flavor_manager.py` | ✅ | view.md - 口味查询 |
| `scripts/diet_tag_manager.py` | ✅ | view.md - 饮食标签查询 |
| `scripts/meal_type_manager.py` | ✅ | view.md - 餐次查询 |
| `scripts/cookware_manager.py` | ✅ | view.md - 炊具查询 |
| `scripts/ingredient_manager.py` | ✅ | view.md - 食材查询 |
| `scripts/step_ingredient_manager.py` | ✅ | view.md - 步骤食材关联查询 |
| `scripts/step_manager.py` | ✅ | view.md - 步骤查询 |
| `scripts/technique_manager.py` | ✅ | view.md - 技法查询 |
| `scripts/tip_manager.py` | ✅ | view.md - 小贴士查询 |
| `scripts/history_manager.py` | ✅ | view.md - 历史查询 |
| `scripts/background_manager.py` | ✅ | view.md - 背景知识查询 |
| `scripts/relation_manager.py` | ✅ | view.md - 派生关系查询 |
| `scripts/nutrition_manager.py` | ✅ | view.md - 营养信息查询 |

### Manager脚本（shopping.md引用）

| 脚本 | 存在？ | 影响功能 |
|------|--------|---------|
| `scripts/shopping_manager.py` | ✅ | shopping.md - 采购清单生成 |

### Manager脚本（add.md引用）

| 脚本 | 存在？ | 影响功能 |
|------|--------|---------|
| `scripts/recipe_manager.py` | ✅ | add.md - 食谱创建/冲突处理 |
| `scripts/category_manager.py` | ✅ | add.md - 分类录入 |
| `scripts/ingredient_manager.py` | ✅ | add.md - 食材录入 |
| `scripts/step_manager.py` | ✅ | add.md - 步骤录入 |
| `scripts/step_ingredient_manager.py` | ✅ | add.md - 步骤食材关联录入 |
| `scripts/technique_manager.py` | ✅ | add.md - 技法录入 |
| `scripts/tip_manager.py` | ✅ | add.md - 小贴士录入 |
| `scripts/background_manager.py` | ✅ | add.md - 背景知识录入 |
| `scripts/cookware_manager.py` | ✅ | add.md - 炊具录入 |
| `scripts/nutrition_manager.py` | ✅ | add.md - 营养信息录入 |
| `scripts/recipe_import.py` | ✅ | add.md / SKILL.md - JSON文件导入 |

**结论**：所有脚本依赖均存在，共20个独立脚本文件全部验证通过。scripts目录下还有`init_db.py`和`recipe_manager.py.bak`两个额外文件未被文档引用。

---

## 发现的故障

### [P0] 文件存储路径不可达 — 阻断QQBot文件发送

**影响范围**：view.md（查看食谱、做菜模式）、shopping.md（采购清单）
**严重程度**：P0 - 核心功能完全不可用
**描述**：
- `/home/feather/.openclaw/media/qqbot/` 和 `/home/feather/.openclaw/media/qqbot/shopping/` 在Windows环境下不存在
- 这两个路径是HTML文件的唯一存储位置
- 路径不可达 = HTML无法保存 = QQBot无法发送文件给用户
- 影响view.md的两个核心功能（查看食谱、做菜模式）和shopping.md的采购清单功能

**修复建议**：
将路径改为Windows兼容格式，如 `D:/2Study/StudyNotes/SKILLS/私家大厨/output/qqbot/` 和 `D:/2Study/StudyNotes/SKILLS/私家大厨/output/qqbot/shopping/`，或使用环境变量/配置文件统一管理。

---

### [P1] 外部技能路径全部不可达 — HTML设计质量降级

**影响范围**：view.md（查看食谱、做菜模式）
**严重程度**：P1 - 功能可用但质量严重降级
**描述**：
- Taste Skill 和 UI/UX Pro Max 的4个引用路径全部无法访问
- view.md 明确声明"违反强制要求，输出视为不合格"
- 两个技能实际文件存在于 `D:/2Study/StudyNotes/SKILLS/` 下，但路径格式错误
- 如果AI无法加载这些技能文件，生成的HTML将缺少设计规范指导

**修复建议**：
将view.md中的路径引用统一改为Windows格式：
- Taste Skill: `D:/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md`
- UI/UX Pro Max: `D:/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md`

---

### [P2] 路径格式不统一 — 混用Linux/WSL/Windows格式

**影响范围**：所有功能文件
**严重程度**：P2 - 维护隐患
**描述**：
文档中存在三种路径格式混用：
1. `~/.openclaw/skills/...` — Linux home目录格式
2. `/mnt/d/2Study/...` — WSL路径格式
3. `D:/2Study/...` — Windows路径格式（仅在脚本命令中使用）

当前运行环境为Windows，只有第3种格式可正常工作。前两种格式在Git Bash、CMD、PowerShell中均无法直接解析。

**修复建议**：
统一使用Windows路径格式，或引入配置变量（如 `%SKILL_HOME%`）实现跨平台兼容。

---

## 审计总结

| 类别 | 总数 | 存在 | 缺失 | 存在率 |
|------|------|------|------|--------|
| 外部技能路径 | 4 | 0 | 4 | 0% |
| 文件存储路径 | 2 | 0 | 2 | 0% |
| 脚本依赖 | 20 | 20 | 0 | 100% |

**关键发现**：
1. 脚本层面完全健康，20个脚本全部存在且可访问
2. 路径层面全部故障，6个外部路径无一可达
3. 根因：文档编写时使用了Linux/WSL路径格式，未适配Windows运行环境
4. 外部技能的实际文件存在，仅需修正路径引用即可恢复
