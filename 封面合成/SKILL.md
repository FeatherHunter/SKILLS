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

## ① 文档层 (本文件)

### 5 层架构速查

```
封面合成/
├── SKILL.md                   # 本文件(① Agent 读)
├── 封面合成.html              # ① 人类读镜像
├── changelog.md               # ① 版本日志
├── references/                # ① 深入文档
│   ├── 反模式.md              # ⭐ 今天踩的 16 个坑全在这里
│   ├── 术语对照表.md         # "alpha 二值化" 是什么鬼?
│   └── 案例集.md              # 抖音 / B 站 / 视频号案例
├── scripts/                   # ②③ CLI + 业务
│   ├── cli.py                 # ② argparse 入口
│   ├── compose.py             # ③ 主流程
│   ├── layout.py              # ③ 布局引擎
│   ├── layers.py              # ③ ⭐ 旋转 / 羽化 / 二值化(踩坑封装)
│   ├── text.py                # ③ 文字水印
│   ├── diagnose.py            # ③ 诊断子命令
│   ├── presets.py             # ③ 平台预设查询
│   └── validators.py          # ③ 硬规则集中校验
└── lib/                       # ④ 数据层
    ├── canvas.py              # ④ RGBA 画布 + 智能保存
    ├── diagnostics.py         # ④ 像素分析(brightness / alpha / bbox)
    └── presets_data.py        # ④ 平台规格常量
```

---

## ② 契约层 (CLI)

### 子命令 1: `compose` 合成封面

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

## ③ 业务层 (核心模块)

### `rotate_hard(path, w, h, angle)` ⭐ 今天踩坑封装

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

### `binarize_alpha(rgba)`

alpha 通道二值化(>128 → 255),消除 PIL 抗锯齿的中间值

### `place(canvas, img, x, y)`

纯硬贴图层,无 shadow 无 feathering

### `layout` 支持 4 种

| layout | 用途 |
|---|---|
| `symmetric-cascade` (默认) | 主图 + 左右副图,镜像对称 |
| `cascade` | 主图 + 副图堆叠(右下偏移) |
| `polaroid` | 主图中央,副图四角散落(拍立得风) |
| `grid` | 网格平铺(多图无主图场景) |

---

## ④ 数据层 (`lib/`)

- `lib/canvas.py` — RGBA 画布创建 + 智能保存(.jpg 强制转 RGB,.png 留 alpha)
- `lib/diagnostics.py` — 像素分析(brightness / alpha / bbox / symmetry)
- `lib/presets_data.py` — 平台规格常量(不存 DB)

---

## ⑤ 集成层

- ✅ 输入校验:`validators.py` 在 compose() 入口校验,status=error 不 crash
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
| ③ 业务 | 模块切分 6 个,各 50-200 行 | ✅ |
| ③ 业务 | 软规则用心法表达 | ✅ (在 references/) |
| ③ 业务 | 硬规则集中在 `validators.py` | ✅ |
| ④ 数据 | canvas.py / diagnostics.py / presets_data.py | ✅ |
| ⑤ 集成 | 输入校验 + 失败降级 + 标准 JSON | ✅ |

---

## 快速上手(3 分钟)

```bash
# 1. 查平台预设
封面合成 presets --platform douyin
# → {"ratio": "9:16", "size": [1080, 1920], "name": "抖音"}

# 2. 合成
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