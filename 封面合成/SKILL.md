# 封面合成 (cover-composer)

> 多图旋转叠加 + 文字水印 + 半透明黑防御
> v1.0 · 2026-07-15

## 管什么

多张照片(+ 文字水印)在 16:9 / 9:16 / 4:3 / 1:1 画布上的**层叠合成**:

- ✅ 多图旋转 / 透明叠加 / 对称布局 / 文字水印
- ✅ 半透明黑检测 / 对称性检测 / 暗像素区检测
- ✅ 平台预设模板(抖音 / B 站 / 视频号 / 小红书 / YouTube / 微博)
- ✅ 16 张照片以内的 collage 自动布局(主图 + 左右副图 + 散落副图)

## 不管什么

- ❌ 单图磨皮 / 调色 / 滤镜 → 用其它 skill(如 cover-editor)
- ❌ 视频帧提取 / 视频 thumbnail → 用 ffmpeg
- ❌ GIF / 动图 / AI 生图 → 用其它 skill
- ❌ 大型 LUT / 调色分级 → 用其它 skill
- ❌ 多文字 / 复杂海报 → 用 design-tool

## 触发词

| 中文 | 英文 |
|---|---|
| 封面合成 | cover compose |
| 多图拼图 | photo collage |
| 做封面 | make cover |
| 缩略图 | thumbnail |
| 拼贴 | collage |
| 海报合成 | poster |
| 3 张图叠在一起 | stack 3 photos |
| 加文字 | add text overlay |
| 旋转叠图 | rotated collage |

---

## 5 层架构速查

```
封面合成/
├── SKILL.md                   # ① 文档
├── 封面合成.html              # ① HTML 镜像
├── changelog.md               # ① 版本
├── references/                # ① 深入文档
│   ├── 反模式.md
│   ├── 术语对照表.md
│   └── 案例集.md
├── features/                  # ③ 业务子模块(按操作类型切)
│   ├── compose.md             # 合成入口文档
│   ├── diagnose.md            # 诊断入口文档
│   ├── presets.md             # 预设查询文档
│   └── text.md                # 文字水印文档
├── operations/                # ② 契约层(CLI 子命令入口)
│   ├── cli.py                 # ② 统一入口
│   ├── auto_compose.py        # ② 智能挡(分析图 + 决策 + 调 ①)
│   ├── diagnose.py            # ② diagnose 子命令
│   └── presets.py             # ② presets 子命令
├── core/                      # ③ 业务核心(与 features 文档对应)
│   ├── layers.py              # 旋转/羽化/二值化(踩坑封装)
│   ├── layout.py              # 布局引擎
│   ├── text.py                # 文字水印
│   ├── validators.py          # 硬规则集中
│   └── pipeline.py            # 主流程编排(① 基础 API,参数化)
└── infra/                     # ④ 基础设施(纯函数,无业务)
    ├── canvas.py              # RGBA 画布 + 智能保存
    ├── diagnostics.py         # 像素分析 + 图片特征分析(给 auto_compose 用)
    └── presets_data.py        # 平台规格常量
```

### 命名约定

- `operations/` — **入口**层,CLI 子命令,做"接收参数 → 调度核心"
- `core/` — **业务核心**层,纯算法(rotation、layout、文字),无 CLI 逻辑
- `infra/` — **基础设施**层,纯函数(RGBA 画布、像素诊断、平台规格常量),无业务
- `features/` — **业务说明文档**层,markdown 文档,对应每个 CLI 子命令
- `references/` — **深入文档**层,反模式 / 术语 / 案例

`operations` → `core` → `infra` 层层依赖(只能向下)。`features` / `references` 是文档,不依赖代码。

### 双层 API 设计(关键)

```
                    ┌─────────────────┐
                    │  ② 智能 CLI       │  ← operations/auto_compose.py
                    │  (智能决策)        │     (分析图 → 决策 → 调 ①)
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  ① 基础 API       │  ← core/pipeline.py
                    │  (参数化)          │     (接收完整参数,直接合成)
                    └─────────────────┘
```

- **手动挡 compose**(用户传完整参数)→ ① 直接执行
- **自动挡 auto**(用户只传 --photos)→ ② 分析决策 → 调 ①
- 两者都通过 `core/pipeline.py:compose()` 这个**唯一基础 API** 落地
- `operations/auto_compose.py` 不直接调 `core/layers.py` / `core/text.py` / `core/layout.py`,只调 `compose()` 保持 ① 的纯粹性

---

## ② 契约层 (CLI)

### 子命令 1: `compose` 合成封面(手动挡)

```bash
封面合成 compose \
  --photos main.jpg left.jpg right.jpg \
  --layout symmetric-cascade \
  --aspect 16:9 \
  --text '{"main":"14 天","sub":"-7 斤","tags":"腰突 大基数"}' \
  --bg "#000000" \
  --output cover.jpg
```

**参数**:

| 参数 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `--photos` | ✅ | - | 2+ 张图片路径(第 1 张 = 主图) |
| `--layout` | ❌ | `symmetric-cascade` | 布局类型(symmetric-cascade/cascade/polaroid/grid) |
| `--aspect` | ❌ | `16:9` | 画布比例(16:9/9:16/4:3/1:1 等) |
| `--text` | ❌ | None | 文字层 JSON(见下) |
| `--bg` | ❌ | `#000000` | 画布背景色(hex 或 'auto') |
| `--output`, `-o` | ✅ | - | 输出路径(.jpg/.png) |

### 子命令 1.5: `auto` 智能合成(自动挡)

```bash
封面合成 auto --photos a.jpg b.jpg c.jpg -o cover.jpg
封面合成 auto --photos a.jpg b.jpg c.jpg --hint "14 天" -o cover.jpg
```

**参数**:

| 参数 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `--photos` | ✅ | - | 1+ 张图片路径 |
| `--hint` | ❌ | None | 文字提示(字符串 / JSON / 不传) |
| `--output`, `-o` | ✅ | - | 输出路径 |

**自动挡的决策**(详见 `features/auto.md`):
- `layout`:1 张 → cascade,2-3 张 → symmetric-cascade,4+ 张 → polaroid
- `aspect`:全 portrait → 9:16,全 landscape → 16:9,混合 → 16:9
- `bg`:主图亮 → 用主图主色,否则 → #000000
- `text`:从主图文件名提取,或用 hint

**双层 API 关系**:
```
operations/auto_compose.py (② 智能挡)
    ↓ 调
core/pipeline.py:compose() (① 基础 API,只接受完整参数)
    ↓ 调
core/layers / core/text / core/layout (③ 业务核心)
    ↓ 调
infra/canvas / infra/diagnostics (④ 基础设施)
```

依赖方向严格 `operations → core → infra`(只能向下)。auto 不会绕过 compose 直接调 core/layers。

**`--text` JSON 两种格式**:

简单格式(自动转 3 行):
```json
{
  "main": "14 天",
  "sub": "-7 斤",
  "tags": "腰突 · 大基数"
}
```

完整格式(自定义):
```json
{
  "lines": [
    {"text": "14 天", "position": "middle-center", "size": 200, "font_color": [255,215,0], "outline_color": [0,0,0], "outline_width": 8},
    {"text": "腰突 · 大基数", "position": "bottom-center", "size": 60}
  ]
}
```

**统一输出格式**:
```json
{
  "status": "ok" | "warn" | "error",
  "data": {
    "path": "cover.jpg",
    "size": [1920, 1080],
    "applied_layers": [{"path": "a.jpg", "x": 240, "y": 30, "w": 1250, "h": 1020, "angle": 0, "z": 1}],
    "text_lines": 3
  },
  "message": "合成完成:共 3 个图层",
  "warnings": []
}
```

**退出码**: 0=ok, 1=error, 2=warn

### 子命令 2: `diagnose` 诊断图片

```bash
封面合成 diagnose cover.jpg --check transparency,darkness,symmetry
```

**检查项**:
- `transparency`: 扫半透明像素(alpha ∈ [10,245])
- `darkness`: 扫过暗像素(RGB < 30)占比,以及暗斑位置
- `symmetry`: 左右翻转对比,差异 > 8% 警告

输出示例:
```json
{
  "status": "warn",
  "data": {
    "image": "cover.jpg",
    "size": [1920, 1080],
    "semi_transparent": {"count": 5230, "pct": 0.25, "warning": false},
    "dark_areas": {"count": 1200000, "pct": 55.7, "warning": false},
    "symmetry": {"diff_pct": 5.2, "warning": false}
  },
  "message": "诊断完成:无问题",
  "warnings": []
}
```

### 子命令 3: `presets` 平台/比例预设

```bash
封面合成 presets --list
封面合成 presets --platform douyin
封面合成 presets --aspect 16:9
```

支持的平台:抖音 / 视频号 / 小红书 / 快手 / B站 / YouTube / 微博 + 通用 16:9 / 9:16 / 4:3 / 1:1

---

## ③ 业务核心(`core/`)

### `layers.rotate_hard(path, w, h, angle)` ⭐ 今天踩坑封装

硬旋转,7 步流程:

```python
def rotate_hard(path, target_w, target_h, angle):
    im = Image.open(path).convert("RGB").resize((target_w, target_h), Image.LANCZOS)
    w, h = im.size
    diag = int(sqrt(w**2 + h**2)) + 20
    rgba = im.convert("RGBA")
    temp = Image.new("RGBA", (diag, diag), (0,0,0,0))
    temp.paste(rgba, ((diag-w)//2, (diag-h)//2), rgba)
    rotated = temp.rotate(angle, resample=Image.BICUBIC, expand=False)
    cropped = rotated.crop(rotated.getbbox())
    return binarize_alpha(cropped)
```

防坑:旋转黑边 / alpha 羽化 / 中间值残影

### `layers.binarize_alpha(rgba)`

alpha 通道二值化(>128 → 255),消除 PIL 抗锯齿的中间值

### `layers.place(canvas, img, x, y)`

纯硬贴图层,无 shadow 无 feathering

### `layout` 支持 4 种(`core/layout.py`)

| layout | 用途 |
|---|---|
| `symmetric-cascade` (默认) | 主图 + 左右副图,镜像对称 |
| `cascade` | 主图 + 副图堆叠(右下偏移) |
| `polaroid` | 主图中央,副图四角散落(拍立得风) |
| `grid` | 网格平铺(多图无主图场景) |

### `core/pipeline.py` 主流程

```
photos → 校验(validators) → 画布(infra.canvas) →
布局(core.layout) → 按 z 处理每张图(core.layers) →
文字(core.text) → 诊断(infra.diagnostics) → 保存(infra.canvas.safe_save) →
返回 {status, data, message, warnings}
```

---

## ④ 基础设施(`infra/`)

- `infra/canvas.py` — RGBA 画布创建 + 智能保存(.jpg 强制转 RGB,.png 留 alpha)
- `infra/diagnostics.py` — 像素分析(brightness / alpha / bbox / symmetry)
- `infra/presets_data.py` — 平台规格常量(不存 DB)

---

## ⑤ 集成层

- ✅ 输入校验:`core/validators.py` 在 pipeline() 入口校验,status=error 不 crash
- ✅ 失败降级:photos[i] 不存在 → status=error,明确告诉用户哪个
- ✅ 输出标准 JSON:供其它 Skill(如居家管家、智剪工坊)解析,联动生成 vlog 封面

---

## 反模式清单(精简版,详见 references/反模式.md)

**核心 8 条**,每条都是真实坑:

1. ❌ `Image.rotate(expand=True)` on RGB → 角是黑实色 → ✅ **先转 RGBA 再 rotate**
2. ❌ GaussianBlur 羽化 alpha → 半透明黑 → ✅ **二值化**(>128 → 255)
3. ❌ shadow 扩散 + 画布色 → 半透明黑 → ✅ **完全去掉 shadow**
4. ❌ RGB 转 RGBA → alpha 默认 255 → ✅ RGBA 直接创建,fill=(0,0,0,0)
5. ❌ JPG 保存 RGBA → alpha 丢 → ✅ .png 留 alpha,.jpg 强制 RGB
6. ❌ shadow offset (12,12) → 视觉不对称 → ✅ all-around 或去掉
7. ❌ 不显式 z-order → 谁覆盖谁不确定 → ✅ LayerSpec.z 显式
8. ❌ 文字无描边 → 亮色照片读不清 → ✅ stroke_fill=(0,0,0) 黑色描边

---

## 自检清单 (按手册 ③)

| 层 | 项目 | 状态 |
|---|---|---|
| ① 文档 | SKILL.md 第一段 30 秒答"管什么 / 不管什么" | ✅ |
| ① 文档 | 触发词表 = 9 个动词+名词组合 | ✅ |
| ② 契约 | argparse schema 文档化 | ✅ |
| ② 契约 | 统一 `{status, data, message}` JSON | ✅ |
| ② 契约 | 错误含字段名 + 当前值 + 期望值 + 怎么修 | ✅ |
| ③ 业务 | 模块切分 4 个(operations/core/infra/features),各 50-200 行 | ✅ |
| ③ 业务 | 软规则用心法表达 | ✅ (在 references/) |
| ③ 业务 | 硬规则集中在 `core/validators.py` | ✅ |
| ④ 数据 | infra/canvas.py / diagnostics.py / presets_data.py | ✅ |
| ⑤ 集成 | 输入校验 + 失败降级 + 标准 JSON | ✅ |

---

## 快速上手(3 分钟)

```bash
# 1. 查平台预设
封面合成 presets --platform douyin
# → {"ratio": "9:16", "size": [1080, 1920], "name": "抖音"}

# 2a. 自动挡(只传 --photos,AI 决策)
封面合成 auto \
  --photos ~/DAY14/汉堡特写.jpg ~/DAY14/吃包.jpg ~/DAY14/健身房.jpg \
  -o ~/DAY14/cover.jpg
# → 智能决策:layout=symmetric-cascade, aspect=9:16, bg=#000000
# → 返回的 decisions 字段告诉你 AI 为啥这样选

# 2b. 手动挡(传完整参数,精确控制)
封面合成 compose \
  --photos ~/DAY14/汉堡特写.jpg ~/DAY14/吃包.jpg ~/DAY14/健身房.jpg \
  --layout symmetric-cascade \
  --aspect 16:9 \
  --text '{"main":"14 天","sub":"-7 斤","tags":"腰突 大基数"}' \
  -o ~/DAY14/cover.jpg

# 3. 自检
封面合成 diagnose ~/DAY14/cover.jpg
# → status: "ok" 或 "warn",给出具体警告和修复建议
```

---

## 完整 changelog

### v1.0 (2026-07-15)
- 初版。从智剪工坊 DAY14 封面处理的 16 个真实踩坑提取
- 4 个 layout + 3 个子命令
- 完整的 5 层架构 + 16 条反模式防御
- 目录重构:scripts → operations+core,lib → infra,新增 features(业务说明文档)