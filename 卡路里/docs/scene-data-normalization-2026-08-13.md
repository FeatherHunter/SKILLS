# scene_data 归一化记录(#316 · 2026-08-13)

> 归属: 卡路里 · Base 重构 task ④(#316, parent #260)
> 决策: `_triggers.py` 唯一权威(运行时 SoT · #291 grilling Q4) · 开发期 JSON 转只读归档(不物理删除)

## 结果口径

| 项 | 数值 |
|---|---|
| `_triggers.py` 总数 | 436(新 13 字段 413 + legacy 23) |
| `.scratch/scene_data/*.json` 总数 | 449(归档, 不再消费) |
| 双向缺口 | JSON 独有 **36**(全 11-技能协同) · `_triggers` 独有 **23**(查榜 13 / 复盘 9 / 有备注 1) |
| HELP 渲染 | 10 分类 · 436 场景(Base help_template · scene-data 契约 v1) |
| 文件契约 | `calorie_html/卡路里_HELP_<TS>.html` + 根镜像 `卡路里.html`(保留) |

## 处置明细(用户拍板 2026-08-13)

### A. JSON 独有 36 条 = 全部 11-技能协同类 → 不迁入
- 设计稿已备(11-技能协同.json)、prompt 未逐条确认、运行时零同步、功能实现属 [#270 技能互联](https://github.com/FeatherHunter/SKILLS/issues/270) 消费方票范畴(在途 open)
- 处置: 不迁入运行时; HELP 从 11 分类变 10 分类; 36 条留在归档 JSON, 待 #270 推进时再入运行时

### B. `_triggers` 独有 23 条(v2 时代 legacy) → 全部保留
- 查榜类 13: 查高热量榜/查低热量榜/查频繁吃榜/查高碳水榜/查高蛋白榜/查营养结构(6 条与 v1.0「看榜」重复, 保留旧词以维持既有触发词兼容)+ 查健康报告/查卡路里数据/查热量缺口/查热量趋势/查运动分布/查运动贡献/查食物排行(7 条无 v1.0 设计对应, 有真实模板功能)
- 复盘类 9: 复盘/今日复盘/本周复盘/本月复盘/本年复盘/复盘日期范围/开启定时复盘/关闭定时复盘/查定时复盘
- 看「有备注」的饮食记录 1
- 处置: 全部保留, 转换层归 分析/既有唤醒词(复盘 9 + 查榜 13)+ 饮食/既有唤醒词(1)

### C. 数字口径修正
- 票面预盘点「JSON 独有 35 + _triggers 独有 24」→ 实测 **36 + 23**(核对脚本按 (wake_word, key) 合并键逐条核算)

## 联动改造(归一化必要连带 · 偏离记录)

| 文件 | 改动 |
|---|---|
| `scripts/render_help_center.py` | v4.0 重写: 转换层 + Base help_template 注入; `--dev/--merged` 模式退役(JSON 已归档), 保留 `--output/--no-mirror` |
| `templates/help_center.html` | 退役删除(自研 HELP 模板, 证据链在 git 历史) |
| `scripts/render_exercise_review_html.py` | `load_scene_prompt` 改读 `_triggers.py`(原读 05-健身计划.json) |
| `scripts/check_prompt_soak.py` | payload 解析适配 help-data 契约(groups→subgroups→scenes.prompt_template) |
| `scripts/check_scene_data.py` | 角色降级为归档校验器(docstring 标注) |
| `SKILL.md` §完整 HTML 模板清单 | help_center.html 行更新为 Base 参数化 HELP 描述 |
| `AGENTS.md` SoT 链 | 更新为 `_triggers.py` → 转换层 → Base help_template → 卡路里.html |

## 验收口径(#316)

- 守卫测试全绿(门禁 A): 转换层契约校验 / 场景数零丢失(436) / 技能协同 36 不在 / 渲染产物占位符 0 残留 + Base 资产注入 / 三副本契约(时间戳 + 根镜像)
- 双端人工验收(门禁 B · 用户是唯一判官): 375/1280 视口 · 复制 prompt 与定稿逐字一致
- 偏离记录三问随闭环评论
