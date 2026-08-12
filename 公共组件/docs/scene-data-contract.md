# 统一 scene_data 契约 v1

> 归属：`公共组件/` · Base Skill 资产
> 来源：#289 落地 · 对齐 V4.16 原型（用户 2026-08-12 认可）+ help-template-contract §2/§3
> 定位：**Help HTML 对外参数定死 = 本契约。** 公共组件不翻译任何技能数据；技能在重构自己的 view 时主动对齐本契约（用户拍板核心思想 2026-08-12）。

## 0. 一句话

技能侧把场景数据重构为本契约形态 → Base `help_template.html` 渲染出 HELP 页。技能数据文件**可以动**（重构对齐契约是技能重构优化票的任务）；Base 侧零翻译、零适配。

## 1. 顶层结构

```json
{
  "skill_name": "作息管家",
  "title": "能力速查台",
  "subtitle": "一句话说明（可选）",
  "meta_blocks": [],
  "groups": []
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `skill_name` | string | ✅ | 技能中文名 · 页面标题/文件名 |
| `title` | string | ✅ | 页面大标题（如 能力速查台） |
| `subtitle` | string | 可选 | 副标题/一句话说明 |
| `meta_blocks` | array | 可选 | 技能特有元信息透传块（见 §4） |
| `groups` | array | ✅ | 2 级分组（见 §2） |

## 2. groups —— 2 级分组（category → subfunction）

统一为 **2 级分组**：一级 = 分组 Tab/折叠区（category），二级 = 子功能折叠组（subfunction），三级内容 = 场景卡片。

```json
{
  "id": "record",
  "icon": "✍️",
  "label": "记作息",
  "subgroups": [
    {
      "id": "record_single",
      "label": "单条记录",
      "scenes": []
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `groups[].id` | string | ✅ | 分组唯一标识（英文语义化） |
| `groups[].icon` | string | 可选 | 一级分组图标（emoji，显示在 Tab） |
| `groups[].label` | string | ✅ | 一级分组展示名 |
| `groups[].subgroups[].id` | string | ✅ | 二级分组唯一标识 |
| `groups[].subgroups[].label` | string | ✅ | 二级分组展示名（折叠组标题） |
| `groups[].subgroups[].scenes` | array | ✅ | 场景卡片（见 §3） |

## 3. scenes —— 场景卡片

```json
{
  "id": "record_add_single",
  "title": "添加单条作息记录",
  "wake_word": "#0 记作息",
  "type": "采集",
  "status": "",
  "prompt_template": "请帮我记一条作息:今天 14:00-15:00 写了 AI 调优代码",
  "editable_fields": []
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | ✅ | 场景唯一标识（对齐源数据 scenario_id/id/key） |
| `title` | string | ✅ | 场景标题（卡片名） |
| `wake_word` | string | ✅ | 唤醒词（卡片 chip 展示） |
| `type` | string | 可选 | 场景类型徽章（采集/查看/校验/回执…） |
| `status` | string | ✅ | `''` 可用 / `【待开发】` 禁用（禁用 = 醒目标注 + 复制按钮仍可点） |
| `prompt_template` | string | ✅ | **复制 prompt 全文，与技能 scene_data 定稿零差异**（#123 契约） |
| `editable_fields` | array | 可选 | 参数化表单字段（见 §5） |

## 4. meta_blocks —— 技能特有元信息透传

技能 HELP 除场景列表外的大量技能特有内容（大厨 prompt_rules/methodology/status_legend、备忘录 dependencies、卡路里 AI 验证协议）——**Base 原样透传**，不进通用 scenes 结构。

```json
[
  { "id": "usage_rules", "title": "使用须知", "html": "<p>…</p>" },
  { "id": "ai_verify", "title": "AI 验证协议", "html": "<p>…</p>" }
]
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | ✅ | 块唯一标识 |
| `title` | string | ✅ | 块标题（渲染为折叠组/章节头） |
| `html` | string | ✅ | **技能方提供的 HTML 原文**，Base 原样透传渲染（含转义需求技能方自理；禁止 `</script>`/`</style>` 字样混入资产注释） |

渲染位置：页面顶部标题区下方（初始化横幅之后、分组导航之前），按数组顺序纵向排列。

## 5. editable_fields —— 参数化表单字段

对齐复制按钮契约 v2（#123）：可编辑字段 + 实时预览 + 空值拦截。

```json
[
  { "name": "activity", "label": "活动", "value": "", "hint": "如: 写了 AI 调优代码", "required": true }
]
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | ✅ | 参数名（填进 prompt 的 key） |
| `label` | string | ✅ | 显示标签 |
| `value` | string | ✅ | 推荐值/默认值（可为空） |
| `hint` | string | 可选 | 输入提示（placeholder） |
| `required` | bool | 可选 | 必填标记（空值拦截；缺省 false） |

**来源映射（技能重构时）**：卡路里 fill_hints / 备忘录·作息 dimensions / 居家·大厨 prompt 内参数（`____` 占位符提取）。

## 6. 与 V4.16 原型的关系

本契约 = V4.16 原型数据形态（`GROUPS`）的正式化：

| V4.16 原型 | 本契约 |
|---|---|
| `GROUPS[].key` | `groups[].id` |
| `GROUPS[].icon/name` | `groups[].icon/label` |
| `GROUPS[].subgroups[].name` | `groups[].subgroups[].label` |
| `scenes[].id/name/chip` | `scenes[].id/title/wake_word` |
| `scenes[].prompt` | `scenes[].prompt_template` |
| `scenes[].params[]` | `scenes[].editable_fields[]` |

渲染输出与 V4.16 原型视觉一致（验收标准）。

## 7. 校验与守卫

- JSON schema：`公共组件/docs/scene_data.schema.json`（§8 完整定义）
- 守卫测试：`公共组件/tests/test_scene_data_contract.py`
  - 结构完整性：必填字段存在 + 类型正确 + `groups[].id`/`scenes[].id` 全局唯一 + 分组引用完整
  - status 二态：`''` / `【待开发】`
  - 违规反例：缺 `skill_name` / scenes 无 `prompt_template` / id 重复 → 校验失败
- 渲染器（injector --help-template）校验失败 → **渲染失败报错**（与组件契约硬拦截同级）

## 8. JSON schema

见 `scene_data.schema.json`（同目录）。schema 是本契约的机读编译版；本 md 是人读版，两处修改必须同步。

---

提交信息：
- 提交者: Mavis
- 提交时间: 2026-08-12 20:15
- 任务上下文: wayfinder #260 P2 #289 执行——统一 scene_data 契约 v1 入库（纯组件落地第 1 步）
