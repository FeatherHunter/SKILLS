# Base 组件契约 v1.1（待入库 `公共组件/`）

> 来源：T3 契约草案（#263）+ T4 形态决策（#264）+ 原型验证 + **2026-08-11 对抗式审查 6 条修正**（v1 → v1.1）
> 本契约是 Base Skill 组件的**冻结接口**，修改必须走公共层 ISSUE（总纲 09 §92）+ 遵循 §8 版本机制。

## 0. 版本记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-08-11 | 初稿（P0 签名/P1 契约/占位符/注入器接口） |
| v1.1 | 2026-08-11 | 对抗式审查修正：①唯一真相源 ②payload 信封契约 ③硬拦截豁免通道 ④版本与变更机制 ⑤P0/P1 实施分界 ⑥注入器 payload 结构校验 + 定稿: 信封加 `meta.skill_name`（buildDataText 标题参数化） |

## 1. 目录结构（Base Skill 定稿后的样子）

```
公共组件/
  SKILL.md                 # Base Skill 定义（触发词/用法/资产清单）
  README.md                # 使用手册（接管线步骤/占位符规范/验收清单模板）
  CHANGELOG.md             # 版本变更记录（见 §8）
  assets/
    base.js                # P0+P1 JS（13 函数，单一真相源）——原型已跑通
    base.css               # A 组 token + 按钮样式（P1，入库时补）
  injector.py              # 注入器（CLI + 硬拦截校验 + payload 结构校验）
  docs/
    component-contract.md  # 本契约
    help-template-contract.md  # 参数化 HELP 模板契约
```

## 2. 唯一真相源声明（v1.1 新增）

- **Base `assets/` 是公共组件的唯一真相源**——所有技能的公共 JS/CSS 一律以 Base 为准
- 各技能原实现（居家管家 `scripts/render/_shared.py`、饼干记账 `scripts/_shared_js.py`、备忘录 `script/_shared/clipboard.js`、各技能内联实现）在**对应技能迁移完成后退役**
- **迁移完成前**：公共组件的任何修改只允许发生在 Base，技能内文件只读（防止同源双写漂移）
- 原型 `build_base_asset.py` 的提取是一次性初始化动作，正式版不再从技能文件反向同步

## 3. 占位符标准

| 占位符 | 数量规则 | 用途 |
|---|---|---|
| `<!--INJECT-DATA-->` | **必须恰好 1** | 数据注入点（payload JSON） |
| `<!--SHARED-HELPERS-->` | **必须恰好 1**（硬拦截） | 公共 JS 注入点（base.js） |
| `<!--CHARTS-HELPERS-->` | 0 或 1 | 图表组件（可选，第二版） |

**硬拦截语义**：INJECT-DATA 缺失/重复、SHARED-HELPERS 缺失/重复 → 渲染失败报错（防漂移机制）。

**豁免通道（v1.1 新增）**：确无公共 JS 需求的模板（如纯静态展示页）必须**显式声明** `<!--NO-SHARED-->`（白名单式：缺省 = 必须注入）。豁免名单由 render 公共层维护并在实施审查中复核；不得用「注释掉占位符」等方式隐式豁免。

## 4. payload 信封契约（v1.1 新增）

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
    "scene": { "...场景专属字段..." }
  }
}
```

- **必填**：`status`（'ok'）、`data.meta.command_cn`、`data.meta.occurred_at`、`data.scene`（对象）
- **可选**：`data.meta.skill_name`（技能中文名，`buildDataText` 数据快照标题用；缺省回退 command_cn）、`data.meta.wake_word`、`data.meta.skill_version`
- 组件依赖字段清单：`buildDataText` 依赖 `data.meta` + `data.scene`（item/items/groups/tree/events/record 任一）；`buildLogText` 依赖 `data.meta` + `data.copy_log`（可选）；`metaHeader` 依赖 `data.meta`
- 注入器 **payload 结构校验（v1.1，可选开关 `--strict-payload`）**：缺必填字段 → error；关闭时仅 json 合法性校验（兼容存量技能过渡）

## 5. P0 冻结签名（原型已验证 · 逐字来自 v2 基准）

| 函数 | 签名 | 语义 |
|---|---|---|
| `esc(s)` | 字符串→转义 HTML | 防 XSS |
| `arr(v)` | 任意→数组 | 安全数组访问 |
| `val(v)` | 任意→HTML | null/空显示「未填写」 |
| `yes(v)` | 布尔→徽章 | 通过/未通过 |
| `validate(p)` | payload→{ok,msg} | 数据守门（status==='ok' + data 是对象） |
| `_fbCopy(s)` | 字符串→bool | execCommand fallback（内部） |
| `copyText(s)` | 字符串→void | v2 语义：clipboard + _fbCopy fallback + 成功/失败双 toast，**不改按钮文字** |
| `toast(msg, detail?)` | 字符串→void | hm-toast 面板（📋+标题+详情+「✓ 知道了」，4.5s，≤820px 全宽） |

三态文案（08 表恒定）：已复制/粘贴给 AI · 复制失败/长按选择文本手动复制 · 请先勾选…

## 6. P1 契约

| 组件 | 签名 | 语义 |
|---|---|---|
| `metaHeader(p, m)` | payload+meta→HTML | 页头（eyebrow 含 command_cn+时间 / h1 / lead / stage） |
| `remindersBlock(p)` | payload→HTML | 顺路提醒（warn/danger 分级） |
| `buildDataText(p)` | payload→文本 | 人类可读数据（`【场景名 · 数据快照】` + 关键指标一行 + 明细分节逐行）——对齐 #248/08 规范 |
| `buildLogText(p)` | payload→文本 | 6 段日志（①场景标识 ②思考链 ③数据结构 ④调用链 ⑤时间戳+版本 ⑥异常）——对齐 #248 |
| `actionBar(p, extra, noSb?)` | payload→HTML | 场景按钮 + 复制数据/复制日志（ghost，独立一行） |
| 样式 token A 组 | CSS 变量 | `--fg/fg2/fg3/bg/card/line/blue/blue2/soft/ok/shadow` |

**按钮规范**：≤3 色按功能区分；偶数一行 2 个、奇数重要按钮单独一行；复制数据/复制日志 = 白底+主色描边+主色文字胶囊、min-height 48px、并排一行独立。

**P0/P1 实施分界（v1.1）**：第一版一起入库，但验收分两步——**P0 先行冻结验收**（守卫组+copyText+toast，原型已按此验证），**P1 跟随**（metaHeader/remindersBlock/buildDataText/buildLogText/actionBar/token，需先过 payload 信封契约）。

## 7. 注入器接口

```bash
python injector.py <模板.html> --payload <数据.json> [--output <输出.html>] [--js <资产.js>] [--charts <图表.js>] [--strict-payload]
```

- 校验：INJECT-DATA 恰 1 / SHARED-HELPERS 恰 1（或显式 `<!--NO-SHARED-->` 豁免）/ CHARTS-HELPERS ≤1
- payload：json 合法性必校验；`--strict-payload` 时按 §4 信封结构校验
- 注入顺序：SHARED → CHARTS → DATA；输出：写文件 + 打印结果 JSON（status ok/error）

## 8. 版本与变更机制（v1.1 新增）

- Base 资产带版本号（如 v1.1），变更记入 `CHANGELOG.md`
- **签名变更 = 破坏性变更**：必须全技能同步 + 一次性完成 + 变更记录；不允许「新签名 + 旧签名并存」跨版本漂移
- 非破坏性变更（内部实现/样式细节）：可独立发布，CHANGELOG 记录
- 任何变更先开公共层 ISSUE（总纲 09 §92），review 后实施

## 9. 与既有规范的关系

- **#248/08-HTML交互规范.md** = prompt 参数格式 / 复制数据日志 / 按钮颜色布局的规范本体（Base 对齐；用户提示「不一定都对」→ 落地时对抗式审查逐条验证）
- **T3 草案（#263）** = 本契约的盘点基础
- **居家管家 render/__init__.py** = 注入器的现成范式（迁移完成后退役，见 §2）

---
提交信息：
- 提交者: Mavis
- 提交时间: 2026-08-11 12:06
- 任务上下文: #264 推进——对抗式审查 6 条修正（唯一真相源/payload 信封/豁免通道/版本机制/P0P1 分界/结构校验）落地 v1.1
