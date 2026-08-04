# 模板拆分原则(形态不兼容即独立 · 按形态拆分落地)

Status: accepted

2026-08-04 场景 21「改饮水目标」验收时发现:页面误渲染全部 5 项 slider(热量/蛋白/碳水/脂肪/饮水)。根因是**模板硬编码字段列表 + `water_only` 旁路布尔标记决定形态** —— 形态与场景的对应关系靠数据旁路维护,一处漏传即串扰全场景。随后 goal_config.html 被并行 session 反复覆盖(字段机制/上限改动被 checkout 回退),证明**共用模板无法支撑并行差异化开发**。用户拍板两项原则 + 直接落地拆分。

## 原则 1:模板数量 ≈ 形态数量,不是场景数量

- **模板的职责 = 呈现形态**(布局骨架 + 交互语义),不是场景。
- **同构**(DOM 骨架相同,差异 = 数值/文案/显隐)→ 共用模板,差异由数据表达。
- **异构**(骨架/交互语义不同,或模板内出现"if 场景A else 场景B"分支)→ **拆独立模板,不硬塞**。不嫌模板多,形态不兼容就是拆的充分理由。
- 触发信号(出现任一即拆或重构):
  1. 模板内出现按场景/模式分叉的逻辑分支
  2. 用旁路布尔标记(如 `water_only`)控制整体形态
  3. 无法用注入数据表达的场景差异
- 反例红线:446 场景 × 446 模板(维护爆炸、修复要改 N 份、风格漂移)—— 场景数量不是拆分单位,形态才是。

## 原则 2:激活字段由 render 端下发,模板零硬编码字段列表

- render 端下发 `fields`(激活字段 key 列表),模板只渲染收到的字段;缺失时回退全量(向后兼容 mock/旧数据)。
- 数值元数据(上限/步进/标签)是**模板单点权威**(FIELD_META 字典),Python 不复制数值,避免双源漂移。
- 形态判定(如"仅饮水")从 `ACTIVE_FIELDS` 推导,不依赖数据旁路布尔。

## 落地(2026-08-04 同日执行)

- **拆 2 套模板**:`templates/goal_config_nutrition.html`(定/改营养:5 字段 slider 联动 + BMR 提示)+ `templates/goal_config_water.html`(定/改饮水:单字段,无宏量联动/BMR,slider 左右留白对称 110/1fr/110)。
- `scripts/render_goal_config.py` 按 mode 选模板;`data['fields']` 仍下发(契约);旧 `templates/goal_config.html` 退役删除。
- 饮水上限 4000→6000(用户拍板,两模板统一);mini chart 参照系翻转「改前 vs 改后」(diff = 新−旧);数值行 nowrap 防换行。

## 案例

- 场景 21 改饮水目标:独立模板单字段,无旁路标记,串扰从架构上绝迹。
- 场景 1/6/19(定营养/定饮水/改营养):随模板拆分顺带回归(6000 上限/翻转 chart/nowrap),slider 语义(满项锁定/向左当前比例/归零锚定/1:1:1)复测一致。
- 后续新增场景若形态与现有模板异构(如新的图表交互),按原则 1 拆独立模板,而不是往旧模板塞分支。

## 相关文件

- `卡路里/templates/goal_config_nutrition.html` · `卡路里/templates/goal_config_water.html`
- `卡路里/scripts/render_goal_config.py`(按 mode 选模板 + fields 下发)
- 验证:`卡路里/.scratch/visual/verify_goal_split_templates.py` · `verify_goal_chart_nowrap.py`

## 参考

- ADR-0008(HELP 设计原则)同位置同风格;本原则适用于所有共用模板的后续开发(goal_progress / goal_weight / goal_recommend 等)。
