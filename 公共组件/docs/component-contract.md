# Base 组件契约 v1.25

> 来源：v1.3（#288 图表组件落地）+ v1.4（#290 状态层加固）+ v1.5（#289 HELP 参数化）+ **v1.6 图表全参数化**（2026-08-12：方向 A 定稿，四形态全参数 + 复合形态）+ **v1.9 selectList 行内控件**（2026-08-13 · #327）+ **v1.10 copyText 反馈钩子**（2026-08-13 · #328）+ **v1.11 smartSelect 选择器组件**（2026-08-13 · #312 · 立项 #320）+ **v1.12 smartSelect 候选区折叠**（2026-08-13 · #312 实测反馈）+ **v1.13 line 动画断线修复**（2026-08-14 · #317 验收二轮）+ **v1.14 charts.line connectNulls**（2026-08-14 · #356）+ **v1.15 charts.line yTicks 轴刻度**（2026-08-14 · #333）+ **v1.16 markLine 标签拉伸/遮挡修复**（2026-08-14 · #333 验收）+ **v1.17 series[].ownScale 系列独立刻度**（2026-08-14 · #334）+ **v1.18 markPoint 峰谷点标注**（2026-08-14 · #319）+ **v1.19 band 置信带**（2026-08-14 · #335）+ **v1.20 markLine 竖线 xValue**（2026-08-14 · #340）+ **v1.21 fillBetween 线间填充**（2026-08-14 · #338）+ **v1.22 小缺口：异常点/拐点圈选/首尾标签避让**（2026-08-14 · #341）+ **v1.23 bar 堆叠柱 stacked**（2026-08-14 · #336）+ **v1.24 bar 分组双柱 grouped**（2026-08-14 · #339）+ **v1.25 charts.scatter 散点图**（2026-08-14 · #337）
> 本契约是 Base Skill 组件的**冻结接口**，修改必须走公共层 ISSUE（总纲 09 §92）+ 遵循 §8 版本机制。

## 0. 版本记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-08-11 | 初稿（P0 签名/P1 契约/占位符/注入器接口） |
| v1.1 | 2026-08-11 | 对抗式审查 6 条修正（唯一真相源/payload 信封/豁免通道/版本机制/P0P1 分界/结构校验）+ 信封加 `meta.skill_name` |
| v1.2 | 2026-08-11 | **#269 试点用户拍板全量落地**：①buildDataText/buildLogText 重构为**领域无关 snapshot 结构化接口**（title/summary/sections，零居家管家字段绑定）②toast 升级**通用提示控件**（4 形态：徽章/操作/计数/留空 + 队列 + 图标库 + 多操作 + 富详情 + 无障碍）③复制按钮控件化（预览/格式选择/脱敏/导出）④新控件 P0+P1（formPrompt/selectList/confirm/foldBox/statusBadge/emptyState/errorReceipt）⑤injector 加 **SHARED-CSS 注入**（修 v1.1 只注入 JS 缺口）⑥结构校验违规**直接报错**（硬拦截） |
| v1.3 | 2026-08-12 | **#288 P2 图表组件落地**：新增 `assets/charts.js`（`charts.bar/line/donut/progress` 四接口，纯 CSS+SVG 无外部依赖，数据空→emptyState 联动）；`<!--CHARTS-HELPERS-->` 从「第二版预留」转**正式版**；注入器 `--charts` 参数正式化；SHARED_JS 全家桶处置清单（Base 等价物走 Base / 图表走 charts.js / 居家特定留技能侧） |
| v1.4 | 2026-08-12 | **#290 P2 状态层落地（加固）**：三控件（statusBadge/emptyState/errorReceipt）从「零消费方定义」加固为**对外可靠接口**——①errorReceipt 去掉 `window.__hmPayload` 强依赖（新增显式 `payload` 参数优先、`data/log` 字符串直传兜底）②errorReceipt 复制按钮改为渲染期生成文本存 `data-t`（onclick 仅 `copyText(this.dataset.t)`，零注入面；点击不再实时调 buildDataText）③errorReceipt 补 `.hm-actions` 网格布局（修正重试 primary wide 独立一行 + 复制数据/日志 ghost 一行 2 个，08 规范奇数按钮）④payload 无 snapshot 时容错（不渲染复制按钮，控件不崩）⑤statusBadge 非法 status 白名单降级 `empty`（防无样式徽章）⑥emptyState/statusBadge/errorReceipt 全部文本字段 esc 防 XSS，action 明示「受信 HTML 透传」。守卫测试 +9（边界/XSS/容错/布局） |
| v1.6 | 2026-08-12 | **图表全参数化（方向 A 定稿）**：charts.js 四形态全参数化（line 16 项 / bar 7 / donut 6 / progress 4）+ 复合形态（combo 柱线组合 / sparkline 迷你趋势 / gauge 仪表盘）+ 结构校验违规报错（对齐 v1.2）+ 坐标唯一性（容器零 padding）+ 双端自适应（≤720px 独立 UI）+ 全部动画。守卫测试 141/141。**注意：v1.6 与 #289/#290 并发推进，版本号按落地顺序递增** |
| v1.9 | 2026-08-13 | **#327 selectList 行内控件**（非破坏性 · 签名零变更）：①items[].widget 新可选字段（date/text/select，行内控件与勾选/批量/计数共存）②批量回调第二参 `onClick(ids, values)` = 勾选条目行内值（只读勾选，未填 → null）③读取接口选定形态 = `opts.onSubmit(selectedIds, values)`（全部行内值，含未勾选条目）④计数联动隔离（控件值变化不干扰）⑤行内值渲染一律 esc 零注入面。守卫测试 +11 → 162/162 全绿。详见 §6.7 |
| v1.10 | 2026-08-13 | **#328 copyText 反馈钩子**（非破坏性 · 签名零变更）：①`opts.toast = {ok:{msg,detail,icon?}, fail:{msg,detail,icon?}}` 自定义成功/失败 toast 文案（只覆盖提供字段，缺省回落默认，对齐 08 规范「文案由技能自设计」）②`opts.onOk`/`opts.onFail` 回调（成功/最终失败必触发，互斥；`silent` 时不弹 toast 仍触发）③未传新选项行为与 v1.9 逐字一致。守卫测试 +7 → 169/169 全绿。详见 §6.8 |
| v1.11 | 2026-08-13 | **#312 smartSelect 选择器组件**（非破坏性 · 新增全局函数 + 新增样式 · 既有接口零变更；立项 #320）：①字段级「复用优先·新建其次」选择器，`smartSelect(el, config)` 一行接入，一页 N 实例互不干扰 ②config 与 `form.selector.<fieldKey>` 对齐（options/inferred/recommended_new/initial{name,source}），零领域词全参数化（texts/theme 外部注入）③初始选中推导 = initial > AI 推断 > 历史预填 > AI 推荐新建 > 空 ④回填协议 input.value + dataset.source + dataset.new + change 事件，prompt 上层自拼 ⑤结构校验违规直接报错 + source 白名单 + 类名全 ss- 命名空间 ⑥options 空数组且无推断/推荐 → 降级普通输入 ⑦全部动态文本 esc 零注入面。守卫测试 +29 → 全量全绿。详见 §6.9 |
| v1.12 | 2026-08-13 | **#312 实测反馈 · smartSelect 候选区折叠**（非破坏性 · 新可选参数 `maxChips` 缺省 8 · 签名零变更）：①候选 chips 超阈值折叠（前 maxChips 个 + 「展开全部(N)」/「收起」按钮，样式 `.ss-more`）②初始选中项在折叠区时保可见（提前进可见区）③搜索输入全量过滤（跳过折叠，折叠区候选可搜出）④搜索框内容跨渲染保持，清空回折叠态 ⑤展开态点选后保持展开。守卫测试 +8 → 全量全绿。详见 §6.9 |
| v1.13 | 2026-08-14 | **#317 验收二轮 · line 动画断线修复**（非破坏性 · 内部实现）：动画过渡结束（transitionend + 1.2s 兜底）清除 `stroke-dasharray` 残留，恢复实线（`preserveAspectRatio=none` 拉伸下 dash 按屏幕像素解释导致中段断线）。守卫测试 +2。**本条目为 §0 漏记补录**（CHANGELOG 已有 v1.13） |
| v1.14 | 2026-08-14 | **#356 charts.line 缺失值连线 connectNulls**（非破坏性 · 新可选参数 `connectNulls` 默认 false · 签名零变更）：跨 null 断点连线（跳过缺失值直连相邻有效点）；缺值日无 dot、首尾 null 不延伸、全 null 仍空路径；与 smooth/step/area/series/avgLine 正交可组合（area 跟随同一开关、avgLine 均线跨 null 连线）。守卫测试 +9 → 全量全绿（tests/ 221/221）。详见 §6.5 |
| v1.15 | 2026-08-14 | **#333 charts.line Y 轴刻度文字 yTicks**（非破坏性 · 新可选参数 `yTicks` 数字=刻度数收敛 2-6 / false 关闭 · 签名零变更）：左侧刻度短线（SVG）+ 刻度文字（HTML 覆盖层不占位）；值域 = 共享 Y 域（含 padding）均分，文字走 `format`，首尾贴边防裁剪；默认关闭既有渲染逐字节不变；与 series/grid:false/tooltip 正交。守卫测试 +9 → 全量全绿（tests/ 230/230）。详见 §6.5 |
| v1.16 | 2026-08-14 | **#333 验收 · markLine 标签拉伸/遮挡修复**（非破坏性 · 签名零变更 · 内部实现）：标签从 SVG `<text>` 改为 HTML 覆盖层（`preserveAspectRatio="none"` 拉伸不再作用于文字；绘制顺序调整到最上层不被 area/折线遮挡；位置语义不变）。守卫测试 +2 → 全量全绿（tests/ 232/232）。详见 §6.5 |
| v1.17 | 2026-08-14 | **#334 series[].ownScale 系列独立刻度**（非破坏性 · 新可选字段 · 签名零变更）：每系列按自身 min-max（+6% padding）独立归一化铺满图高，量级差 100 倍不压平；ownScale 序列不参与共享域（yTicks/网格/markLine 仍以主序列域为准）；legend:true 时图例注明「各指标独立刻度」；与 yTicks/legend/tooltip/area 正交。守卫测试 +4 → 全量全绿（tests/ 236/236）。详见 §6.5 |
| v1.18 | 2026-08-14 | **#319 charts.line markPoint 峰谷点标注**（非破坏性 · 新可选字段 · 签名零变更）：契约 §6.5 参数表早已声明 `markPoint` 但无渲染实现，本次补齐——`true`/`{index|value, label?, color?}`，默认在主序列（items / series[0]）最大值点渲染高亮数据点 + 上方文字标注；index 按 items 索引（越界忽略）、value 按值匹配首个点；label 缺省 = 该点值走 format；标注文字贴边防裁剪（左右 18% 区域锚定内侧边缘，中间居中）；与 series/showValues/markLine/highlightLast 正交。守卫测试 +6 → 全量全绿（tests/ 242/242）。详见 §6.5 |
| v1.19 | 2026-08-14 | **#335 charts.line 置信带 band**（非破坏性 · 新可选参数 `band:{hi:[],lo:[]}` · 签名零变更）：主序列 hi/lo 区间半透明填充（fill-opacity 0.15，绘制在折线下方不遮挡）；hi/lo 与 items 等长、值可为 null 断点（任一侧 null → 该段断开）；hi/lo 值并入共享域计算（防区间超出裁剪）；域跟随主序列（ownScale 时跟随自身域）；不参与 tooltip/图例；缺省渲染逐字节不变。守卫测试 +6 → 全量全绿（tests/ 248/248）。详见 §6.5 |
| v1.20 | 2026-08-14 | **#340 charts.line markLine 竖线 xValue**（非破坏性 · 新可选字段 · 签名零变更）：`markLine:{xValue}` = 垂直里程碑线（X 轴位置）+ 顶部文字标注，与 `{value}`（水平阈值）按字段区分、可同传分别渲染；xValue = items 索引（越界忽略）或 label 字符串匹配；缺省标注文字 = 该点 label；线色走 `color`（缺省 #ff9500）；标注贴边防裁剪（同 markPoint 机制）；既有 `{value}` 行为零变更。守卫测试 +6 → 全量全绿（tests/ 254/254）。详见 §6.5 |
| v1.21 | 2026-08-14 | **#338 charts.line fillBetween 线间填充**（非破坏性 · 新可选参数 `fillBetween:{a,b,color?}` · 签名零变更）：a/b = series[] 索引，两线之间区域半透明填充（透明度对齐 areaOpacity，绘制在折线下方）；任一侧 null → 该段断开不填充；a/b 非数字/越界/相同/两系列长度不一致 → 直接报错；一次一组填充（不支持多组叠加）；缺省渲染逐字节不变。守卫测试 +6 → 全量全绿（tests/ 260/260）。详见 §6.5 |
| v1.22 | 2026-08-14 | **#341 charts.line 小缺口三能力**（非破坏性 · 新可选字段 · 签名零变更）：①items 每点 `anomaly:true` → 该点数据点染警示红（默认 #ff3b30）②`highlightPoints:'turns'|'crossings'` → 拐点（方向变化点）/交点（多序列线相交段）渲染圈选环（.hm-c-dot-hl）③`showValues:'edge'` 只标首尾有效点 + 密集标签碰撞避让（相邻中心距 <26 viewBox 单位跳过）。缺省渲染逐字节不变。守卫测试 +7 → 全量全绿（tests/ 267/267）。详见 §6.5 |
| v1.23 | 2026-08-14 | **#336 charts.bar 堆叠柱 stacked**（非破坏性 · 新可选参数 `stacked/segNames/stackMode` · 签名零变更）：定义**多值 item 结构单一真相源** `items:[{label, values:[v1,v2,...], color?}]`（#339 复用，禁止另立字段）——`stacked:true` 段纵向堆叠；`stackMode:'percent'`（缺省，柱内合计 100%）/`'absolute'`（相对全局最大合计）；每段独立颜色（colors 色板），`segNames` 图例 + 段级 tooltip；柱顶合计值走 showValues/format；缺 values/段值非数字/各 item 段数不一致 → 直接报错；缺省渲染逐字节不变。守卫测试 +6 → 全量全绿（tests/ 273/273）。详见 §6.5 |
| v1.24 | 2026-08-14 | **#339 charts.bar 分组双柱 grouped**（非破坏性 · 新可选参数 `grouped` · 签名零变更 · 原生阻塞解除）：复用 #336 定义的多值 item 结构（零新字段）——`grouped:true` 每列 N 根并排子柱（宽度均分，`.hm-c-gw` 包裹）；高度相对共享域（全域 max/min，对齐单柱语义）；每子柱独立颜色（colors 色板）+ `segNames` 图例；showValues 每子柱顶部数值标签；tooltip 按子柱命中（值 + 段名）；校验与 stacked 同源。缺省渲染逐字节不变。守卫测试 +6 → 全量全绿（tests/ 279/279）。详见 §6.5 |

## 1. 目录结构

```
公共组件/
  SKILL.md                 # Base Skill 定义（触发词/用法/资产清单）
  README.md                # 使用手册（接管线步骤/占位符规范/验收清单模板）
  CHANGELOG.md             # 版本变更记录（见 §8）
  assets/
    base.js                # P0+P1+P1.5 JS（唯一真相源）
    base.css               # token A 组 + 全部控件样式（唯一真相源）
    charts.js              # 图表组件（v1.3 新增 · v1.6 全参数化 · 七接口）
  injector.py              # 注入器（CLI + 硬拦截 + payload/CSS/图表注入 + 结构校验）
  docs/
    component-contract.md  # 本契约
    help-template-contract.md  # 参数化 HELP 模板契约
```

## 2. 唯一真相源声明

- **Base `assets/` 是公共组件的唯一真相源**——所有技能的公共 JS/CSS/图表一律以 Base 为准
- 各技能原实现（居家管家 `scripts/render/_shared.py`、饼干记账 `scripts/_shared_js.py`、备忘录 `script/_shared/clipboard.js`、各技能内联实现）在**对应技能迁移完成后退役**
- **迁移完成前**：公共组件的任何修改只允许发生在 Base，技能内文件只读（防止同源双写漂移）
- **SHARED_JS 全家桶处置（#288 核对结论）**：居家管家 `_shared.py` SHARED_JS 中 Base 已有等价物（esc/toast/copyText/buildDataText/buildLogText/actionBar 等）走 Base、图表（bar/line/progress）走 charts.js、metaHeader/remindersBlock 居家特定留技能侧——居家迁移完成后 SHARED_JS 整体退役
- **v1.2 领域无关声明**：Base 组件接口**不绑定任何技能领域**（不认 item/items/groups 等居家管家字段）——技能把领域数据组织成通用结构（snapshot），Base 只渲染通用结构。未来居家管家重构时，它的复制按钮作废，改按 v1.2 接口传参（用户 2026-08-11 拍板，高于一切）

## 3. 占位符标准

| 占位符 | 数量规则 | 用途 |
|---|---|---|
| `<!--INJECT-DATA-->` | **必须恰好 1** | 数据注入点（payload JSON） |
| `<!--SHARED-HELPERS-->` | **必须恰好 1**（硬拦截） | 公共 JS 注入点（base.js） |
| `<!--SHARED-CSS-->` | **必须恰好 1**（v1.2 新增，硬拦截） | 公共 CSS 注入点（base.css） |
| `<!--CHARTS-HELPERS-->` | 0 或 1（v1.3 正式版） | 图表组件注入点（charts.js，`--charts` 参数） |

**硬拦截语义**：INJECT-DATA 缺失/重复、SHARED-HELPERS 缺失/重复、SHARED-CSS 缺失/重复 → 渲染失败报错（防漂移机制）。

**豁免通道**：确无公共 JS/CSS 需求的模板（如纯静态展示页）必须**显式声明** `<!--NO-SHARED-->`（白名单式：缺省 = 必须注入）。豁免名单由 render 公共层维护并在实施审查中复核；不得用「注释掉占位符」等方式隐式豁免。

## 4. payload 信封契约

所有注入的数据遵循统一信封（Base 组件依赖的最小字段）：

```json
{
  "status": "ok",
  "message": "(可选，失败时必有)",
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
      "snapshot": { "title": "...", "summary": [...], "sections": [...] },
      "buttons": [ { "label": "...", "text": "...", "kind": "primary|red" } ]
    },
    "copy_log": { "thinking": "...", "data_structure": "...", "call_chain": "...", "timestamp": "...", "exception": "..." }
  }
}
```

- **copy_log 位置**：`data.copy_log`（顶层，兼容 `data.scene.copy_log`——base.js 两层都读）

- **必填**：`status`（'ok'）、`data.meta.command_cn`、`data.meta.occurred_at`、`data.scene`（对象）
- **可选**：`data.meta.skill_name`、`data.meta.wake_word`、`data.meta.skill_version`
- 注入器 **payload 结构校验**（`--strict-payload`）：缺必填字段 → error；关闭时仅 json 合法性校验（兼容存量技能过渡）

## 5. P0 冻结签名（v1.2 更新）

| 函数 | 签名 | 语义 |
|---|---|---|
| `esc(s)` | 字符串→转义 HTML | 防 XSS |
| `arr(v)` | 任意→数组 | 安全数组访问 |
| `val(v)` | 任意→HTML | null/空显示「未填写」 |
| `yes(v)` | 布尔→徽章 | 通过/未通过 |
| `validate(p)` | payload→{ok,msg} | 数据守门（status==='ok' + data 是对象） |
| `_fbCopy(s)` | 字符串→bool | execCommand fallback（内部） |
| `copyText(s, opts?)` | 字符串→void | v2 语义：clipboard + fallback + 双 toast，**不改按钮文字**；opts.silent 可静默。**v1.10（#328）**：opts.toast 自定义文案 + onOk/onFail 回调 —— 详见 §6.8 |
| `toast(msg, detail?, options?)` | 字符串→void | **通用提示控件**（v1.2 增强，见 §5.1） |

### 5.1 toast 通用提示控件（v1.8 堆叠模式 · #304 · 向后兼容）

```js
toast(msg, detail?, {
  icon: 'copy'|'ok'|'warn'|'danger'|'info'|emoji,  // 内置图标库或自定义 emoji（默认 'copy'=📋）
  badge: { text: '成功', type: 'ok'|'warn'|'danger' },  // 标题右侧状态徽章
  actions: [{ label: '撤销', onClick: fn }],             // 标题右侧快捷操作（最多 2 个）
  count: '5 条',                                         // 轻量计数（数据量/进度）
  lines: ['多行', '详情'],                               // 富详情：多行文本
  code: '错误堆栈...',                                   // 富详情：代码样式块
  timeout: 4500,                                         // 自动消失时长（默认 4500）
  maxStack: 5,                                           // 堆叠上限（默认 5; 栈容量 = 栈内各 toast maxStack 最大值）
})
```

- **向后兼容**：`toast(msg, detail)` 不带 options = 完全等价 v1.1 行为（调用方零改动）
- **堆叠模式（v1.8 · #304 用户拍板）**：同屏最多 N 条同时可见（N 默认 5）；老上旧下（新 toast 贴屏幕底部出现，旧的向上顶，间距 8px）；超 N 挤掉最旧（FIFO）；≤820px 视口上限自动收窄为 3；单条独立计时消失
- **无障碍**：`role="status" aria-live="polite"`
- 三态文案（08 表恒定）：已复制/粘贴给 AI · 复制失败/长按选择文本手动复制 · 请先勾选…
- 样式：Base 内部注入（深色毛玻璃 + 📋 + 知道了按钮 + ≤820px 全宽），技能零样式

## 6. P1+P1.5 契约（v1.2 重构）

### 6.1 snapshot 结构化接口（v1.2 核心 · 领域无关）

```js
buildDataText(p, format?) → 人类可读文本
buildLogText(p, format?) → 6 段日志文本
```

- **snapshot schema**（技能把领域数据组织成通用结构，Base 只渲染）：
```json
snapshot = {
  "title": "场景中文名",                     // 标题（Base 输出头时用）
  "summary": ["记录 5 条 · 覆盖 8h30m"],      // 关键指标行（行数不限）
  "sections": [                              // 明细分节（节数不限）
    { "heading": "分类统计", "rows": ["睡眠 7h30m", "工作 2h"] }
  ]
}
```
- **行脱敏**：row 可为字符串或 `{ text: "密码", sensitive: true }`（敏感字段复制时输出 **** 并提示）
- **format 参数**：`'text'`(默认,人类可读) | `'json'` | `'csv'`（v1.2 新增；08 规范 §3 复制数据格式选择）
- **结构校验（违规直接报错）**：title 非空字符串 + summary 数组 + sections 数组 + 每节含 heading/rows → 缺失/类型错 → **渲染失败报错**（Q7 用户拍板：违规直接报错）
- buildDataText 输出头：`【技能名 · 操作】` + 场景/时间行 + summary 行 + sections 分节
- buildLogText 6 段：①场景标识 ②AI 思考链 ③数据结构 ④调用链 ⑤时间戳版本 ⑥异常（读 data.copy_log，缺省字段显示「(未知)」）

### 6.2 复制按钮控件（v1.2 增强）

```js
copyText(s, opts?)          // opts.silent 静默复制（不弹 toast）; v1.10: opts.toast 文案 + onOk/onFail（见 §6.8）
actionBar(p, extra?, opts?) → HTML
```

- actionBar 输出：场景按钮（scene.buttons，kind: primary/red）+ **复制数据/复制日志 ghost 按钮**（独立一行，08 规范硬标准）
- **复制数据/复制日志 = Base 控件**（用户拍板）：按钮文本可配（默认「复制数据」「复制日志」）、复制内容由使用方决定（走 buildDataText/buildLogText）、参数校验拦不规范传参
- opts 增强：`{ preview: bool(点击前弹预览面板), formatMenu: bool(格式选择菜单), download: bool(导出文件) }`
- 按钮规范（08 规范）：≤3 色按功能区分；ghost = 白底+主色描边+主色文字胶囊、min-height 48px、独立一行；偶数一行 2 个

### 6.3 新控件（P0+P1 · v1.2 新增）

| 组件 | 签名 | 语义 |
|---|---|---|
| `formPrompt(fields, template)` | fields[] + prompt 模板→HTML | **P0**：用户填参数表单（#122 拍板：页内表单+实时预览+空值拦截，禁系统弹窗）。fields: [{key,label,type:'text'\|'number'\|'select',options?,default?,placeholder?}]；生成表单+实时预览+空值拦截+复制按钮 |
| `selectList(items, batchActions?, opts?)` | items[] → HTML | **P0**：勾选列表+批量操作+「本组已选 x/y」计数联动（2026-08-11 手机端拍板：文本不省略/批量进内容区/计数联动/激活色随语义）。支持单选行操作+全选。**v1.9（#327）**：items[].widget 行内控件（date/text/select）+ 读取接口 opts.onSubmit —— 详见 §6.7 |
| `confirm({title, detail?, danger?, onOk})` | 配置→对话框 | **P0**：危险操作二次确认。danger=true 红按钮+警示文案；点确认→onOk()，取消/遮罩→关闭 |
| `foldBox(title, contentHtml)` | 字符串→HTML | **P1**：折叠区（查看详情/原始数据），默认折叠，展开动画统一 |
| `statusBadge(status, text?)` | 'ok'\|'warn'\|'danger'\|'empty'→HTML | **P1**：状态徽章（语义色统一）。**v1.4 加固**：非法/未知 status 值白名单降级 `empty`（防无样式徽章）；text 缺省用语义默认（成功/警告/失败/无数据）；text 经 esc 防 XSS | 
| `emptyState({icon?, text, hint?, action?})` | 配置→HTML | **P1**：空状态（图示+文案+下一步建议）。**v1.4 加固**：icon/text/hint 一律 esc 防 XSS；`action` = **受信 HTML 透传**（调用方负责其内容安全，通常放按钮；如含用户数据必须先在调用方 esc） |
| `errorReceipt({message, retryPrompt?, data?, log?, payload?})` | 配置→HTML | **P1**：错误回执（08 规范 §6.1：错误描述+修正重试+复制数据/日志）。**v1.4 加固**：①`payload` = 数据信封（显式传入优先；兼容 `window.__hmPayload` 全局兜底）②`data`/`log` = 复制按钮内容字符串直传（显式优先，缺省从 payload 生成）③复制按钮渲染期生成文本存 `data-t`，onclick 仅 `copyText(this.dataset.t)`——**不依赖点击时环境，零注入面** ④payload 缺 `scene.snapshot` 时容错：不渲染复制数据/日志按钮，控件不抛错 ⑤布局：修正重试 primary wide 独立一行 + 复制数据/日志 ghost 一行 2 个（08 规范奇数按钮） |
| `smartSelect(inputEl, config)` | `<input>` + config → {getState, getValue} | **P1.5（v1.11 · #312）**：字段级「复用优先·新建其次」选择器（账户/分类/账本/运动类型等任何此类字段通用）。详见 §6.9 |

### 6.4 样式 token A 组 + 控件样式（base.css）

- token A 组 12 变量不变：`--fg/fg2/fg3/bg/card/line/blue/blue2/soft/ok/shadow`
- v1.2 新增控件样式：toast 徽章/操作/计数、formPrompt 表单、selectList 勾选、confirm 对话框、foldBox、statusBadge、emptyState、errorReceipt
- 全部样式唯一真相源在 base.css；技能零样式副本

### 6.5 图表组件（v1.6 · CHARTS-HELPERS · 全参数化）

```js
charts.bar(el, items[, opt])        // 柱状图
charts.line(el, items[, opt])       // 折线图
charts.donut(el, items[, opt])      // 环形图
charts.progress(el, pct[, opt])     // 进度条
charts.combo(el, {bars, lines}, opt) // 柱线组合（v1.6 新增）
charts.sparkline(el, items[, opt])  // 迷你趋势卡（v1.6 新增）
charts.gauge(el, pct[, opt])        // 仪表盘（v1.6 新增）
```

- **数据形状（统一）**：`items: [{label, value, color?}]`；**value 显式 null = 缺失断点（仅 line 支持，线段断开；`connectNulls:true` 时跨断点连线）**；其余非数字 → 结构校验报错
- **结构校验（v1.6 硬行为）**：items 非数组 / 元素缺 label / value 非法 → **直接抛错**（对齐 Base v1.2「违规报错」）；空数组 → emptyState 联动（合法场景）
- **空态联动**：空数组 → `emptyState`（存在则用之，否则内联兜底）；donut 合计为零同样走空态
- **connectNulls（v1.14 · #356）**：`line` 可选参数，默认 `false`（行为与 v1.13 逐字节一致）；`true` 时跨 null 断点连线——跳过缺失值直接连接相邻有效点，数据点仍只在有值日渲染，首尾 null 不向图外延伸，全 null 系列仍空路径；与 `smooth`/`step`/`area`/`series`/`avgLine` 正交可组合（area 跨 null 连续填充、avgLine 均线跨 null 连线）
- **yTicks（v1.15 · #333）**：`line` 可选参数，默认 `false`（行为与 v1.14 逐字节一致）；数字 = 刻度数量（收敛 2-6）——左侧刻度短线 + 刻度文字（HTML 覆盖层，不占位），刻度值 = 共享 Y 域（含 6% padding，尊重 yMin/yMax）均分，文字走 `format`（与 tooltip 同一格式化器，无 format 时数值收敛 2 位小数）；首尾刻度贴边防裁剪；与 `series`（共享域）/`grid:false`（短线独立渲染）/`tooltip`（pointer-events:none 不挡悬停）正交可组合；不改 X 轴标签策略、无交互
- **scatter（v1.25 · #337）**：新增接口 `charts.scatter(el, items[, opt])`——items: `[{x, y, label?}]`（x/y 双数值坐标，非法值直接报错；空数组 → emptyState）；**回归线**：线性最小二乘（n≥2 时渲染，`regression: false` 关闭，`regressionColor` 缺省 #ff3b30 虚线）；**Y 轴刻度**：复用 line 的 yTicks 机制（数字 2-6 / false 关闭；**scatter 缺省 4 条**——读轴是散点核心用途，与 line 默认关闭不同）；**X 轴标签**：`labels: 'edge'`（缺省，首尾）/ `'all'` / `'none'`；`format` 同其他接口（刻度/tooltip 同一格式化器）；`tooltip: true` 最近点命中（显示 label + x · y）；`animation` 点淡入；`height`/`color`/`dotSize` 可选；双端自适应沿用 line 语义（≤720px 点 8px）；坐标唯一性同 line（容器零 padding，viewBox 留白）
- **grouped（v1.24 · #339）**：`bar` 可选参数 `grouped: true`——复用 #336 多值结构（零新字段）：每列 N 根并排子柱（`.hm-c-gw` 包裹，宽度均分，gap 3px）；高度相对共享域（全域 max/min，对齐单柱语义）；每子柱独立颜色（`item.color` 或 `colors` 色板）；`segNames` 图例（legend:true）；`showValues` 每子柱顶部数值标签（9px 小字）；`tooltip:true` 按子柱命中（段名 + 值）；校验与 stacked 同源（缺 values/非数字/长度不一致报错）；与 stacked 互斥（同传时 stacked 优先）；缺省渲染逐字节不变
- **bar 多值 item 结构（v1.23 · #336 定义 · #339 复用）**：`bar` 多值模式共用结构——`items: [{label, values: [v1, v2, ...], color?}]`（values = 多段/多值数组，长度各 item 一致，值必须为数字，违规直接报错）；`segNames: [段名...]` 图例/段名（缺省「段1/段2…」）；每段颜色 = `item.color` 或 `colors` 色板逐段取色。**stacked（v1.23 · #336）**：`stacked: true` 段纵向堆叠；`stackMode: 'percent'`（缺省：柱内合计 100%）/ `'absolute'`（相对全局最大合计）；柱顶显示合计值（showValues/format）；段级 tooltip（`tooltip:true` 悬停列出各段值与占比）；不参与 yMin/yMax（percent 恒 0-100%）。**grouped（v1.24 · #339）**：见下方条目。缺省（不传 stacked/grouped）→ 既有单柱渲染逐字节不变
- **小缺口三能力（v1.22 · #341）**：`line` 新增三个可选能力——①**异常点变色**：items 每点 `anomaly: true` → 该点数据点染警示红（默认 #ff3b30，含光晕；缺省 false）；②**拐点/交点圈选**：`highlightPoints: 'turns'`（方向变化点，dy 符号反转，两端点不判）或 `'crossings'`（多序列线相交段，段两端差值符号反转即交，标记段右端点）→ 渲染圈选环（`.hm-c-dot-hl`，透明大环，缺省 null）；③**首尾数值标签 + 碰撞避让**：`showValues: 'edge'` 只标首尾有效点；`showValues: true` 密集数据相邻标签中心距 <26 viewBox 单位时跳过（静态避让，无拖拽交互）；三项缺省 → 既有渲染逐字节不变
- **fillBetween（v1.21 · #338）**：`line` 可选参数，默认 `null`（行为与 v1.20 逐字节一致）；`fillBetween: {a, b, color?}`——a/b = `series[]` 索引（数字，越界/相同/非数字/两系列 items 长度不一致 → 直接报错），两线之间区域半透明填充（透明度 = `areaOpacity`，绘制在折线路径之前不遮挡；`color` 覆盖填充色，缺省主色）；任一序列该点 `null` → 该段断开不跨空填充；一次一组填充（不支持多组叠加、不做上/下侧语义）；与 band/markLine/series 正交
- **markLine 竖线（v1.20 · #340）**：`line` 的 `markLine` 支持竖线类型——`markLine: {xValue: <items 索引或 label>, label?, color?}`：xValue = X 轴位置（数字 = items 索引，越界忽略不报错；字符串 = 按 items label 精确匹配）；渲染垂直虚线（贯穿绘图区）+ 顶部文字标注（缺省标注文字 = 该点 label，可 `label` 覆盖；线色 `color` 缺省 #ff9500）；标注贴边防裁剪（点落左右 18% 区域锚定内侧边缘，中间居中）；与既有 `{value}`（水平阈值）按字段区分，可同传分别渲染横/竖线；既有 `{value}` 行为零变更（逐字节回归）；markPoint（峰谷点标注）= #319 已实现，不属本参数
- **band（v1.19 · #335）**：`line` 可选参数，默认 `null`（行为与 v1.18 逐字节一致）；`band: {hi: [], lo: []}`——主序列（items / series[0]）置信带区间渲染：hi/lo 与 items 等长（不等 → 直接报错），每点值可为 `null` 断点（任一侧 null → 该段断开不填充）；区间半透明填充（`fill-opacity 0.15`，绘制在折线路径之前不遮挡）；hi/lo 值并入共享 Y 域计算（防区间超出裁剪，显式 yMin/yMax 优先）；ownScale 主序列时跟随自身域；不参与 tooltip/图例；与 yTicks/connectNulls（区间按自身 null 语义，不随 connectNulls 跨空）/markLine 正交
- **markPoint（v1.18 · #319）**：`line` 可选参数，默认 `false`（行为与 v1.17 逐字节一致）；`true` 或对象 `{index|value, label?, color?}`——在主序列（items / series[0]）指定点渲染高亮数据点（白边 + 阴影圈）+ 上方文字标注：`true`/缺字段 = 默认取主序列最大值点；`{index:n}` = 按 items 索引（越界忽略不报错）；`{value:v}` = 按值匹配首个点；`label` 覆盖标注文字（缺省 = 该点值走 `format`）、`color` 覆盖标注色（缺省 = 序列色）；标注文字贴边防裁剪（点落左右 18% 区域 → 锚定内侧边缘左对齐/右对齐，中间 → 居中，任意长度不裁出界）；与 series/showValues/markLine/highlightLast 正交；不影响 tooltip/动画
- **series[].ownScale（v1.17 · #334）**：`series` 条目可选字段，默认 `false`（行为与 v1.16 逐字节一致）；`true` 时该系列按自身 min-max（+6% padding，忽略 yMin/yMax）独立归一化 → 铺满图高，量级差 100 倍的系列同图不压平（对齐旧自绘「各自独立刻度」语义）；ownScale 序列**不参与共享域**（yTicks/网格/markLine 仍以非 ownScale 序列域为准，极端量级不污染主轴刻度）；`legend:true` 且存在 ownScale 序列时图例末尾追加「各指标独立刻度」注记（虚线样式）；与 yTicks/legend/tooltip/area（跟随所属系列域）正交；单序列 ownScale 无行为差异；不做第三轴/对数轴，`combo.y2` 语义不动
- **全参数（不传 = 默认）**：

| 接口 | 参数 |
|---|---|
| `line` | `height/compact/width` · `color/lineWidth/dashed` · `smooth`（Catmull-Rom，点在线）· `showDots/dotSize/dotStyle` · `area/areaOpacity` · `labels('edge'/'all'/'none'/'select')` · `showValues/labelRotate` · `yMin/yMax/grid` · `format` · `tooltip` · `markLine{value,label}`（标签为 HTML 覆盖层 · v1.16）· `markPoint` · `step` · `animation` · `series[{name,items,color,dashed,smooth,area,ownScale}]`（ownScale=独立刻度 · v1.17）· `avgLine(n)` · `legend` · `highlightLast` · `onclick/ondrill` · `emptyText` · `connectNulls`（跨缺失断点连线，默认 false · v1.14）· `yTicks`（Y 轴刻度数量 2-6 / false 关闭，默认 false · v1.15） |
| `bar` | `format` · `colors/singleColor` · `height/compact` · `labels('all'/'none'/'select')` · `showValues` · `yMin/yMax/grid` · `tooltip/animation` · `onclick` |
| `donut` | `format` · `colors` · `size/ringWidth` · `legend('right'/'bottom'/'none')` · `showPercent` · `centerLabel/centerValue` · `animation` |
| `progress` | `color/gradient` · `height(轨道px)` · `showPct` · `animation`（pct 非数报错，超界收敛 0~100） |
| `combo` | `{bars:[{label,value}], lines:[{label,value}]}`（同长同 label）· `barColor/lineColor` · `format` · `height` · `legend` · `animation` · `onclick` |
| `sparkline` | `color/width/height` · `showValue` · `format`（涨绿跌红） |
| `gauge` | `label/color/size` · `format` · `animation`（pct 非数报错） |

- **坐标唯一性（v1.6 修复的根因）**：容器**零 padding**，留白进 SVG viewBox——数据点 overlay 与折线共享同一坐标系，物理对齐（实测误差 <0.2px）；`vector-effect="non-scaling-stroke"` 防拉伸线宽变形
- **双端自适应（≤720px）**：柱标签两行、图例下沉（donut）、折线高度 150、数据点 8px——手机独立 UI
- **语义色**：默认 token A 组（`var(--blue,#007aff)` 带 fallback）；donut 内置 10 色 Apple 语义色板；series 逐条取色板
- **自包含**：本地 esc 兜底，可独立注入；样式自注入（`hm-charts-style`）
- **白名单例外**：卡路里 `weight_volatility_v2` canvas 留技能自营，走公共层 ISSUE 审批

### 6.6 复合形态（v1.6 新增）

「无法统一的」不是形态参数，而是**组合**——新形态独立成组件，共享同一 token/空态/双端规则：

| 组件 | 用途 | H3 场景 |
|---|---|---|
| `combo` | 柱=量 + 线=趋势/目标 | 每日摄入(柱)+累计趋势(线)、每周录入(柱)+均线(线) |
| `sparkline` | 迷你趋势卡（无坐标轴 + 首尾值 + 涨绿跌红） | 概览页每个分类一个小趋势 |
| `gauge` | 弧形进度 + 目标刻度 | 单指标达成（今日目标 80%） |

### 6.7 selectList 行内控件（v1.9 · #327）

**一句话**：items 条目可声明一个行内输入控件，与勾选行/批量操作/计数联动共存；批量回调与 `opts.onSubmit` 可读取行内输入值。**非破坏性**：未声明 `widget` 的既有调用渲染输出与行为完全不变（守卫测试逐字节回归 outerHTML）。

**widget 字段（items[].widget，新可选）**：

```js
items: [{
  id, title, sub?, group?,
  widget?: {                       // v1.9 · 单条目最多 1 个
    type: 'date' | 'text' | 'select',
    key:  '读取时使用的字段键',     // 缺省 'w'+行号
    label?: '控件标题',             // esc
    placeholder?: '占位提示',       // text/date 用, esc
    options?: [ '原始值' | { value, label } ]   // select 用; 缺省渲染「请选择」占位
  }
}]
```

- **宽容渲染（不报错）**：非法 `type` 降级 `text`；`key` 缺省 `'w'+行号`；`options` 元素可为字符串（value=label）或 `{value,label}` 对象
- **共存**：控件渲染在行内（`.sl-widget`），勾选/批量/计数全部照常；**计数联动只随勾选态，控件值变化不干扰**「本组已选 x/y」
- **安全**：label/placeholder/option value+label 渲染一律 `esc`，零注入面

**读取接口（v1.9 选定形态 = `opts.onSubmit` 等价形式，非返回对象）**：

```js
selectList(items, batchActions?, {
  onSubmit(selectedIds, values){}   // 读取接口
})
```

- **触发时机**：任意批量操作按钮点击后触发（与按钮自身 `onClick` 并列调用；无勾选时与既有拦截一致，不触发）
- **`values` = 全部行内值**：`{ [id]: { [key]: value } }`——含**未勾选条目**；无 widget 条目不出现；**未填统一归一 `null`**（date/text 空输入、select 占位项）
- **id 统一字符串键**（与勾选 idList 一致，来自 DOM `data-id`）

**批量回调增强**：`batchActions[].onClick(ids, values)` 第二参 `values` = **勾选条目对应**的行内值 `{ [id]: { [key]: value } }`（只读勾选条目；未填 → null 不报错；未勾选条目不参与）。旧回调只取第一参，零影响。

**样式**：`.sl-widget*` 走 token A 组（base.css v1.9），技能零样式副本。

### 6.8 copyText 反馈钩子（v1.10 · #328）

**一句话**：`copyText` 支持自定义成功/失败 toast 文案与回调钩子，对齐 08 规范「文案由各技能按场景自设计」（2026-08-13 修订）。**非破坏性**：未传新选项时行为与 v1.9 逐字一致（守卫测试断言 toast 文案）。

```js
copyText(s, {
  silent: true,                          // v1.1 既有: 不弹 toast
  toast: {                               // v1.10 新增: 自定义反馈文案（缺省回落默认）
    ok:   { msg: '已存剪贴板', detail: '发给 AI 执行', icon: '🎉' },
    fail: { msg: '复制失败啦', detail: '请长按手动复制', icon: '😭' }
  },
  onOk:   function(){},                  // v1.10 新增: 复制成功（主路径或兜底）触发
  onFail: function(){},                  // v1.10 新增: 最终失败（剪贴板不可用且兜底失败）触发
})
```

- **文案覆盖规则**：`toast.ok/fail` 只覆盖提供的字段（`msg`/`detail`/`icon`），未提供字段回落默认——ok 默认 `已复制/粘贴给 AI`（无图标），fail 默认 `复制失败/长按选择文本手动复制` + `badge:{text:'失败',type:'danger'}`（失败徽章恒在，不可移除）
- **回调语义**：`onOk` 在复制成功（`navigator.clipboard` 主路径或 `_fbCopy` 兜底）必触发；`onFail` 在最终失败必触发；两者互斥
- **silent 组合**：`silent:true` 时不弹 toast，但回调仍触发（08 规范定制文案场景的标准做法：silent + 自定义乐观 toast + onFail 纠错）
- **空串**：`copyText('')` 直接 return，无 toast 无回调（既有语义）
- **安全**：文案经 `toast` 内部 `esc` 转义（既有）

### 6.9 smartSelect 选择器组件（v1.11 · #312 · 立项 #320）

**一句话**：字段级「复用优先·新建其次」选择器——优先复用已有项，其次新建；AI 推断 / AI 推荐新建辅助决策；组件零领域词，label/选项/徽章文案/来源说明/prompt 拼装全部由外部 config 注入。与 copyText/actionBar 同级 Base 组件，注入走 SHARED-HELPERS / SHARED-CSS 管线（入 base.js / base.css，注入器零改动）。**非破坏性**：新增全局函数 + 新增样式，既有接口零变更。

```js
smartSelect(inputEl, config) → { getState, getValue }
```

- **config（snake_case，与数据契约 `form.selector.<fieldKey>` 对齐）**：

```json
{
  "options": [{"name": "美团", "disabled": false}, {"name": "支付宝", "disabled": true}],
  "inferred": "美团",
  "recommended_new": "美团月付",
  "initial": {"name": "美团", "source": "inferred"},
  "texts": { "candTitle": "...", "search": "...", "newPlaceholder": "...", "newButton": "＋ 新建",
             "emptyButton": "留空(不填)",
             "badgeInferred": "AI 推断", "badgeRecommendedNew": "AI 推荐·新建",
             "badgeExisting": "已有", "badgeHistory": "历史", "badgeCustom": "自定义",
             "cardSrc": { "inferred": "...", "recommended_new": "...", "existing": "...",
                          "history": "...", "custom": "...", "empty": "..." } },
  "theme": { "brand": "#123a63", "brandSoft": "#e9f0f7", "onBrand": "#ffffff", "deep": "#0b1f3b" }
}
```

- **行为契约**（#307 形态定稿）：chips 平铺候选 + 顶部「已选卡片」（SVG ✓ 圆形图标 + 来源徽章）；初始选中优先级 = **AI 推断 > 历史预填 > AI 推荐新建 > 空**（`initial` 缺省时组件自行推导；无推断时默认选中「AI 推荐新建」项）；用户可改选已有 / 自定义新建 / 留空；**绝不静默填错**；新建值以 chip 加入候选区（「自定义」徽章 + 选中态），重名自动选中已有项；相似提示组件内置；停用态划线置灰不可点；搜索过滤候选；主题色默认账本藏蓝 `#123A63`（CSS 变量每实例可覆盖）
- **候选区折叠（v1.12 · 实测反馈）**：`maxChips`（缺省 8；0/负数/非数字 = 不折叠）——候选超过阈值时只显前 maxChips 个 + 「展开全部(N)」/「收起」按钮；**初始选中项在折叠区时保可见**（提前进可见区，避免「选了但看不见」）；**搜索输入全量过滤**（跳过折叠，折叠区候选可搜出）；搜索框内容跨渲染保持；展开态点选后保持展开。账户/账本等小候选集（<10 个）不受影响
- **降级**：`options` 缺省空数组 **且** 无 `inferred` / `recommended_new` / `initial` → 组件降级为普通输入（T4 决议：键空 → options 空数组 → 降级），输入值回填 `source=custom` / 空 `source=empty`
- **回填协议**（组件→上层，**prompt 由上层 buildPrompt 自拼，组件零 prompt 知识**）：

| 通道 | 值 |
|---|---|
| `input.value` | 最终选中值（留空 = 空串） |
| `input.dataset.source` | 来源（白名单） |
| `input.dataset.new` | `'1'` = 选了新建（recommended_new/custom） |
| 事件 | `change`（bubbles）每次选中触发；`smartSelect(el).getState()/getValue()` 可选 |

- **source 白名单**：`inferred | recommended_new | existing | history | custom | empty`（违规直接报错）
- **守卫**：结构校验违规直接报错（对齐 Base v1.2 原则）——config 非对象 / options 非数组 / option 缺 name / disabled 非布尔 / inferred、recommended_new 非字符串 / initial 缺 name 或 source 不在白名单 / inputEl 非 `<input>` → `throw new Error('smartSelect 违规: …')`；类名全 `ss-` 命名空间（**封装纪律**，禁止裸类名 plain/ai/new/sel/dis/ic/nm/src/empty 等——宿主同名规则会命中组件，实证 bug：宿主 `.plain{width:100%}` 命中徽章类把已选卡片文本区挤成 1 字宽）；全部动态文本经 `esc` 零注入面；候选 chip 用 `<button type="button">`（无障碍 + 键盘可用）
- **样式**：`.ss-*` 走 base.css（token A 组 + 主题 CSS 变量），技能零样式副本；手机 ≤820px 独立适配（新建行纵向、触控高度）

## 7. 注入器接口（v1.3）

```bash
python injector.py <模板.html> --payload <数据.json> [--output <输出.html>] [--js <资产.js>] [--css <资产.css>] [--charts <图表.js>] [--strict-payload]
```

- 校验：INJECT-DATA 恰 1 / SHARED-HELPERS 恰 1 / **SHARED-CSS 恰 1**（v1.2 新增）/ CHARTS ≤1
- 注入顺序：SHARED(JS) → SHARED-CSS → CHARTS → DATA
- `--css`：base.css 注入点（缺省 = assets/base.css）；NO-SHARED 豁免时 CSS 同样豁免
- `--charts`（v1.3 正式化）：charts.js 注入点（缺省 = 不注入）；模板含 `<!--CHARTS-HELPERS-->` 时替换为资产内容
- payload：json 合法性必校验；`--strict-payload` 时按 §4 信封结构校验
- 输出：写文件 + 打印结果 JSON（status ok/error）

## 8. 版本与变更机制

- Base 资产带版本号（当前 v1.10），变更记入 `CHANGELOG.md`
- **签名变更 = 破坏性变更**：必须全技能同步 + 一次性完成 + 变更记录；不允许「新签名 + 旧签名并存」跨版本漂移
- 非破坏性变更（内部实现/样式细节）：可独立发布，CHANGELOG 记录
- 任何变更先开公共层 ISSUE（总纲 09 §92），review 后实施
- v1.2 破坏性变更说明：buildDataText/buildLogText 从「居家管家字段绑定」重构为「snapshot 通用结构」——**当前零消费方**（作息管家是第一个），重构零成本；未来居家管家迁移按 v1.2 接口传参
- v1.3 非破坏性说明：新增 charts.js 资产（新增接口，既有接口零变更）——居家管家/饼干记账图表迁移属于 6 张技能重构票，迁移完成前技能内图表实现冻结

## 9. 与既有规范的关系

- **#248/08-HTML交互规范.md** = prompt 参数格式 / 复制数据日志 / 按钮颜色布局的规范本体（Base 对齐；用户提示「不一定都对」→ 落地时对抗式审查逐条验证）
- **T3 草案（#263）** = 本契约的盘点基础
- **居家管家 render/__init__.py** = 注入器范式（迁移完成后退役，见 §2）
- **#269 试点用户拍板** = v1.2 接口定稿依据（Grill 收口 2026-08-11：snapshot 结构化 / toast 通用化 / 复制按钮控件化 / 校验违规报错 / 新控件 P0+P1 / CSS 注入）

---
提交信息：
- 提交者: Mavis
- 提交时间: 2026-08-11 18:0x
- 任务上下文: #269 作息管家试点 Grill 收口——用户拍板 Base v1.2 全量落地（snapshot 领域无关接口 / toast 通用提示 4 形态 / 复制按钮控件化 / 新控件 P0+P1 / CSS 注入管线）
