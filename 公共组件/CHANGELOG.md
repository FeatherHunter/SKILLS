# CHANGELOG

> Base Skill 公共组件版本变更记录。**签名变更 = 破坏性变更**（必须全技能同步 + 一次性完成 + 本文件记录）;非破坏性变更（内部实现/样式细节）可独立发布。任何变更先开公共层 ISSUE（总纲 09 §92）。

## v1.24（2026-08-14 · charts.bar 分组双柱 grouped · #339）

**charts.bar 新增可选参数 `grouped`**（非破坏性 · 新可选参数 · 签名零变更 · #336 原生阻塞解除）。

- **复用 #336 多值 item 结构（零新字段）**: `items: [{label, values: [v1, v2, ...]}]`——本票只新增 `grouped` 渲染模式（triage 拍板「禁止另立字段」遵守）
- **`grouped: true`（每列 N 根并排子柱）**: 宽度均分（.hm-c-gw 包裹, gap 3px）; 高度相对共享域（全域 max/min, 对齐单柱语义）——实做 vs 计划对比（goal_progress / exercise_review combo 近似）恢复
- 每子柱独立颜色（item.color 或 colors 色板）+ `segNames` 图例; showValues 每子柱顶部数值标签（9px 小字）; tooltip 按子柱命中（段名 + 值）
- 校验与 stacked 同源（缺 values/非数字/长度不一致 → 报错）; 与 stacked 互斥（同传时 stacked 优先）
- **向后兼容**: 不传 grouped → 既有单柱渲染逐字节一致（显式断言 innerHTML 全等）
- 契约 §6.5 grouped 条目 + §0 版本记录 + CHANGELOG 同步; 守卫测试 +6 → 全量全绿

## v1.23（2026-08-14 · charts.bar 堆叠柱 stacked · #336）

**charts.bar 新增可选参数 `stacked/segNames/stackMode`**（非破坏性 · 新可选参数 · 签名零变更；缺省行为逐字节不变）。

- **多值 item 结构（单一真相源, 本票定义, #339 复用）**: `items: [{label, values: [v1, v2, ...], color?}]`——段值数组, 各 item 长度一致, 值必须为数字（缺 values/非数字/长度不一致 → 直接报错）
- **`stacked: true`（段纵向堆叠）**: `stackMode: 'percent'`（缺省: 柱内合计 100%）/ `'absolute'`（相对全局最大合计）——三大营养素每日占比堆叠柱（nutrition_analysis macro3 div 占比条近似）恢复
- **每段独立颜色**: item.color 或 `colors` 色板逐段取色; `segNames` 图例（legend:true）+ 段级 tooltip（悬停列出各段值与占比）
- **柱顶合计值**: showValues 显示合计（走 format）; 动画/双端自适应沿用既有语义
- **向后兼容**: 不传 stacked/grouped → 既有单柱渲染逐字节一致（显式断言 innerHTML 全等）
- 契约 §6.5 bar 多值结构 + §0 版本记录 + CHANGELOG 同步; 守卫测试 +6 → 全量全绿

## v1.22（2026-08-14 · charts.line 小缺口三能力 · #341）

**charts.line 三个小能力落地**（非破坏性 · 新可选字段 · 签名零变更；缺省行为逐字节不变）。

1. **异常点变色**: items 每点 `anomaly: true` → 该点数据点染警示红（默认 #ff3b30 + 光晕）——超标数据点（如卡路里超目标）提示恢复（calorie_trend / long_trend）
2. **拐点/交点圈选**: `highlightPoints: 'turns'`（方向变化点）/ `'crossings'`（多序列线相交段）→ 圈选环（.hm-c-dot-hl 透明大环）——health_report 拐点/双线交点视觉恢复
3. **首尾数值标签 + 碰撞避让**: `showValues: 'edge'` 只标首尾有效点; `showValues: true` 密集数据相邻标签中心距 <26 viewBox 单位时跳过（静态避让）——weight_compare / exercise_review 首尾标注恢复、30+ 点标签不再重叠
- **向后兼容**: 三项缺省时渲染与 v1.21 逐字节一致（全量回归通过; 稀疏数据 showValues:true 标签全保留不过度跳标）
- 契约 §6.5 三能力条目 + §0 版本记录 + CHANGELOG 同步; 守卫测试 +7 → 全量全绿

## v1.21（2026-08-14 · charts.line fillBetween 线间填充 · #338）

**charts.line 新增可选参数 `fillBetween: {a, b, color?}`**（非破坏性 · 新可选参数 · 签名零变更；缺省 `null` 行为逐字节不变）。

- **`fillBetween: {a, b}`**: a/b = series[] 索引, 两线之间区域半透明填充——摄入 vs 消耗双线缺口阴影（热量缺口可视化, calorie_deficit 迁移时省略的填充）恢复
- **断点语义**: 任一序列该点 null → 该段断开不填充（与断线语义一致）
- **校验**: a/b 非数字/越界/相同/两系列 items 长度不一致 → 直接报错（对齐 Base 违规报错）; 一次一组填充, 不支持多组叠加
- **透明度对齐 `areaOpacity`**（缺省 0.12）; `color` 覆盖填充色（缺省主色）; 绘制在折线路径之前不遮挡
- **向后兼容**: fillBetween 未传时渲染与 v1.20 逐字节一致（显式断言 innerHTML 全等）
- 契约 §6.5 fillBetween 条目 + §0 版本记录 + CHANGELOG 同步; 守卫测试 +6 → 全量全绿

## v1.20（2026-08-14 · charts.line markLine 竖线 xValue · #340）

**charts.line 的 `markLine` 扩展竖线类型**（非破坏性 · 新可选字段 · 签名零变更；既有 `{value}` 行为逐字节不变）。

- **`markLine: {xValue, label?, color?}`**: 垂直里程碑线（X 轴位置）+ 顶部文字标注——weight_history 最高/最低体重点、里程碑日期竖线（原图例徽章近似）恢复语义
- **xValue 匹配**: 数字 = items 索引（越界忽略不报错）; 字符串 = 按 items label 精确匹配; 缺省标注文字 = 该点 label（可 label 覆盖）
- **与 `{value}` 按字段区分**: 可同传分别渲染横线+竖线; 线色走 `color`（缺省 #ff9500）
- **贴边防裁剪**: 标注文字点落左右 18% 区域锚定内侧边缘（同 markPoint 机制, 最左/最右竖线不裁出界）
- **向后兼容**: 未传 markLine 或仅传 `{value}` 时渲染与 v1.19 一致（回归通过）
- 契约 §6.5 markLine 条目 + §0 版本记录 + CHANGELOG 同步; 守卫测试 +6 → 全量全绿

## v1.19（2026-08-14 · charts.line 置信带 band · #335）

**charts.line 新增可选参数 `band: {hi: [], lo: []}`**（非破坏性 · 新可选参数 · 签名零变更；缺省 `null` 行为逐字节不变）。

- **`band: {hi, lo}`（置信带/误差带）**: 主序列（items / series[0]）hi/lo 区间渲染半透明填充（`fill-opacity 0.15`）——预测报告的置信区间恢复可视化（predict_report 迁移时省略的区间）
- **等长校验**: hi/lo 必须与 items 等长（不等 → 直接报错，对齐 Base 违规报错）；每点值可为 null 断点（任一侧 null → 该段断开不跨空填充）
- **域并入**: hi/lo 值并入共享 Y 域计算（区间超出主线范围不裁剪；显式 yMin/yMax 优先）；ownScale 主序列时区间跟随自身域
- **不遮挡**: 绘制在折线路径之前（DOM 顺序在主线之下）；不参与 tooltip/图例
- **向后兼容**: band 未传时渲染与 v1.18 逐字节一致（显式断言 innerHTML 全等）
- 契约 §6.5 band 条目 + §0 版本记录 + CHANGELOG 同步; 守卫测试 +6 → 全量全绿

## v1.18（2026-08-14 · charts.line markPoint 峰谷点标注 · #319）

**charts.line `markPoint` 参数补齐实现**（非破坏性 · 新可选字段 · 契约 §6.5 参数表早已声明该参数但无渲染代码, 本次真正实现; 缺省 false 行为逐字节不变）。

- **`markPoint: true`**: 默认在主序列（items / series[0]）最大值点渲染高亮数据点（白边 + 阴影圈）+ 上方文字标注（标注文字 = 该点值, 走 `format`）
- **`{index: n}`**: 指定 items 索引点（越界忽略不报错）; **`{value: v}`**: 按值匹配首个点
- **`{label, color}` 覆盖**: 自定义标注文字 / 标注色（缺省 = 序列色）
- **贴边防裁剪**: 点落左右 18% 区域时标注文字锚定内侧边缘（左对齐/右对齐）, 中间区域居中——任意长度标注不裁出界（对齐饼干记账旧实现 text-anchor 贴边经验, #300 验收修复 91b1a1a）
- **正交**: 与 series（作用于主序列）/ showValues / markLine / highlightLast 可组合; 不影响 tooltip / 动画
- **向后兼容**: markPoint 未传/false 时渲染与 v1.17 逐字节一致（显式断言 innerHTML 全等）
- 契约 §6.5 markPoint 条目 + §0 版本记录 + CHANGELOG 同步; 守卫测试 +6 → 全量全绿

## v1.17（2026-08-14 · charts.line 系列独立刻度 series[].ownScale · #334）

**charts.line 新增可选参数 `series[].ownScale: true`**（非破坏性 · 新可选字段 · 签名零变更；缺省行为逐字节不变）。

- **`ownScale: true`（每系列独立归一化）**: 该系列按自身 min-max（+6% padding, 忽略 yMin/yMax）独立映射 → 各自铺满图高——量级差 100 倍的系列（如摄入 kcal 数千 vs 运动 kcal 数百）同图不再压平，形状/幅度各自可读（对齐旧自绘语义「各自 min-max 独立刻度」）
- **不污染主轴**: ownScale 序列**不参与共享域**——yTicks/网格/markLine 仍以主序列（非 ownScale 序列）域为准，极端量级序列不会把主轴刻度撑爆
- **图例注明**: `legend:true` 且存在 ownScale 序列时，图例末尾追加「各指标独立刻度」注记（虚线样式区分）
- **正交**: 与 yTicks（刻度 = 非 ownScale 序列域）/ legend / tooltip / area（跟随所属系列域）可组合; 单序列 ownScale = 无行为差异（本就按自身域铺满）
- **向后兼容**: 未传 ownScale 时共享域计算与 v1.16 逐字节一致（全量回归通过）; 不做第三轴/对数轴（#334 范围边界）, `combo.y2` 语义不动
- 契约 §6.5 参数表 + ownScale 条目 + §0 版本记录 + CHANGELOG 同步; 守卫测试 +4（铺满图高/不污染主轴刻度/图例注记/单序列无差异）→ 全量全绿（tests/ 236/236）

## v1.16（2026-08-14 · markLine 标签拉伸/遮挡修复 · #333 验收发现）

**charts.line markLine 标签渲染修复**（非破坏性 · 签名零变更 · 内部实现修复）。

- **现象**：markLine 标签为 SVG `<text>`，在 `preserveAspectRatio="none"` 非等比拉伸下被压扁拉胖（横向 ×2.2 / 纵向 ×1.8）；且绘制顺序在折线/面积路径之前，被 area 填充和折线遮挡（#333 验收演示 ⑩ 用例用户实测发现）
- **修复**：标签改为 **HTML 覆盖层**（`<i class="hm-c-markline-t">`，与 yTicks/showValues 同机制）——文字不经过 viewBox 拉伸永远清晰；最后插入（z 序在 area/线/刻度之上）不被遮挡；`pointer-events:none` 不挡 tooltip 悬停
- **位置语义不变**：仍右对齐到阈值线右端（x=_W-_P-2），位于线上方 4 单位
- 守卫测试 +2（标签不在 SVG 内 + 计算字号 10px / area 共存时标签最后插入不被遮挡）→ 全量全绿（tests/ 232/232）

## v1.15（2026-08-14 · charts.line 新增 Y 轴刻度文字 yTicks · #333）

**charts.line 新增可选参数 `yTicks`**（非破坏性 · 新可选参数 · 签名零变更；默认 `false` 行为逐字节不变）。

- **`yTicks: 4`（数字 = 刻度数量, 收敛 2-6; 传 `false`/不传 = 关闭）**: 渲染左侧刻度短线（SVG, x=_P 起 5 单位）+ 刻度文字（HTML 覆盖层, 不占位 → 坐标唯一性与既有几何零变化）
- **刻度值域 = 当前共享 Y 域（含 6% padding, 尊重 yMin/yMax）均分**——最上/最下刻度即 padded 域两端, 首尾文字贴边防裁剪（均落在 svg 区上下界内, 极端值全 0/全相同值不报错）
- **刻度文字走 `format` 参数**（与 tooltip 同一格式化器）; 无 format 时数值先收敛 2 位小数
- **正交**: 与 `series`（共享域刻度）/ `grid:false`（刻度短线独立于网格仍渲染）/ `tooltip`（文字 pointer-events:none 不挡悬停）可组合; 不做 X 轴标签策略改动、无交互
- **向后兼容**: `yTicks` 未传/`false` 时渲染与 v1.14 逐字节一致（守卫显式断言 innerHTML 全等）; 顺带修正 charts.js 头注释版本滞留（v1.4 → v1.15, #331 附带登记）
- 契约 §6.5 参数表 + yTicks 条目 + §0 版本记录 + CHANGELOG 同步; 守卫测试 +9 → 全量全绿（tests/ 230/230 · test_components.py 170/170）

## v1.14（2026-08-14 · charts.line 缺失值连线 connectNulls · #356）

**charts.line 新增可选参数 `connectNulls`**（非破坏性 · 新可选参数 · 签名零变更；默认 `false` 行为逐字节不变）。

- **`connectNulls: true`**: 跨 null 断点直接连接相邻有效点（跳过缺失值）——稀疏采样指标（体重/体脂/围度等每周 2-3 次记录）趋势连续可见; 数据点（dot）仍只在有值日渲染（缺值日无 dot）; 首尾 null 不向图外延伸; 全 null 系列仍空路径（不报错）
- **正交可组合**: 与 `smooth`（单段平滑跨空连续）/ `step`（阶梯跨空连续）/ `area`（跨 null 连续填充, 跟随同一开关, 不新增第二参数）/ `series`（每序列独立生效）/ `avgLine`（均线跨 null 连线, 滑动窗口内无有效值处仍产出 null）均可组合
- **向后兼容**: `connectNulls` 未传或 `false` 时路径构造与 v1.13 逐字节一致（既有 `test_line_missing_value_breaks` 等回归通过）
- 契约 §6.5 参数表 + §0 版本记录（含补录 v1.13 漏记条目）+ CHANGELOG 同步; 守卫测试 +9（连线/回归逐字节/首尾 null/全 null/组合六项）→ 全量全绿（tests/ 221/221 · test_components.py 161/161）

## v1.13（2026-08-14 · line 动画断线修复 · #317 验收二轮）

**charts.line 动画残留导致中段断线**（非破坏性 · 签名零变更 · 内部实现修复）。

- **现象**：所有 `charts.line`（animation 默认 true）页面出现"点与点之间断线"——线只画前半段，中段 40%+ 消失，尾段又出现
- **根因**：动画实现 `p.style.strokeDasharray = getTotalLength()`（SVG 用户单位长度）写入 CSS style，浏览器按**屏幕像素**解释；而 svg 是 `preserveAspectRatio="none"` 非等比拉伸（viewBox 320×110 → 屏幕 690×198，X 方向 2.16 倍）→ dash 图案长度与路径实际屏幕长度不匹配：dash 只覆盖路径前 ~47%，中段落入 gap 不可见，动画结束后 dasharray 残留
- **修复**：动画过渡（stroke-dashoffset → 0）结束后 `transitionend` + 1.2s 兜底清空 `stroke-dasharray`，恢复实线
- **验证**：像素级沿 path 采样（body_composition 修复前缺 26/61 点 → 修复后 61/61 全命中）；守卫测试 +2（动画后 dasharray 清空 / animation:false 无 dash）
- **遗留**：多序列线完全重合时后画线覆盖先画线（数据巧合，非渲染 bug，SVG 语义如此）

## v1.12（2026-08-13 · 图表两处视觉 bug 修复 · #317 验收）

**charts.js 两处视觉缺陷修复**（非破坏性 · 签名零变更 · 纯内部实现/样式）。

- **donut 粗环裁切**：固定 `r=52` 仅支持 `ringWidth ≤ 16`；`ringWidth 22/24/26` 时圆环外缘超出 svg viewBox 半宽被裁切成"方框圆环"。修复：`r = max(20, 60 - ringWidth/2 - 2)` 随 ringWidth 自适应（外缘恒 ≤ 58 留 2 边距）。**向后兼容**：ringWidth ≤16 时 r 从 52 → 50（外缘从 60 → 58，视觉基本一致，环略微内收 2px）
- **line x 标签溢出**：`.hm-c-line-wrap` 高度固定 `--c-h`，svg `height:100%` 占满后 x 标签行溢出 wrap 底部，与下方内容（note/表格）重叠。修复：wrap 改 `display:flex;flex-direction:column`，svg `flex:1`，x 标签行自然落在 wrap 内底部。**向后兼容**：无 x 标签（labels:'none'）时 svg 仍占满；有标签时 svg 高度 = `--c-h` 减标签行，总高度不变
- 守卫测试 +3（donut ringWidth 26 外缘 < 半宽 / line x 标签不溢出 wrap / donut 中心文字可显式关闭）→ 公共组件全量 172/172 全绿

## v1.12（2026-08-13 · smartSelect 候选区折叠 · #312 实测反馈）

**候选区折叠**（非破坏性 · 新可选参数 `maxChips` · 签名零变更; 实测发现分类几十上百个时 chips 全量平铺把确认页拉成长页）。

- **`maxChips`（缺省 8, 0/负数/非数字 = 不折叠）**: 候选 chips 超过阈值 → 折叠态只显前 maxChips 个 + 末尾「展开全部(N)」按钮（ghost 虚线样式 `.ss-more`）; 展开后显示「收起」; 展开态点选后保持展开（便于连续改选）
- **选中项保可见**: 初始选中（initial/inferred）在折叠区时自动提前进可见区（避免「选了但看不见」）; 停用态不占选中位
- **搜索全量联动**: 搜索输入时跳过折叠（全量过滤, 折叠区候选也能搜出）; 搜索框内容跨渲染保持（过滤状态不丢）; 清空搜索回折叠态
- 账户/账本（通常 <10 个）不受影响; 首个消费方饼干记账分类（历史+L1 几十上百）自动受益, 表单零改动
- 契约 §6.9 补 maxChips + CHANGELOG 同步; 守卫测试 +8（折叠默认/展开收起/选中保可见/选中态高亮/搜索穿透折叠/清空回折叠/展开保持/可配）→ 全量全绿
- 验收页新增「大量候选 · 折叠」场景（60 个分类）

## v1.11（2026-08-13 · smartSelect 选择器组件 · #312 · 公共层立项 #320）

**smartSelect = 字段级「复用优先·新建其次」选择器组件**（非破坏性 · 新增全局函数 + 新增样式 · 既有接口零变更; 首个使用域 = 饼干记账, 根治 #298）。

- **定位**: 字段级组件（一页 N 实例, 每字段一容器一 config 一隐藏 input, 互不干扰）· 零领域词全参数化 · `smartSelect(el, config)` 一行接入; 与 copyText/actionBar 同级入 base.js/base.css（注入走 SHARED-HELPERS/SHARED-CSS 管线, 注入器零改动）
- **行为契约**（#307 形态定稿）: chips 平铺候选 + 顶部「已选卡片」（SVG ✓ + 来源徽章）; 初始选中优先级 = **AI 推断 > 历史预填 > AI 推荐新建 > 空**（initial 缺省时组件自推; 无推断时默认选中「AI 推荐新建」）; 用户可改选已有/自定义新建/留空; **绝不静默填错**; 新建落位候选区 chip、重名自动选中已有; 相似提示组件内置; 停用划线置灰不可点; 搜索过滤候选; 主题色默认账本藏蓝 #123A63（CSS 变量每实例可覆盖）
- **数据契约**（#309 契约草案）: config 与 `form.selector.<fieldKey>` 对齐（snake_case）——`options(含 disabled) / inferred / recommended_new / initial{name,source}`; source 白名单 `inferred|recommended_new|existing|history|custom|empty` 违规直接报错; options 缺省空数组且无推断/推荐/initial → **降级普通输入**（T4 决议）
- **回填协议**（组件→上层）: `input.value` + `dataset.source` + `dataset.new('1'=新建)` + change 事件（bubbles）; `smartSelect(el).getState()/getValue()` 可选; **prompt 由上层 buildPrompt 自拼（组件零 prompt 知识）**
- **守卫**（契约 §6）: 结构校验违规直接报错（对齐 Base v1.2）; 类名全 `ss-` 命名空间（封装纪律, #309 用户实测揪出裸类名 `.plain` 冲突 bug 的教训）; 全部动态文本 esc 零注入面; chips 用 `<button type="button">`（无障碍 + 键盘可用）
- 契约 §6.3 条目更新 + 新增 §6.9 + CHANGELOG 同步; 守卫测试 +29（渲染/优先级推导/回填协议/停用/新建/重名/相似提示/留空/降级/校验报错/封装纪律反例/XSS/多实例/搜索过滤/主题覆盖/getState）→ 全量全绿
- 验收页: `docs/reviews/smartSelect验收.html`（#298 美团场景 + 三字段 + 降级 + 主题切换; 回填仪表**默认隐藏**（生产不显示）, 验收时可开）

## v1.10（2026-08-13 · copyText 反馈钩子 · #328）

**copyText 自定义反馈文案 + 回调钩子**（非破坏性 · 签名零变更 · 新增可选能力; 对齐 08 规范「文案由各技能按场景自设计」2026-08-13 修订, 备忘录 6 模板手搓 silent 包装退役的前置 Base 能力）。

- **`opts.toast = {ok:{msg,detail,icon?}, fail:{msg,detail,icon?}}`**: 自定义成功/失败 toast 文案——只覆盖提供的字段, 缺省回落默认（ok 默认 已复制/粘贴给 AI; fail 默认 复制失败/长按选择文本手动复制 + danger 徽章, 失败徽章恒在）
- **`opts.onOk` / `opts.onFail` 回调**: 复制成功（主路径或 `_fbCopy` 兜底）必触发 onOk, 最终失败必触发 onFail, 互斥
- **silent 组合**: `silent:true` 不弹 toast 仍触发回调（定制文案场景标准做法: silent + 乐观 toast + onFail 纠错）
- **向后兼容**: 未传新选项行为与 v1.9 逐字一致（守卫测试断言默认 toast 文案）; `copyText('')` 空串仍直接 return 无回调（既有语义）
- 契约 §5 表格 + §6.2 + 新增 §6.8 + CHANGELOG 同步; 守卫测试 +7（默认文案回归/自定义文案/部分覆盖回落/图标覆盖/onOk-onFail 互斥/silent+钩子/空串 noop）→ 169/169 全绿

## v1.9（2026-08-13 · selectList 行内控件 · #327）

**selectList 行内输入控件**（非破坏性 · 签名零变更 · 新增可选能力; 备忘录 3 向导页自研勾选行退役的前置 Base 能力）。

- **items[].widget 新可选字段**: `{type:'date'|'text'|'select', key, label?, placeholder?, options?}` —— 行内控件与勾选/批量/计数共存（单条目一格; 非法 type 降级 text, key 缺省 'w'+行号, options 元素可为字符串或 {value,label}）
- **读取接口（选定形态 = opts.onSubmit 等价形式, 非返回对象）**: 任意批量操作点击后触发 `opts.onSubmit(selectedIds, values)`（与 onClick 并列; 无勾选不触发, 与既有拦截一致）; `values` = 全部行内值 `{[id]:{[key]:value}}`（含未勾选条目, 无 widget 条目不出现）; 未填统一归一 `null`
- **批量回调增强**: `onClick(ids, values)` 第二参 = 勾选条目对应的行内值（只读勾选; 未填 → null 不报错; 未勾选条目不参与）——旧回调只取第一参, 零影响
- **计数联动隔离**: 控件值变化不干扰「本组已选 x/y」（update 只数勾选态）
- **零注入面**: 行内 label/placeholder/option value+label 渲染一律 esc; 样式走 token A 组（base.css `.sl-widget*`）
- **向后兼容**: 未声明 widget 的既有调用渲染输出逐字节不变（守卫测试 outerHTML 回归断言）
- 契约 §6.3 条目更新 + 新增 §6.7 + CHANGELOG 同步; 守卫测试 +11（三种控件渲染/onSubmit 全量读取/批量勾选读取/未填 null/计数隔离/点击不勾选/无 widget 逐字节回归/转义/非法 type 降级/无勾选拦截）→ 162/162 全绿

## v1.8.1（2026-08-13 · 测试卫生修复 · #325）

**test_help_template 缺省落盘残留修复**（非资产变更 · 纯测试 + 忽略规则;Base 资产/契约签名零改动）。

- `test_render_default_filename_by_skill` 改为在 pytest `tmp_path` 内复制模板副本后执行无 `--output` 调用,断言缺省产物落在临时 `out/help_<技能名>.html`（保留缺省文件名契约,不再向仓库目录落盘）
- `.gitignore` 新增 `公共组件/assets/out/`（injector 缺省输出目录兜底,防 untracked 残留）
- 回归:公共组件全量 151/151 全绿;测试后 `git status` 零残留

## v1.8（2026-08-13 · toast 队列改堆叠模式 · #304）

**toast 堆叠模式**（非破坏性 · 签名零变更 · 行为升级 · #299 备忘录重构反馈 → 公共层 ISSUE #304, 用户拍板四项决策）。

- **堆叠显示**: 同屏最多 N 条 toast 同时可见（原队列串行 1 条 → 堆叠 N 条）; 老上旧下（新 toast 贴屏幕底部出现, 旧的向上顶, 间距 8px, 新增 `#hm-toast-stack` 容器）
- **N 可配置**: `opts.maxStack` 调用时传参, 默认 5; 栈容量 = 栈内各 toast maxStack 的最大值（空栈 5）
- **超 N 处置**: 挤掉最旧（FIFO）, 新 toast 照常显示（已核实 6 技能生产模板无操作按钮 toast, 无「撤销来不及点」风险）
- **移动端收窄**: ≤820px 视口上限自动收窄为 3（375px 手机 5 条全宽 ≈ 糊半屏）
- **兼容**: `toast(msg, detail)` 完全等价 v1.1; `__hmToastFlush` 升级为清空整个栈; 单条独立计时消失, 互不影响; 全宽适配从 .hm-toast 迁移到栈容器
- **回归**: 守卫测试 test_toast_queue 重写 → 堆叠 6 项（同屏 N 条/挤最旧/maxStack 参数/移动端收窄/独立消失/清栈）+ 既有 145 项, 151/151 全绿; 双端验收页 `docs/reviews/304-toast堆叠验收.html`
- 契约 §5.1 + README §4.3 同步; 08 规范零改动（toast 样式基准不变, 规范只描述样式与文案）

## v1.7（2026-08-13 · .hm-actions 自约束宽度 · #322）

**actionBar 复制按钮胶囊自约束**（非破坏性 · 样式细节 · #314 波① 验收发现）。

- `.hm-actions` 加 `max-width: 520px; margin-left/right: auto; box-sizing: border-box`
- 修复：复制数据/复制日志按钮被全宽容器拉伸成半屏宽块（卡路里 6 页桌面 636px / 饼干 888px zone → 收敛 520px 居中）
- 影响面：zone 宽 > 520 的场景收敛居中（胶囊语义恢复）；zone 宽 < 520 的窄容器场景零变化（max-width 不触发）
- 回归：公共组件 tests + 饼干/作息/卡路里三技能 pytest 全量 + 代表页双端几何对比（见 #322 闭环评论）
- 契约不变（actionBar 签名/按钮类名零变更）

**charts.js 四形态全参数化 + 复合形态**（契约 v1.6;与 #288 方向 A 定稿一致;新增参数非破坏性, 既有调用零变更;与 #289/#290 并发, 版本号按落地顺序递增）。

- **折线图 line 全量 16 项**: `height/compact/width` 尺寸三件套 · `color/lineWidth/dashed` 线条 · `smooth` 平滑曲线（Catmull-Rom, 数据点严格在曲线上）· `showDots/dotSize/dotStyle` 数据点 · `area/areaOpacity` 面积渐变 · `labels('edge/all/none/select')` 标签策略 · `showValues/labelRotate` 数值标注 · `yMin/yMax/grid` 坐标 · `format` 数值格式化 · `tooltip` 悬停提示 · `markLine` 阈值线 · `markPoint` 峰谷标注 · `step` 阶梯图 · `animation` 入场动画 · `series` 多序列 + `legend` 图例 · `avgLine` 移动均线 · `highlightLast` 最新点高亮
- **柱状图 bar 对齐 7 项**: format/colors/singleColor/height/compact/labels/showValues/yMin/yMax/grid/tooltip/animation; 修复「柱底参差」根因（绘图区+标签区两段式）
- **环形图 donut 对齐 6 项**: format/colors/size/ringWidth/legend(含手机 bottom)/showPercent/animation
- **进度条 progress 对齐 4 项**: color/gradient/height/showPct/animation
- **复合形态 3 个**: `charts.combo`（柱线组合）/ `charts.sparkline`（迷你趋势, 涨绿跌红）/ `charts.gauge`（仪表盘弧形进度）
- **结构校验（硬行为）**: items 非数组/缺 label/value 非法 → 直接抛错（对齐 Base v1.2 违规报错）; 显式 null = 缺失断点（line 线段断开）
- **坐标唯一性修复**: 容器零 padding + 留白进 viewBox → 数据点与线物理对齐（实测 <0.2px）; vector-effect 防拉伸变形
- **双端自适应**: ≤720px 手机独立 UI（标签两行/图例下沉/高度紧凑/触屏 tooltip）
- 守卫测试 141/141 全绿（+33 项参数断言 + 坐标对齐 + 双端视口 + 结构校验）; 契约 v1.6 + CHANGELOG 同步

## v1.5（2026-08-12 · #289 P2 HELP 参数化落地）

**HELP 参数化正式版**（契约 v1.2 + scene-data-contract v1；新增资产非破坏性，既有接口零变更）。

- **新资产 `assets/help_template.html`（单一真相源）**: V4.16 原型（用户 2026-08-12 认可）收敛为 Base 参数化模板——去手机壳真机全屏、数据全外部注入（`<!--INJECT-DATA-->` 注入 scene-data 契约 JSON）、复制/toast 走 Base 控件、待开发徽章模板内置（t-dev · 对齐 V4.16 定稿视觉）
- **新契约 `docs/scene-data-contract.md` + `docs/scene_data.schema.json`（v1）**: 2 级分组（category→subfunction）scenes 契约 + meta_blocks 透传块 + editable_fields 表单字段;机读 schema 守卫测试
- **归一化层实体取消（用户拍板核心思想）**: Base 零翻译、零适配;技能侧重构数据文件对齐契约（「技能侧零改动」红线作废）
- **injector `--help-template` 模式**: `validate_help_data` 契约校验（必填/分组/场景/id 唯一/status 二态）+ 文件名 sanitize（缺省 `help_<技能名>.html` + `..` 穿越拒绝）
- **editable_fields 管线**: 统一 `{name,label,value,hint,required}` → Sheet 参数表单 + Prompt 实时预览 + 空值拦截（复制按钮契约 v2 #123）
- **meta_blocks 设计**: 技能特有元信息（大厨 prompt_rules/methodology、备忘录 dependencies、卡路里 AI 验证协议）→ Base 原样透传（数据字段 · 页面不渲染展示 · 对齐 V4.16 定稿）
- 契约 v1.2 + CHANGELOG 同步;守卫测试 +33（契约 schema 15 + help 模板 18）→ 108/108 全绿
- 示例: `docs/examples/help_example_data.json`（覆盖 meta_blocks/init_banner/待开发/可编辑字段全特性）;浏览器实测 Sheet 参数表单 + 实时预览通过

## v1.4（2026-08-12 · #290 P2 状态层落地）

**状态层三控件加固**（statusBadge/emptyState/errorReceipt 从「定义」到「对外可靠」; 非破坏性, 签名全部向后兼容）。

- **errorReceipt 去 `window.__hmPayload` 强依赖**: 新增显式 `payload` 参数（优先）+ `data`/`log` 字符串直传（显式优先, 缺省从 payload 生成）+ 兼容全局兜底——**重构票迁移时不再依赖技能侧注入变量名**（卡路里 `__DATA__`/居家 `<script id="payload">` 都接得住）
- **复制按钮零注入面**: 渲染期生成复制文本存 `data-t`, onclick 仅 `copyText(this.dataset.t)`（原实现在点击时实时调 `buildDataText(window.__hmPayload)`, payload 缺失即 JS 报错）
- **错误回执容错**: payload 缺 `scene.snapshot` → 不渲染复制数据/日志按钮, 控件不抛错（错误场景数据常残缺, 不能让控件崩）
- **按钮布局对齐 08 规范**: 修正重试 primary wide 独立一行 + 复制数据/日志 ghost 一行 2 个（补 `.hm-actions` 网格容器, 原实现按钮无容器堆叠）
- **statusBadge 白名单降级**: 非法/未知 status 值降级 `empty`（原实现输出无样式徽章）
- **XSS 面收口**: 三控件全部文本字段经 `esc`; emptyState `action` 明示「受信 HTML 透传, 调用方负责内容安全」（契约 §6.3 明示）
- 契约 v1.4 + CHANGELOG 同步; 守卫测试 +9（非法值降级/XSS 转义/无 payload 容错/按钮布局/字符串直传）→ 15 项三控件测试全绿

## v1.3（2026-08-12 · #288 P2 图表组件落地）

**图表组件 CHARTS-HELPERS 正式版**（契约 v1.3, 与 #287 P2 盘点 + #288 落地一致;新增资产非破坏性, 既有接口零变更）。

- **新资产 `assets/charts.js`（唯一真相源）**: `window.charts` 四接口——`bar(el, items, opt)` / `line(el, items, opt)` / `donut(el, items, opt)` / `progress(el, pct, opt)`;bar/line/progress 从居家管家 CHARTS_JS **零行为变更提取**（接口兼容, 试点模板同调用可跑）, donut 从饼干记账 donutSVG 重构为数据驱动（2026-08-12 新增形态）
- **输入校验 + 空态联动**: items 非数组/空数组 → 渲染 emptyState（window.emptyState 存在则用之, 否则内联兜底）;progress pct 非数兜底 0、超界收敛 0~100
- **语义色走 token A 组**: 默认 `var(--blue,#007aff)` 带 fallback;bar/donut 支持逐项 color 覆盖;donut 内置 10 色 Apple 语义色板
- **纯 CSS+SVG 无外部依赖 · 手机 375px 适配**: 保留居家 @media 断点（柱高 130px/环形 130px）, 柱状图容器内横向滚动不撑破视口
- **自包含**: 本地 esc 兜底（window.esc 不存在时用内联转义）, 可独立注入不依赖 base.js
- **注入器**: `--charts <图表.js>` 参数注入 `<!--CHARTS-HELPERS-->` 占位符（0 或 1, v1.2 已预留;本版补正向测试）
- **SHARED_JS 全家桶核对**（#288 对抗式审查补充）: 居家 `_shared.py` SHARED_JS 中 Base 等价物（esc/toast/copyText/buildDataText/buildLogText/actionBar 等）走 Base、图表走 charts.js、metaHeader/remindersBlock 居家特定留技能侧;居家迁移完成后 SHARED_JS 整体退役（component-contract §2, 属 6 张技能重构票）
- **白名单例外**: 卡路里 weight_volatility_v2 canvas（特殊交互）留技能自营, 走公共层 ISSUE 审批
- 契约 v1.3 文档 + CHANGELOG 同步;守卫测试 +64（注入 4 + Playwright 四接口 17 项）→ 64/64 全绿
- 试点: 居家管家 stats 域同结构演示页走通 CHARTS-HELPERS 注入（四形态 + 375px 视口实测 0 溢出 0 JS 错误）

## v1.2（2026-08-11 · #269 试点 Grill 收口 · 用户拍板全量落地）

**领域无关重构 + 控件库扩展**（契约 v1.2, 与 #269 作息管家试点 Grill 决策一致;零消费方窗口, 破坏性变更零成本）。

- **snapshot 结构化接口（核心）**: buildDataText/buildLogText 从「居家管家字段绑定」重构为**领域无关通用结构**（title/summary/sections）——Base 不认任何技能领域字段, 技能把数据组织成 snapshot 传入, Base 只渲染（用户决策 2: 高于一切, 接口参数要什么技能就传什么）
- **toast 升级通用提示控件**: 4 形态（状态徽章/快捷操作/轻量计数/留空）+ 队列管理（连续不叠加）+ 内置图标库 + 多操作（最多 2）+ 富详情（多行/代码块）+ 无障碍 aria;`toast(msg, detail)` 向后兼容, 增强为可选第三参
- **复制按钮控件化**: 复制数据/复制日志 = Base 控件（文本可配/内容使用方定/参数校验）;增强: 复制前预览 + 格式选择（text/json/csv）+ 敏感字段脱敏 + 导出文件
- **结构校验违规直接报错**: snapshot 缺 title/非数组/节缺 heading → 渲染失败（硬拦截, 用户拍板「违规直接报错」）
- **新控件 P0+P1**: formPrompt（参数表单+实时预览+空值拦截）/ selectList（勾选+批量+计数联动）/ confirm（危险确认）/ foldBox / statusBadge / emptyState / errorReceipt
- **injector 加 SHARED-CSS 注入**: 修 v1.1 只注入 JS 缺口, base.css 唯一真相源进单文件 HTML
- 契约 v1.2 文档 + CHANGELOG 同步

## v1.1（2026-08-11 · 定稿入库）

**首个正式版**（契约 v1.1, 与 T4 #264 决策一致）。

- 形态: 资产目录 + 注入占位符（形态 A）;单一真相源（`assets/`）, 技能原实现迁移后退役
- P0+P1 组件入库: base.js 13 函数（守卫组/copyText v2/toast + metaHeader/remindersBlock/buildDataText/buildLogText/actionBar）
- base.css: token A 组 12 变量 + 按钮样式（≤3 色按功能/ghost 独立行/手机适配）
- injector.py: 硬拦截（INJECT-DATA/SHARED 恰 1）+ `--strict-payload` 信封校验 + `<!--NO-SHARED-->` 豁免通道 + CHARTS 可选
- 守卫测试 17 项（硬拦截反例/豁免/payload 校验/CLI 端到端）
- **跨技能硬编码修正**: buildDataText 技能名 / buildLogText 版本号参数化（消除「居家管家」写死）
- 两份契约入库: component-contract.md / help-template-contract.md（v1.1）

## 历史

- v1.0（2026-08-11 · 原型）: 注入器原型 + base.js 提取（居家管家基准）——原型验证用, 非正式版
