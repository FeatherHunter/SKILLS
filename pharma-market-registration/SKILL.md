---
name: pharma-market-registration
description: Use ONLY when the user works on pharmaceutical international registration market requirements (药品国际注册市场要点 / 注册要求 / 申报要求 / 文件清单). Covers developed markets 马达加斯加, 喀麦隆, 也门, 科特迪瓦, 利比里亚, 尼日利亚, 多米尼加, 洪都拉斯, 危地马拉, 柬埔寨, 马里, 南苏丹 and any new (undeveloped) market. Front-load trigger keywords: 注册要求, 申报要求, 市场要求, 文件清单, GMP, COPP, FSC, CPP, CTD, 注册证, 进口许可, 马达加斯加, 喀麦隆, 也门, 科特迪瓦, 利比里亚, 尼日利亚, 多米尼加, 洪都拉斯, 危地马拉, 柬埔寨, 马里, 南苏丹, 非洲, 中美洲, registration requirements, market requirements.
---

# 药品国际注册 · 市场要点库（Market Registration Guide）

本 skill 是"知识库 + 录入工作流"：市场知识按国家分文件存放，内容主要靠用户口头补充录入，AI 负责固化和维护。

## 市场路由表

用户提到以下市场名时，先读对应文件再干活：

| 市场 | 文件 |
|---|---|
| 马达加斯加 | `markets/madagascar.md` |
| 喀麦隆 | `markets/cameroon.md` |
| 也门 | `markets/yemen.md` |
| 科特迪瓦 | `markets/cote-divoire.md` |
| 利比里亚 | `markets/liberia.md` |
| 尼日利亚 | `markets/nigeria.md` |
| 多米尼加 | `markets/dominican-republic.md` |
| 洪都拉斯 | `markets/honduras.md` |
| 危地马拉 | `markets/guatemala.md` |
| 柬埔寨 | `markets/cambodia.md` |
| 马里 | `markets/mali.md` |
| 南苏丹 | `markets/south-sudan.md` |

不在列表内的市场（未开发市场）→ 用 `markets/_template.md` 新建文件，全部内容标「待确认」。

## 工作流

### 流程 A · 查询（用户问某市场要求）

1. 按路由表读对应市场文件
2. 输出：注册文件清单 + 缺口分析（缺哪些文件、需向生产商索要什么）
3. 文件里标「待确认」的条目，输出时提示用户「这条还没确认过，是否属实？」

### 流程 B · 录入（用户口头/文件补充要求）

1. 按路由表定位市场文件
2. 把用户说的要求写进对应字段，更新 `last_verified` 为当天日期
3. 用户提供文件（截图/PDF/邮件）→ 先按工作区三轴模型归档（sources/ 只读原件，research/ 加工产物），再把提炼结论写进市场文件
4. 回报：写入位置 + 一句话总结，等用户确认

### 流程 C · 逐国访谈（新建知识库时）

1. 一次只问一个国家，从市场文件的第一个字段开始逐节问
2. 用户没答的字段留空，标注「待录入」，不追问到底
3. 用户中途提供文件 → 按流程 B 归档 + 提炼
4. 一个国家问完 → 简述已录入内容清单 → 进入下一个国家
5. 国家顺序不强制，用户指定优先

## 置信度规则

| 标记 | 含义 | 何时用 |
|---|---|---|
| 已核实 | 用户明确确认过，或来自官方文件 | 用户口头确认后升级 |
| 待确认 | AI 联网/推测/未确认的信息 | 新信息默认此档 |
| 待录入 | 字段未填 | 用户未提过 |

升级规则：只有用户明确确认的内容才从「待确认」升级为「已核实」，AI 不得自行升级。

## 跨市场文件复用矩阵

同药品在 X 国注册过 → Y 国可能复用：

| 文件类型 | 可复用性 | 说明 |
|---|---|---|
| CTD 模块（药品部分） | 高 | 换市场主要改模块 1（行政信息）和本地化要求 |
| COA / 检验报告 | 高 | 同一批样品可复用，注意有效期 |
| GMP 证书 | 中 | 多数市场接受生产国 GMP，部分要求本国现场核查 |
| COPP / FSC / CPP | 低 | 按市场单独出具，需向生产商/出口国药监索取 |
| Artwork | 中 | 语言、注册号、警示语需本地化 |

## 内容维护

- 每个市场文件头部 `last_verified` 无日期 = 知识可能过期，查询时提示用户
- 用户在新会话里提到市场新要求 → 直接更新市场文件（流程 B）
- 市场文件只存"可复用知识"，不存具体任务实例（任务实例在工作区目录/issue）
