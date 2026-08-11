# 参数化 HELP 模板契约 v1.1（待入库 `公共组件/`）

> 来源：T4 决策（#264）+ **2026-08-11 对抗式审查 3 条修正**（v1 → v1.1：可编辑字段结构 / 文件名安全 / scene_data 兼容性标注）
> 设计原则：**一套 HELP 模板 + 外部数据 → 自动生成任意技能的 HELP 页；传入什么，页面就是什么**。图表留第二版。

## 1. 模板结构（骨架 + 注入点）

```
help_template.html（Base 资产，单一真相源）
├── <head>  ────────── 注入: 页面标题（含技能名）
├── 顶部标题区 ──────── 注入: skill_name / title / subtitle
├── 内容目录区 ──────── 注入: groups（分组导航）
├── 场景内容区 ──────── 注入: scenes（场景卡片，含 prompt_template + 可选 editable_fields）
└── 底部 ──────────── 复用 Base P0 复制按钮/copyText/toast
```

## 2. 注入参数

| 参数 | 类型 | 说明 | 必填 | 模板落点 |
|---|---|---|---|---|
| `skill_name` | string | 技能名（如 卡路里/作息管家） | ✅ | 标题、文件名、各处技能名 |
| `title` | string | 页面大标题（如 能力速查台） | ✅ | 顶部标题区 |
| `subtitle` | string | 副标题/一句话说明 | 可选 | 顶部标题区 |
| `groups` | array | 分组列表 `[{id, label, count}]` | ✅ | 内容目录区（导航） |
| `scenes` | array | 场景卡片（见 §3） | ✅ | 场景内容区 |
| `output_filename` | string | 输出文件名（如 `help_卡路里.html`） | 可选（缺省按 skill_name 生成） | 文件名参数化 |

**校验**：必填缺失 → 渲染失败报错（与组件契约硬拦截同级）。

## 3. scenes 场景卡片结构

```json
{
  "id": "scene-id",
  "category": "分组 id（对应 groups[].id）",
  "title": "场景标题",
  "wake_word": "唤醒词",
  "prompt_template": "复制 prompt 全文（与 scene_data/HELP 定稿零差异）",
  "editable_fields": [
    {"name": "参数名", "label": "显示标签", "value": "推荐值", "hint": "提示（可选）"}
  ]
}
```

- **`editable_fields`（v1.1 新增）**：支持复制按钮契约 v2（#123）的「可编辑字段 + 实时预览 + 空值拦截」场景；无参数化需求时省略
- `prompt_template` 与各技能 `scene_data/NN-分类.json` 的 prompt_template **必须零差异**（一致性契约 #123）

## 4. 文件名参数化（v1.1 安全规则）

- 缺省：`help_<skill_name>.html`（skill_name 已 sanitize 后拼接）
- 显式传入 `output_filename`：**sanitize 强制**——只允许 `[a-zA-Z0-9_\-\u4e00-\u9fa5]` + 结尾 `.html`；包含路径分隔符（`/ \ ..`）→ 报错拒绝
- 目的：防路径穿越，保证输出始终落在预期目录

## 5. 渲染流程

```
help_data.json（技能侧从 scene_data 提供）
   ▼
公共组件/injector.py --help-template（或 help_renderer.py）
   │  校验：必填参数 + editable_fields 结构 + 文件名 sanitize
   ▼
help_<skill_name>.html
```

## 6. scene_data 兼容性（v1.1 标注 · 待盘点确认）

- 本契约假设各技能 scene_data JSON 可映射为统一 scenes 结构——**尚未盘点验证**（各技能 scene_data 结构可能不一致）
- **P2 实施前必须先做 scene_data 结构盘点**，确认统一结构可行后再定稿本契约；盘点前本契约视为草案（已记 map 盲区清单）

## 7. 与现有资产的关系

- 现有 4 种 HELP 布局家族（居家管家模板家族源 / 卡路里 4 层独立 / 作息 3 层+工具栏 / 私家大厨 ww-card）→ 迁移时以 Base 模板为准，各技能传数据收敛
- 复制 prompt 交互复用 Base P0（copyText/toast）；参数化场景复用「复制按钮契约 v2」（editable_fields）
- **范围：P2（第二版）**——第一版只做 P0+P1 组件，HELP 模板骨架统一留到 Base 跑稳后

---
提交信息：
- 提交者: Mavis
- 提交时间: 2026-08-11 12:07
- 任务上下文: #264 推进——对抗式审查 3 条修正（editable_fields/文件名 sanitize/scene_data 盘点标注）落地 v1.1
