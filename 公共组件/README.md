# 公共组件（Base Skill）使用手册 v1.1

> 跨技能前端公共层: 一套资产 + 注入占位符 → 任何技能 HTML 渲染统一复用。
> 本手册 = 从作息管家试点（#269）提炼的接管线操作手册;修改资产/契约见 `CHANGELOG.md` 与 `docs/component-contract.md`。

## 0. 快速总览

| 你要做什么 | 去哪里 |
|---|---|
| 接 Base 管线 | 见 §1（5 步） |
| 占位符规范 | 见 §2 |
| payload 信封 | 见 §3 |
| 复制按钮/复制数据/日志 | 见 §4 |
| 验收清单模板 | 见 §5 |
| 版本变更 | `CHANGELOG.md` |
| 冻结接口定义 | `docs/component-contract.md` |

## 1. 接 Base 管线（5 步）

1. **复制资产**: 模板 HTML 中加入两个占位符（见 §2）——数据注入点 + 公共 JS 注入点
2. **payload 信封**: 渲染脚本构造统一信封 `{status, data:{meta, scene}}`（必填字段见 §3）
3. **调用注入器**（CLI 或 import）:
   ```bash
   python 公共组件/injector.py templates/<模板>.html --payload <数据.json> --output <输出.html> --strict-payload
   ```
   或 Python:
   ```python
   from injector import inject
   html, err = inject(template_text, payload, js_asset=base_js_text)
   if err: raise RuntimeError(err)  # 硬拦截: 漏占位符/坏 payload 直接失败
   ```
4. **守卫测试**: 加一条测试断言「模板含占位符 + 注入后占位符 0 残留」（参考 `公共组件/tests/test_injector.py`）
5. **验收**: 打开输出页面人工验收（清单见 §5）

> 第一次接管线 = 一次性动作;后续每波组件（复制按钮/toast/按钮栏）只需在模板里声明并使用 Base 函数, 管线不动。

## 2. 占位符规范

| 占位符 | 规则 | 说明 |
|---|---|---|
| `<!--INJECT-DATA-->` | **必须恰好 1** | 数据注入点（payload JSON） |
| `<!--SHARED-HELPERS-->` | **必须恰好 1** | 公共 JS 注入点（base.js） |
| `<!--NO-SHARED-->` | 0 或 1 | 豁免通道: 确无公共 JS 的静态页显式声明（与 SHARED 互斥, 不得注释占位符隐式豁免） |
| `<!--CHARTS-HELPERS-->` | 0 或 1 | 图表组件（第二版） |

模板最小骨架:

```html
<script id="payload" type="application/json"><!--INJECT-DATA--></script>
<script>
<!--SHARED-HELPERS-->
// 这里使用 base.js 暴露的函数（esc/val/yes/copyText/toast/...）
</script>
```

## 3. payload 信封（必填字段）

```json
{
  "status": "ok",
  "data": {
    "meta": {
      "command_cn": "操作中文名",
      "occurred_at": "本地时间",
      "skill_name": "技能中文名(可选, buildDataText 用)",
      "wake_word": "(可选)",
      "skill_version": "(可选)"
    },
    "scene": { "...场景专属字段..." }
  }
}
```

**必填**: `status`('ok') / `data.meta.command_cn` / `data.meta.occurred_at` / `data.scene`(对象)。
注入器 `--strict-payload` 会校验;存量技能过渡期可关。

## 4. 复制按钮三件套

| 函数 | 用途 | 按钮样式 |
|---|---|---|
| `copyText(s)` | 复制任意文本 | 任意 `.copy` 按钮 `onclick="copyText(this.dataset.t)"` |
| `buildDataText(p)` | 人类可读数据快照（`【技能名 · 操作】` + 关键指标 + 明细） | `.copy.ghost` 复制数据 |
| `buildLogText(p)` | 6 段日志（场景标识/思考链/数据结构/调用链/时间戳版本/异常） | `.copy.ghost` 复制日志 |

`actionBar(p, extra, noSb?)` 一键生成场景按钮 + 复制数据/日志（ghost 独立一行）。

**按钮规范**（对齐 08 规范）: ≤3 色按功能区分（蓝=主操作 / 红=危险 / ghost=复制）;偶数一行 2 个, 奇数重要按钮加 `.wide` 单独一行;复制数据/日志 = 白底+主色描边+主色文字胶囊, min-height 48px。

## 5. 验收清单模板（每技能迁移后）

- [ ] 所有相关 HTML 页面逐一打开（人工验收面）
- [ ] 按钮样式统一（computed 颜色 ≤3 色 / 无换行 / 无省略号）
- [ ] 复制出的 prompt 信息正确（参数格式 / 内容零差异）
- [ ] 复制按钮文字恒定（点击后不变, Toast 独立反馈）
- [ ] 守卫测试绿（占位符 0 残留 + 漏接即红）

## 6. 常见问题

- **渲染失败报「模板必须包含恰好 1 个 SHARED-HELPERS」**: 模板漏加占位符或误删 → 补占位符;确无公共 JS 的静态页改用 `<!--NO-SHARED-->`
- **复制按钮点击无反应**: 确认 base.js 已注入（F12 看 `copyText` 是否定义）+ payload 已注入（`window.__hmPayload`）
- **要改组件**: 走公共层 ISSUE（总纲 09 §92）+ CHANGELOG;技能内文件只读, 防同源双写漂移
