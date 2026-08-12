# 公共组件（Base Skill）使用手册 v1.2

> 跨技能前端公共层: 一套资产 + 注入占位符 → 任何技能 HTML 渲染统一复用。
> 本手册 = 从作息管家试点（#269）提炼的接管线操作手册;修改资产/契约见 `CHANGELOG.md` 与 `docs/component-contract.md`。

## 0. 快速总览

| 你要做什么 | 去哪里 |
|---|---|
| 接 Base 管线 | 见 §1（6 步） |
| 占位符规范 | 见 §2 |
| payload 信封 + snapshot | 见 §3 |
| 复制按钮/复制数据/日志 | 见 §4 |
| 新控件（formPrompt/selectList/confirm 等） | 见 §4.2 |
| toast 通用提示 | 见 §4.3 |
| **参数化 HELP（v1.5 新增）** | **见 §4.4** |
| 验收清单模板 | 见 §5 |
| 版本变更 | `CHANGELOG.md` |
| 冻结接口定义 | `docs/component-contract.md` |

## 4.4 参数化 HELP（v1.5 · #289）

**一句话**: 技能把场景数据重构为统一契约（`docs/scene-data-contract.md` v1）→ 调 Base 渲染 → 得到 HELP 页。Base 零翻译、零适配（用户拍板核心思想: Help HTML 对外参数定死, 适配是技能自己的事）。

**契约**: `docs/scene-data-contract.md`（人读版）+ `docs/scene_data.schema.json`（机读版）; 模板 = `assets/help_template.html`; 注入器 = `injector.py --help-template`。

**技能接入 4 步**（6 张技能重构优化票执行依据）:

1. **对齐数据结构**: 把技能 scene_data 重构为契约 v1（2 级分组 groups→subgroups→scenes;字段 id/title/wake_word/type/status/prompt_template/editable_fields）——数据文件可以直接改, 这是重构的一部分
2. **技能特有内容进 meta_blocks**: prompt_rules/methodology/status_legend/dependencies/AI 验证协议等技能特有 HTML 段, 放顶层 `meta_blocks` 原样透传（Base 只透传不解析）
3. **渲染**: `python 公共组件/injector.py 公共组件/assets/help_template.html --payload <对齐后数据>.json --help-template --output <输出>/help_<技能名>.html`
4. **验收**: 与 V4.16 原型视觉一致（用户验收）+ 复制 prompt 正确（参数表单/空值拦截/toast）+ 手机三档视口 0 溢出

**提示**:
- 文件名缺省 `help_<技能名>.html`, 显式 `--output` 文件名部分 sanitize（含 `..` 拒绝）
- `status:【待开发】` 渲染待开发徽章（协同 #290 statusBadge）; `editable_fields` 走契约 v2 参数表单（实时预览 + 空值拦截）
- 示例数据: `docs/examples/help_example_data.json`（覆盖全部特性）——新技能对齐时可参照
- 原技能 HELP 渲染器（如作息 help_render.py / 卡路里 render_help_center.py）在技能重构票中退役或改调 Base


## 1. 接 Base 管线（6 步 · 从作息管家试点提炼）

1. **加占位符**: 模板 HTML 加 3 个占位符（§2）——数据注入点 + 公共 JS 注入点 + 公共 CSS 注入点
2. **payload 信封**: 渲染脚本构造统一信封 `{status, data:{meta, scene}}`;场景数据组织成 `scene.snapshot`（§3）
3. **渲染脚本调 Base 注入器**（CLI 或 import）:
   ```bash
   python 公共组件/injector.py templates/<模板>.html --payload <数据.json> --output <输出.html> --strict-payload
   ```
   或 Python（作息管家范式: 模板预处理 + Base 注入分离）:
   ```python
   from injector import inject
   base_js = (BASE_DIR / 'assets' / 'base.js').read_text(encoding='utf-8').strip()
   base_css = (BASE_DIR / 'assets' / 'base.css').read_text(encoding='utf-8').strip()
   html, err = inject(template_text, payload, js_asset=base_js, css_asset=base_css)
   if err: raise RuntimeError(err)  # 硬拦截: 漏占位符/坏 payload 直接失败
   ```
   > **Base 资产路径**: 仓库布局 `<repo>/公共组件`（技能在 `<repo>/<技能>/` 时 = `技能目录.parent / "公共组件"`）;测试隔离用环境变量 `SKILLS_BASE_DIR` 覆盖（仅 fallback, 真实路径优先）
4. **复制按钮统一 Base**: 模板/JS 里所有复制逻辑（copyText/clipboard/变绿反馈）换 `window.copyText()`（§4）;自研 toast 删除, 换 `window.toast()`（§4.3）
5. **守卫测试**: `tests/test_base_pipeline.py` 断言「3 占位符恰 1 + 注入后占位符 0 残留 + 缺占位符渲染失败」（漏迁即红）
6. **验收**: 打开输出页面人工验收（清单 §5）

> 第一次接管线 = 一次性动作;后续每波组件（toast/按钮栏/新控件）只需在模板里声明并使用 Base 函数, 管线不动。
> ⚠️ 占位符必须放在独立 `<script>`/`<style>` 块内, 勿与 `</script>`/`</style>` 字样混在资产注释里（base.css 曾因注释含 `</style>` 导致 HTML 解析提前闭合, 已修复为「勿含闭合标签字样」约定）。

## 2. 占位符规范

| 占位符 | 规则 | 说明 |
|---|---|---|
| `<!--INJECT-DATA-->` | **必须恰好 1** | 数据注入点（payload JSON） |
| `<!--SHARED-HELPERS-->` | **必须恰好 1** | 公共 JS 注入点（base.js） |
| `<!--SHARED-CSS-->` | **必须恰好 1**（v1.2） | 公共 CSS 注入点（base.css） |
| `<!--NO-SHARED-->` | 0 或 1 | 豁免通道: 确无公共 JS/CSS 的静态页显式声明（与 SHARED 互斥, 不得注释占位符隐式豁免） |
| `<!--CHARTS-HELPERS-->` | 0 或 1 | 图表组件（第二版） |

模板最小骨架:

```html
<script id="payload" type="application/json"><!--INJECT-DATA--></script>
<script>
<!--SHARED-HELPERS-->
// 这里使用 base.js 暴露的函数（esc/val/yes/copyText/toast/buildDataText/...）
</script>
<style>
<!--SHARED-CSS-->
</style>
```

## 3. payload 信封 + snapshot（v1.2 核心 · 领域无关）

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
    "scene": {
      "scene_id": "(可选)",
      "snapshot": {
        "title": "场景中文名",
        "summary": ["关键指标行1", "关键指标行2"],
        "sections": [{"heading": "分节标题", "rows": ["明细行1", "明细行2"]}]
      }
    },
    "copy_log": { "thinking": "...", "data_structure": "...", "call_chain": "...", "timestamp": "...", "exception": "..." }
  }
}
```

**必填**: `status`('ok') / `data.meta.command_cn` / `data.meta.occurred_at` / `data.scene`(对象)。
**snapshot 结构校验（违规直接报错）**: title 非空字符串 + summary 数组 + sections 数组（每节 heading+rows）——缺/错 → 渲染失败（用户拍板「违规直接报错」）。
**领域无关声明**: snapshot 是通用结构, Base 不认任何技能领域字段——技能把领域数据组织成 snapshot 传入, Base 只渲染（用户决策 2: 高于一切）。改排版只改 Base, 全技能零改动。

## 4. 复制按钮三件套（v1.2）

| 函数 | 用途 | 按钮样式 |
|---|---|---|
| `copyText(s, opts?)` | 复制任意文本（按钮文字恒定 + toast 反馈; opts.silent 静默） | 任意 `.copy` 按钮 |
| `buildDataText(p, format?)` | snapshot → 人类可读数据（text/json/csv; 敏感行脱敏） | `.copy.ghost` 复制数据 |
| `buildLogText(p, format?)` | 6 段日志 | `.copy.ghost` 复制日志 |

`actionBar(p, extra?, opts?)` 一键生成场景按钮 + 复制数据/日志（ghost 独立一行）;opts: `{preview(复制前预览), formatMenu(格式选择), download(导出)}`。

**按钮规范**（对齐 08 规范）: ≤3 色按功能区分（蓝=主操作 / 红=危险 / ghost=复制）;偶数一行 2 个, 奇数重要按钮加 `.wide` 单独一行;复制数据/日志 = 白底+主色描边+主色文字胶囊, min-height 48px。

## 4.2 新控件（P0+P1 · v1.2）

| 组件 | 签名 | 用途 |
|---|---|---|
| `formPrompt(fields, template)` | 字段定义 + prompt 模板 → HTML | 用户填参数表单 + 实时预览 + 空值拦截（#122 拍板: 页内表单, 禁系统弹窗） |
| `selectList(items, batchActions?, opts?)` | 条目 + 批量操作 → HTML | 勾选列表 + 批量操作 + 「本组已选 x/y」计数联动 |
| `confirm({title, detail?, danger?, onOk})` | 配置 → 对话框 | 危险操作二次确认（danger 红按钮） |
| `foldBox(title, contentHtml)` | 标题 + 内容 → HTML | 折叠区（查看详情/原始数据） |
| `statusBadge(status, text?)` | ok/warn/danger/empty → HTML | 状态徽章 |
| `emptyState({icon?, text, hint?, action?})` | 配置 → HTML | 空状态友好提示 |
| `errorReceipt({message, retryPrompt?, data?, log?})` | 配置 → HTML | 错误回执（修正重试 + 复制数据/日志） |

## 4.3 toast 通用提示控件（v1.2 增强 · 向后兼容）

```js
toast(msg, detail?, {
  icon: 'copy'|'ok'|'warn'|'danger'|'info'|emoji,   // 内置图标库或自定义
  badge: { text: '成功', type: 'ok'|'warn'|'danger' },  // 状态徽章
  actions: [{ label: '撤销', onClick: fn }],             // 快捷操作（最多 2）
  count: '5 条',                                         // 轻量计数
  lines: ['多行'],                                       // 富详情多行
  code: '堆栈',                                          // 富详情代码块
  timeout: 4500,
})
```

- `toast(msg, detail)` 不带 options = 完全等价 v1.1（调用方零改动）
- 队列管理（连续触发不叠加）+ 无障碍 aria + 样式 Base 管（技能零样式副本）
- 复制类操作反馈统一 toast（「已复制 · 粘贴给 AI」/「复制失败 · 长按选择文本手动复制」）

## 5. 验收清单模板（每技能迁移后）

- [ ] 所有相关 HTML 页面逐一打开（人工验收面）
- [ ] 按钮样式统一（computed 颜色 ≤3 色 / 无换行 / 无省略号 / 手机 375/390/320 三档 0 溢出）
- [ ] 复制出的 prompt 信息正确（参数格式 / 内容零差异）
- [ ] 复制按钮文字恒定（点击后不变, Toast 独立反馈）
- [ ] **08 规范硬标准逐模板核对: 每个业务模板必须有「复制数据」+「复制日志」按钮**（#269 遗漏教训——grill 拍板「补齐」实施时收缩成「只统一」导致 18/19 缺失; 守卫测试必须断言按钮存在性, 不能只测管线占位符）
- [ ] 复制数据/日志内容正确（人类可读全中文 / snapshot 结构 / 脱敏生效）
- [ ] 守卫测试绿（3 占位符恰 1 + 注入后占位符 0 残留 + **每个业务模板含复制数据/日志按钮** + 漏迁即红）
- [ ] 自研 toast/复制实现已删除（全走 Base）; **engine 型模板的外部 JS（_record_engine.js/helper）也要审计, 不能只看模板字符串**
- [ ] 实施范围 = 拍板范围（收缩必须记录偏离 + 回报用户）
- [ ] 无生产库写入（全程临时 DB 验证）

## 6. 常见问题

- **渲染失败报「模板必须包含恰好 1 个 SHARED-HELPERS/SHARED-CSS」**: 模板漏加占位符或误删 → 补占位符;确无公共 JS/CSS 的静态页改用 `<!--NO-SHARED-->`
- **复制按钮点击无反应**: 确认 base.js 已注入（F12 看 `copyText` 是否定义）+ payload 已注入（`window.__hmPayload`）
- **buildDataText 报「snapshot 违规」**: scene.snapshot 缺 title/summary/sections 或类型错 → 按 §3 结构补
- **测试隔离**: 渲染/写库测试把 `SKILLS_DB_PATH` 指向临时目录 + `SKILLS_BASE_DIR` 指向公共组件（如测试把技能复制到 temp）
- **要改组件**: 走公共层 ISSUE（总纲 09 §92）+ CHANGELOG;技能内文件只读, 防同源双写漂移
