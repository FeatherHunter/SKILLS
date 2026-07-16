# 封面合成 · 多图拼版 (PIL) 总览

> 写于 2026-07-16 · 由"封面合成"独立 Skill 合并入智剪工坊时沉淀
> 状态: v1.0 落地 · scripts/ai/cover_compose/

---

## 一、定位 / 与 cover.py 区别

| 能力 | cover.py (AI 生图) | **cover_compose (本模块, 多图拼版)** |
|---|---|---|
| 触发场景 | 一段文字 prompt → AI 生图 → 叠字 | 多张照片 → 自动/手动拼版 → 叠字 |
| 依赖 | matrix MCP + PIL | **纯 PIL + numpy,无需 AI** |
| 输入 | prompt / 单图 + 文字 | 1+ 张照片 + 文字 + 布局参数 |
| 输出 | 单图(AI 生成背景 + 叠字) | 单图(多图合成 + 叠字) |
| AI 决策 | matrix 自动构图 | **本模块自带智能决策**(auto 挡) |
| 速度 | 慢(等 AI 出图) | **快(纯本地计算)** |

**什么时候用哪个:**
- 你要**从无到有**生成封面(没有素材,只有概念)→ cover.py
- 你有**多张照片**想做拼版封面 → **cover_compose**(本模块)
- 已有**单张照片**想加文字 → cover.py + `--image`

---

## 二、双层 API 设计

**核心思想**: 同一个基础 API,两种调用方式。

### 手动挡 `compose()` — 全控制

用户传完整参数,直接调基础 API:

```python
from cover_compose import compose

result = compose(
    photos=["a.jpg", "b.jpg", "c.jpg"],
    layout="symmetric-cascade",     # 布局
    aspect="16:9",                  # 画布比例
    text={"main": "14 天", "sub": "-7 斤"},  # 文字
    bg="#000000",                   # 背景色
    output="cover.jpg",
)
# → {"status": "ok"|"warn"|"error", "data": {path, size, applied_layers, text_lines}, ...}
```

### 自动挡 `auto_compose()` — 不传参,AI 决策

用户只传照片,本模块自动分析+决策+合成:

```python
from cover_compose import auto_compose

result = auto_compose(
    photos=["a.jpg", "b.jpg", "c.jpg"],
    hint=None,   # 或 "主标题文字" / {"main": "14 天", ...}
    output="cover.jpg",
)
# → {"status": ..., "data": ..., "decisions": {layout, aspect, bg, text, reasons}, ...}
```

**自动挡会做什么:**
1. 分析每张图(尺寸/主色/亮度/对比度)
2. 决策 `layout`(1/2/3 张 → cascade/symmetric, 4+ 张 → polaroid)
3. 决策 `aspect`(全 portrait → 9:16, 全 landscape → 16:9)
4. 决策 `bg`(主图亮 → 用主图主色;暗 → 纯黑)
5. 决策 `text`(从 hint 或文件名提取关键词)
6. 调用 `compose()` 合成

---

## 三、文件结构 (scripts/ai/cover_compose/)

```
scripts/ai/cover_compose/           ← 整组,1 个目录 12 个模块
├── __init__.py        # 包入口: 导出 compose / parse_text_spec / ASPECT_RATIOS
│
│  ── ② 契约层 (CLI 入口, 4 个) ──
├── cli.py             # 主 CLI: 4 个子命令( compose / auto / diagnose / presets)
├── auto.py            # 智能挡: 看图决策 + 调 pipeline.compose()
├── diagnose.py        # 诊断子命令
├── presets.py         # 平台/比例预设查询
│
│  ── ③ 业务核心 (5 个) ──
├── pipeline.py        # ⭐ 基础 API compose() — 手动/自动挡最终都调它
├── layers.py          # 旋转/二值化/place/text_layer — 踩坑封装
├── layout.py          # 4 种布局计算
├── text.py            # 9 宫格位置 + 批量文字
├── validators.py      # 硬规则校验(无 --force 跳过)
│
│  ── ④ 基础设施 (3 个) ──
├── canvas.py          # 画布创建 + 智能保存
├── diagnostics.py     # 像素级分析 + 智能决策
└── presets_data.py    # 平台规格 + 字体路径常量
```

**关键约束**:
- 箭头只能向下: pipeline → layers/layout/text → canvas/diagnostics/presets_data
- **下层不知道上层存在**: diagnostics.py 不 import pipeline / cli / auto
- 跨包调用通过**相对导入** `from .pipeline import compose`

---

## 四、CLI 调用方式

```bash
# 1. 自动挡(最常用,只传 --photos)
python scripts/ai/cover_compose/cli.py auto \
  --photos a.jpg b.jpg c.jpg \
  -o cover.jpg

# 2. 手动挡(全控制)
python scripts/ai/cover_compose/cli.py compose \
  --photos a.jpg b.jpg c.jpg \
  --layout polaroid \
  --aspect 9:16 \
  --text '{"main":"14 天","sub":"-7 斤"}' \
  --bg "#1a1a1a" \
  -o cover.jpg

# 3. 诊断
python scripts/ai/cover_compose/cli.py diagnose cover.jpg
python scripts/ai/cover_compose/cli.py diagnose cover.jpg --check transparency

# 4. 预设查询
python scripts/ai/cover_compose/cli.py presets --list
python scripts/ai/cover_compose/cli.py presets --platform douyin
python scripts/ai/cover_compose/cli.py presets --aspect 16:9
```

---

## 五、Python API 调用方式(其他模块)

其他模块(如粗加工 `_make_cover.py`)调本模块:

```python
import sys
sys.path.insert(0, r"D:\2Study\StudyNotes\SKILLS\智剪工坊\scripts\ai")
from cover_compose import compose, auto_compose

# 手动
result = compose(photos=[...], layout="symmetric-cascade", ...)

# 自动
result = auto_compose(photos=[...], hint=None, output="cover.jpg")
```

---

## 六、参数白名单

| 参数 | 必填 | 类型 | 默认 | 白名单 |
|---|---|---|---|---|
| `photos` | ✅ | `list[str]` | - | 1+ 张,文件必须存在 |
| `layout` | ❌ | `str` | `symmetric-cascade` | `symmetric-cascade` / `cascade` / `polaroid` / `grid` |
| `aspect` | ❌ | `str` | `16:9` | `16:9` / `9:16` / `4:3` / `3:4` / `1:1` / `4:5` / `5:4` |
| `bg` | ❌ | `str` | `#000000` | hex (`#RGB` / `#RRGGBB`) 或 `'auto'` |
| `text` | ❌ | `dict \| str` | `None` | 见下方 text 格式 |
| `output` | ✅ | `str` | - | `.jpg` / `.jpeg` / `.png` |

**text 格式(两种)**:
1. 简单: `{"main": "14 天", "sub": "-7 斤", "tags": ["健身", "减肥"]}`
2. 完整: `{"lines": [{"text": "...", "position": "top-center", "size": 64, "font_color": [255,215,0], "outline_color": [0,0,0], "outline_width": 4}]}`

---

## 七、4 种布局对比

| 布局 | 适合场景 | 关键参数 |
|---|---|---|
| **symmetric-cascade** (默认) | 主图 + 左右副图,镜像对称 | 1/2/3 张图推荐 |
| **cascade** | 主图 + 堆叠副图,右倾叠放 | 单图主视觉强调 |
| **polaroid** | 主图中央 + 副图四角散落 | 4+ 张图,拍立得风 |
| **grid** | 网格平铺,无主图概念 | 全 square 或对称多图 |

**自动挡决策逻辑**:
- 1 张 → cascade
- 2/3 张 → symmetric-cascade
- 4+ 张 → polaroid
- 全 square → grid

---

## 八、平台预设(presets)

| Platform | 比例 | 尺寸 | 用途 |
|---|---|---|---|
| douyin | 9:16 | 1080x1920 | 抖音 |
| shipinhao | 3:4 | 1080x1440 | 视频号 |
| xiaohongshu | 4:5 | 1080x1350 | 小红书 |
| kuaishou | 9:16 | 1080x1920 | 快手 |
| bilibili | 16:9 | 1920x1080 | B 站 |
| youtube | 16:9 | 1920x1080 | YouTube |
| weibo | 16:9 | 1280x720 | 微博 |

查询: `python cli.py presets --platform douyin` 返回 ratio/size/safe_area

**safe_area 说明**:
- `16:9` 画布的中央 4:3 区域是"安全区",平台裁切不切到重要内容
- `9:16` 画布的中间 200-1680 像素是"安全区",避开顶部标题栏+底部评论栏

---

## 九、返回结构

所有 CLI 子命令统一返回:

```json
{
  "status": "ok" | "warn" | "error",
  "data": {
    "path": "cover.jpg",        // 输出路径
    "size": [1920, 1080],       // 画布尺寸 [W, H]
    "applied_layers": [         // 应用了的图层(供调试)
      {"path": "a.jpg", "x": 240, "y": 180, "w": 1248, "h": 702, "angle": 0, "z": 1},
      ...
    ],
    "text_lines": 2             // 烧上去的文字行数
  },
  "message": "合成完成:共 3 个图层",
  "warnings": [],               // 诊断发现的问题清单
  "decisions": { ... }          // 仅 auto 挡有,记录 AI 决策
}
```

**退出码**:
- `0` = ok
- `1` = error
- `2` = warn(有警告但仍生成)

---

## 十、与其他模块的关系

```
智剪工坊 粗加工流程(_make_cover.py)
  ↓ 调用
cover_compose.compose() / auto_compose()  ← 本模块
  ↓
[执行 PIL 多图拼版]
  ↓
产出 <workspace>/00_智剪/粗加工/cover/cover_*.jpg
```

**与 scripts/ai/cover.py 关系**:
- cover.py 还在原位(AI 生图 + 叠字,本模块不替代它)
- 本模块专注"多图拼版",是 cover.py 的"兄弟能力"
- 触发词分流: "AI 封面" / "生图" → cover.py;"拼版" / "多图封面" → **cover_compose**

---

## 十一、调试入口

如果生成的封面有问题,按以下顺序排查:

1. **诊断**: `python cli.py diagnose cover.jpg`
   - 半透明像素 > 1%? → 检查 layers.py 的 rotate_hard / binarize_alpha
   - 暗区 > 60%? → 检查 canvas.py 的 bg / z-order
   - 左右 diff > 8%? → 检查 layout.py 对称性

2. **对比反模式**: 见 `封面合成-反模式.md` (16 个常见 bug 清单)

3. **查历史案例**: 见 `封面合成-案例集.md` (DAY14 v15-v16 调试 6 次迭代)

---

## 十二、相关文档

- **总览**(本文件) — 双层 API + 文件结构 + 调用方式
- `封面合成-反模式.md` — 16 个常见 bug 清单 + 修复
- `封面合成-案例集.md` — DAY14 v15-v16 真实调试迭代
- `AI封面-生图叠字两步法.md` — 兄弟能力 cover.py 的文档(AI 生图)
- `references/AI封面-生图叠字两步法.md` — 路径契约唯一真理
