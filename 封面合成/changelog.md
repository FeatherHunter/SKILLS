# 封面合成 changelog

## v1.0 (2026-07-15)

### 初版

**来源**:从智剪工坊 DAY14 封面处理的 16 个真实踩坑提取

**踩坑史**(DAY14 封面处理):
1. 旋转图片的角是黑色实色(RGB rotate 填充黑色)
2. alpha 羽化后边缘有半透明黑
3. shadow 扩散造成画布上方半透明黑叠加
4. 画布 RGB 转 RGBA 时 alpha 默认 255 不透明
5. JPG 保存 RGBA 丢失 alpha
6. 旋转角刚好是黑色实色而非透明
7. PIL rotate 抗锯齿产生 alpha 中间值
8. shadow offset (12,12) 单边阴影视觉不对称
9. 不显式 z-order 导致谁覆盖谁不确定
10. 文字无黑色描边在亮色照片上读不清
11. 重复缩小主图导致主图消失
12. 4:3 安全区在 9:16 / 16:9 画布上不一致
13. RGB 转 RGBA 后 fill 非黑
14. 字号过大撑爆 4:3 安全区
15. JPG 不支持 alpha → 透明失效
16. 旋转后没 diagnose 半透明黑,用户反馈才发现

**目录结构(5 层 + 文档)**:
- ① 文档:`SKILL.md` + `封面合成.html` + `changelog.md` + `references/` + `features/`
- ② 契约:`operations/cli.py compose.py diagnose.py presets.py`
- ③ 业务核心:`core/pipeline.py layout.py layers.py text.py validators.py`
- ④ 基础设施:`infra/canvas.py diagnostics.py presets_data.py`
- ⑤ 集成:status/error 标准 JSON,供其它 Skill 调用

**实现的核心函数**:
- `rotate_hard(path, w, h, angle)` — 7 步硬旋转(临时大画布 → rotate → crop bbox → 二值化)
- `binarize_alpha(rgba)` — alpha 二值化(>128 → 255)
- `text_layer(canvas, content, position, ...)` — 文字 + 黑色描边
- `fit_text_to_area()` — 字号自动适配
- `symmetric-cascade` layout — 主图 + 左右副图,镜像对称
- `diagnose` 子命令 — 扫半透明黑 / 暗区 / 对称

**4 个 layout**:
- symmetric-cascade(默认,镜像对称,适合主图+左右副图)
- cascade(主图 + 副图堆叠,右下偏移)
- polaroid(主图中央,副图四角散落)
- grid(网格平铺)

**3 个 CLI 子命令**:
- compose:合成封面
- diagnose:诊断图片问题(半透明黑/暗区/对称)
- presets:查询平台/比例预设

### 目录重构(v1.0 后期)

最初设计是 `scripts/` + `lib/`,按 5 层架构的"业务+数据"分。但发现命名问题:
- `scripts/` 太通用,跟其他 skill 的同名目录撞了,层级也分不清"哪个是入口哪个是核心"
- `lib/` 含义模糊,不像 "④ 数据层" 那种领域感

**重构后**(本次改动):
- `operations/` — 入口层(② 契约层,CLI 子命令入口)
- `core/` — 业务核心(③ 业务层,纯算法)
- `infra/` — 基础设施(④ 数据层,纯函数)
- `features/` — 业务说明文档(① 文档层,markdown)

命名理由:
- `operations` = "做什么操作"= 入口层
- `core` = "业务核心"= 算法层(对应手册 ③ 业务层)
- `infra` = "基础设施"= 公共函数层(对应手册 ④ 数据层)
- `features` = 按 CLI 子命令切的功能说明文档

依赖方向:`operations → core → infra`(只能向下),`features` / `references` 是文档不依赖代码。

### 双层 API 设计(v1.0 → v1.1)

**问题**:用户希望既能"自己传参数精确控制",也能"AI 自动分析决策"。原设计只支持前者(必须传 layout/aspect/bg/text)。

**解决**:增加"智能挡" auto_compose,作为 `operations/cover_auto/`,内部用 `infra/cover_diagnostics.py` 的图片特征分析做决策,然后调 `core/cover_pipeline.py:compose()` 这个唯一基础 API。

**双层结构**:
- **手动挡 compose**(原):用户传完整参数 → ① core/cover_pipeline.compose() 直接执行
- **自动挡 auto**(新):用户只传 --photos → ② operations/cover_auto.analyze + decide + 调 ①

**目录影响**:
- `infra/cover_diagnostics.py` 新增 `analyze_image()` `decide_layout()` `decide_aspect()` `decide_bg()` `decide_text()` 5 个函数
- `operations/cover_auto/` 新增,做"分析 + 决策 + 调 ①"包装
- `operations/cover_cli/` 新增 `auto` 子命令,接受 --photos --hint --output
- `core/cover_pipeline.py:compose()` 完全不动(已经支持任意参数)
- `infra/__init__.py` 导出新函数

### 命名规范化(v1.1 → v1.2,本次)

**问题**:多个 Skill 共用 `scripts/` `lib/` 等通用目录名 + `cli.py` `layers.py` 等通用文件名,AI 看到 `operations/cli.py` `core/layers.py` 等文件时**不知道这些是封面功能还是其它功能**。

**解决**:给封面 Skill 所有 .py 加 `cover_` 前缀,改成 Python 包(每个功能一个 cover_子目录,`__init__.py` 是入口):

| 之前 | 之后 | 说明 |
|---|---|---|
| `core/layers.py` | `core/cover_layers/__init__.py` | 旋转 / 二值化(踩坑封装) |
| `core/layout.py` | `core/cover_layout/__init__.py` | 布局引擎 |
| `core/pipeline.py` | `core/cover_pipeline/__init__.py` | ① 基础 API compose() |
| `core/text.py` | `core/cover_text/__init__.py` | 文字水印 |
| `core/validators.py` | `core/cover_validators/__init__.py` | 硬规则 |
| `operations/cli.py` | `operations/cover_cli/__init__.py` | ② 统一入口(4 子命令) |
| `operations/auto_compose.py` | `operations/cover_auto/__init__.py` | ② 智能挡 |
| `operations/diagnose.py` | `operations/cover_diagnose/__init__.py` | ② diagnose |
| `operations/presets.py` | `operations/cover_presets/__init__.py` | ② presets |
| `infra/canvas.py` | `infra/cover_canvas/__init__.py` | ④ RGBA 画布 |
| `infra/diagnostics.py` | `infra/cover_diagnostics/__init__.py` | ④ 像素分析 + 图片特征分析 |
| `infra/presets_data.py` | `infra/cover_presets_data/__init__.py` | ④ 平台规格常量 |

**AI 看到 `cover_xxx` 前缀时**:
- 立刻知道"这是封面功能"
- 知道调用边界(只对封面目录生效)
- 知道依赖方向(只向下,不跨封面)

**关键设计原则**(避免反模式):
- ① 基础 API 保持纯粹,不塞"自动决策"逻辑
- ② 智能挡只调 ①,不直接调 core/layers / core/text / core/layout
- operations → core → infra 依赖方向严格(只能向下)
- 目录加 cover_ 前缀 = 跨 Skill 不串台(AI 一眼能分清哪个是封面功能)