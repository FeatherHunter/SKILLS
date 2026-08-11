---
name: 公共组件
description: >
  Base Skill · 跨技能前端公共组件（任何 agent 可用, 不绑定 Mavis 体系）。
  提供统一注入管线 + P0/P1 组件（toast/copyText/注入器/守卫组 + buildDataText/
  actionBar/token）, 单一真相源防分叉漂移。装任何技能必须先装本基础包。
  触发词: 公共组件、Base Skill、注入器、公共组件HELP、base skill
---

# 公共组件（Base Skill）v1.1

跨技能前端公共层: **一套资产 + 注入占位符 → 任何技能的 HTML 渲染统一复用**。
装任何技能必须先装本基础包（强制依赖）;之上再选其他技能。

## 资产清单

```
公共组件/
  SKILL.md                 # 本文件（Base Skill 定义）
  README.md                # 使用手册（接管线步骤/占位符规范/验收清单模板）
  CHANGELOG.md             # 版本变更记录（契约 §8）
  assets/
    base.js                # P0+P1 JS（13 函数, 单一真相源）
    base.css               # token A 组（12 变量）+ 按钮样式
  injector.py              # 注入器（CLI + 硬拦截 + --strict-payload + 豁免通道）
  docs/
    component-contract.md  # 组件契约 v1.1（冻结接口, 修改走公共层 ISSUE）
    help-template-contract.md  # 参数化 HELP 模板契约 v1.1（P2 第二版）
  tests/
    test_injector.py       # 注入器守卫测试（17 项）
```

## 占位符契约（硬拦截）

| 占位符 | 规则 |
|---|---|
| `<!--INJECT-DATA-->` | **必须恰好 1**（缺失/重复 → 渲染失败） |
| `<!--SHARED-HELPERS-->` | **必须恰好 1**（缺失 → 渲染失败） |
| `<!--NO-SHARED-->` | 豁免通道: 确无公共 JS 的静态页显式声明（白名单式, 与 SHARED 互斥） |
| `<!--CHARTS-HELPERS-->` | 0 或 1（图表组件, 第二版） |

## 注入器用法

```bash
python 公共组件/injector.py <模板.html> --payload <数据.json> [--output <输出.html>] [--strict-payload]
```

- 校验: INJECT-DATA 恰 1 / SHARED 恰 1（或显式 NO-SHARED 豁免）/ CHARTS ≤1
- `--strict-payload`: 按信封契约校验必填字段（status/data.meta.command_cn/data.meta.occurred_at/data.scene）
- 注入顺序: SHARED → CHARTS → DATA;输出写文件 + 打印结果 JSON（status ok/error）

## P0/P1 组件（base.js 13 函数）

- **P0**: `esc/arr/val/yes/validate`（守卫组）+ `copyText(s)`（v2: 不改按钮文字 + 双 toast）+ `toast(msg, detail?)`（hm-toast 面板）+ `_fbCopy`
- **P1**: `metaHeader/remindersBlock/buildDataText/buildLogText/actionBar`

详细签名见 `docs/component-contract.md`（冻结接口, 修改必须走公共层 ISSUE + CHANGELOG）。

## 使用步骤（接管线）

1. 模板加占位符: `<script id="payload" type="application/json"><!--INJECT-DATA--></script>` + `<script><!--SHARED-HELPERS--></script>`
2. 渲染脚本调用注入器（或直接 import inject）: 模板 + payload → 输出 HTML
3. payload 走统一信封（`status/meta/scene`）
4. 守卫测试兜底: 漏接占位符 → 渲染失败即红

详见 `README.md` 完整手册。
