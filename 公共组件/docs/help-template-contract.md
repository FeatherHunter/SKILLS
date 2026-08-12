# 参数化 HELP 模板契约 v1.2（正式版 · 已入库 `公共组件/`）

> 来源：T4 决策（#264）+ 2026-08-11 对抗式审查 3 条修正（v1→v1.1）+ **#289 P2 HELP 参数化落地（v1.2 正式版）**
> 设计原则：**一套 HELP 模板 + 外部数据 → 自动生成任意技能的 HELP 页；传入什么，页面就是什么**。
> 数据结构权威 = `docs/scene-data-contract.md`（v1 已入库）——本契约只描述模板与注入器行为，数据结构见 scene-data-contract。

## 0. 版本记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.1 | 2026-08-11 | 草案（editable_fields / 文件名 sanitize / scene_data 盘点标注） |
| v1.2 | 2026-08-12 | **#289 正式版**：①§6 盘点确认完成（#287）②**归一化层实体取消**——技能侧重构数据对齐契约，Base 零翻译（用户拍板核心思想）③数据结构改嵌套 groups→subgroups→scenes（对齐 scene-data-contract v1 与 V4.16 原型）④meta_blocks 承载技能特有元信息 ⑤injector `--help-template` 落地 |

## 1. 模板结构（骨架 + 注入点）

```
公共组件/assets/help_template.html（Base 资产，单一真相源）
├── <head>  ────────── 注入: 页面标题（skill_name + title）
├── 顶部标题区 ──────── 注入: skill_name / title / subtitle / init_banner（可选）
├── meta_blocks 区 ─── 注入: 技能特有元信息透传块（可选）
├── 搜索区 ─────────── 内置（跨 Tab 全局搜索 + 高亮）
├── 内容目录区 ──────── 注入: groups（分组 Tab → 子功能折叠 → 场景卡）
├── Sheet 弹层 ─────── 参数表单（editable_fields）+ Prompt 实时预览 + 复制
├── 关于 Tab ───────── 注入: contact / version / recommendations（可选）
└── 底部 ──────────── 复用 Base P0 复制按钮/copyText/toast + statusBadge（#290 协同）
```

## 2. 注入参数（= scene-data-contract v1 顶层）

| 参数 | 类型 | 说明 | 必填 | 模板落点 |
|---|---|---|---|---|
| `skill_name` | string | 技能名（如 卡路里/作息管家） | ✅ | 标题、文件名、版本、各处技能名 |
| `title` | string | 页面大标题（如 能力速查台） | ✅ | 顶部标题区 |
| `subtitle` | string | 副标题/一句话说明 | 可选 | 顶部标题区 |
| `init_banner` | object | 首次使用横幅（title/subtitle/button_text/prompt/steps） | 可选 | 顶部横幅（未设置不渲染） |
| `meta_blocks` | array | 技能特有元信息 `[{id, title, html}]` | 可选 | 折叠区（原样透传） |
| `groups` | array | 2 级分组 `[{id, icon, label, subgroups:[{id, label, scenes[]}]}]` | ✅ | Tab + 子功能折叠 + 场景卡 |
| `contact` | object | 联系作者（items + copy_all） | 可选 | 关于 Tab |
| `version` | string | 技能版本号 | 可选 | 关于 Tab |
| `recommendations` | array | 其他技能推荐 | 可选 | 关于 Tab |

**校验**：必填缺失（skill_name/title/groups）→ 渲染失败报错（injector `validate_help_data`，与组件契约硬拦截同级）。

## 3. scenes 场景卡片结构

```json
{
  "id": "scene-id",
  "title": "场景标题",
  "wake_word": "唤醒词",
  "type": "采集/查看/结果/向导/批量/校验（可选）",
  "status": "'' | 【待开发】",
  "prompt_template": "复制 prompt 全文（与技能 scene_data 定稿零差异）",
  "editable_fields": [
    {"name": "参数名", "label": "显示标签", "value": "推荐值", "hint": "提示（可选）", "required": false}
  ]
}
```

- **`editable_fields`（v1.1 引入）**：复制按钮契约 v2（#123）「可编辑字段 + 实时预览 + 空值拦截」；无参数化需求时省略
- `prompt_template` 与各技能 scene_data 定稿 **必须零差异**（一致性契约 #123）
- `status:【待开发】` → 渲染待开发徽章（协同 #290 statusBadge 统一）

## 4. 文件名参数化（v1.1 安全规则）

- 缺省：`help_<skill_name>.html`（skill_name 经 sanitize 后拼接）
- 显式传入 `--output`：**sanitize 强制**——文件名部分只允许 `[a-zA-Z0-9_\-\u4e00-\u9fa5]+.html`；路径含 `..` 穿越 → 报错拒绝
- 目的：防路径穿越，保证输出始终落在预期目录

## 5. 渲染流程（injector `--help-template`）

```
<技能 scene_data 重构对齐契约>  →  scene_data.json（scene-data-contract v1）
   ▼
公共组件/injector.py --help-template <help_template.html> --payload scene_data.json [--output help_<技能>.html]
   │  校验：validate_help_data（必填 + 分组/场景规则 + editable_fields + status 二态 + id 唯一）
   │  + 文件名 sanitize（§4）
   ▼
help_<skill_name>.html（单文件离线 · 可手机打开）
```

技能侧调用（示例）：
```bash
python 公共组件/injector.py 公共组件/assets/help_template.html \
  --payload <技能>/<对齐后场景数据>.json --help-template \
  --output <输出目录>/help_<技能名>.html
```

## 6. scene_data 兼容性（v1.2 · #287 盘点确认完成）

- **盘点结论（#287 closed 2026-08-12）**：6 技能 scene_data 核心字段（wake_word/title/prompt/status）高度同构，统一为 2 级分组可行；差异集中在分组层级与 id 命名
- **归一化层实体取消（用户拍板核心思想 2026-08-12）**：Base 不内置任何技能翻译映射；技能在自己重构 view 时主动对齐 scene-data-contract v1，数据文件可动（「技能侧零改动」红线已废）
- 各技能对齐要点（移交 6 张技能重构优化票）：饼干 3 层展平、作息补一级分组、卡路里补 status、备忘录已有 category/subfunction 直接对齐

## 7. 与现有资产的关系

- 现有 4 种 HELP 布局家族（居家模板家族源 / 卡路里 4 层独立 / 作息 3 层+工具栏 / 私家大厨 ww-card）→ 技能重构时收敛到 Base help_template.html，各技能传数据
- 复制 prompt 交互复用 Base P0（copyText/toast）；参数化场景复用「复制按钮契约 v2」（editable_fields）；待开发徽章复用 statusBadge（#290）
- **范围：P2（第二版）正式落地**——本契约 v1.2 + scene-data-contract v1 + help_template.html + injector `--help-template` 全部入库（#289）

---
提交信息：
- 提交者: Mavis
- 提交时间: 2026-08-12 20:35
- 任务上下文: #289 执行——HELP 契约 v1.1 草案升版 v1.2 正式版（#287 盘点确认 + 归一化层取消 + 数据结构对齐 scene-data-contract）
