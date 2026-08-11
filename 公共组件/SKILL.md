---
name: 公共组件
description: >
  Base Skill · 跨技能前端公共组件（任何 agent 可用, 不绑定 Mavis 体系）。
  提供统一注入管线 + 控件库（toast 通用提示/copyText/复制数据日志/formPrompt/
  selectList/confirm 等, 领域无关 snapshot 接口）, 单一真相源防分叉漂移。
  装任何技能必须先装本基础包。
  触发词: 公共组件、Base Skill、注入器、公共组件HELP、base skill
---

# 公共组件（Base Skill）v1.2

跨技能前端公共层: **一套资产 + 注入占位符 → 任何技能的 HTML 渲染统一复用**。
装任何技能必须先装本基础包（强制依赖）;之上再选其他技能。

## 资产清单

```
公共组件/
  SKILL.md                 # 本文件（Base Skill 定义）
  README.md                # 使用手册（接管线步骤/占位符规范/验收清单模板）
  CHANGELOG.md             # 版本变更记录（契约 §8）
  assets/
    base.js                # 控件库 JS（toast/copyText/buildDataText/formPrompt/... 唯一真相源）
    base.css               # token A 组 + 全部控件样式（唯一真相源）
  injector.py              # 注入器（CLI + 硬拦截 + JS/CSS 注入 + payload 校验）
  docs/
    component-contract.md  # 组件契约 v1.2（冻结接口, 修改走公共层 ISSUE）
    help-template-contract.md  # 参数化 HELP 模板契约（P2 第二版）
  tests/
    test_injector.py       # 注入器守卫测试
    test_components.py     # 控件函数测试（v1.2 新增）
```

## 占位符契约（硬拦截）

| 占位符 | 规则 |
|---|---|
| `<!--INJECT-DATA-->` | **必须恰好 1**（缺失/重复 → 渲染失败） |
| `<!--SHARED-HELPERS-->` | **必须恰好 1**（缺失 → 渲染失败） |
| `<!--SHARED-CSS-->` | **必须恰好 1**（v1.2 新增, 缺失 → 渲染失败） |
| `<!--NO-SHARED-->` | 豁免通道: 确无公共 JS/CSS 的静态页显式声明（白名单式, 与 SHARED 互斥） |
| `<!--CHARTS-HELPERS-->` | 0 或 1（图表组件, 第二版） |

## 注入器用法

```bash
python 公共组件/injector.py <模板.html> --payload <数据.json> [--output <输出.html>] [--strict-payload]
```

- 校验: INJECT-DATA 恰 1 / SHARED 恰 1 / SHARED-CSS 恰 1（或显式 NO-SHARED 豁免）/ CHARTS ≤1
- `--strict-payload`: 按信封契约校验必填字段（status/data.meta.command_cn/data.meta.occurred_at/data.scene）
- 注入顺序: SHARED(JS) → SHARED-CSS → CHARTS → DATA;输出写文件 + 打印结果 JSON（status ok/error）

## 控件库（领域无关 · v1.2）

**核心原则（用户 2026-08-11 拍板, 高于一切）**: Base 接口**不绑定任何技能领域**。
技能把领域数据组织成通用结构（snapshot）传入, Base 渲染;改样式/格式只改 Base, 全技能零改动。

- **P0**: `esc/arr/val/yes/validate`（守卫组）+ `copyText(s, opts?)`（不改按钮文字 + toast）+ `toast(msg, detail?, options?)`（通用提示控件）+ `_fbCopy`
- **P1**: `buildDataText(p, format?)` / `buildLogText(p, format?)`（snapshot 结构化, 违规报错）+ `actionBar(p, extra?, opts?)` + `metaHeader` + `remindersBlock`
- **P1.5 新控件（v1.2）**: `formPrompt(fields, template)`（参数表单+实时预览+空值拦截）/ `selectList(items, batchActions?, opts?)`（勾选+批量+计数联动）/ `confirm({...})`（危险确认）/ `foldBox(title, html)` / `statusBadge(status, text?)` / `emptyState({...})` / `errorReceipt({...})`

详细签名见 `docs/component-contract.md`（冻结接口, 修改必须走公共层 ISSUE + CHANGELOG）。

## 使用步骤（接管线）

1. 模板加占位符: `<script id="payload" type="application/json"><!--INJECT-DATA--></script>` + `<script><!--SHARED-HELPERS--></script>` + `<style><!--SHARED-CSS--></style>`
2. 渲染脚本调用注入器（或直接 import inject）: 模板 + payload → 输出 HTML
3. payload 走统一信封（`status/meta/scene`）;场景数据组织成 `scene.snapshot`（title/summary/sections）
4. 守卫测试兜底: 漏接占位符 → 渲染失败即红

详见 `README.md` 完整手册。
