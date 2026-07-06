# 08-cover - AI 封面 — v1.2 已实现

> **对应脚本**: `scripts/ai_cover.py`
> **触发词**: "封面"、"做封面"、"AI 封面"、"AI 生图"、"设计封面"、"缩略图"、"thumbnail"
> **实测状态**: ✅ 验证通过

---

## 1. 调用范式

### 场景 1

```bash
python scripts/ai_cover.py \
  --prompt "A man on a fitness journey, cinematic dramatic lighting, NO TEXT" \
  --title-main "DAY 1" \
  --subtitle "减脂日记" \
  --output cover.jpg
```

### 场景 2

```bash
mavis mcp call matrix matrix_generate_image --file req.json
```

## 2. 参数

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--input` | `-i` | (必填) | 输入视频/音频/图片 |
| `--output` | `-o` | (必填) | 输出路径 |

## 3. 常见错误 / 限制

- 输入文件必须存在（不存在时脚本会报 `FileNotFoundError`）
- 输出目录无权限时脚本会失败
- ffmpeg 默认用 `libx264`，避免 NVENC 崩溃

## 4. 相关参考

- **SKILL.md §14 子技能索引**：本子技能的路由表
- **scripts/README.md**：scripts/ 目录命名规范（`<维度>_<动作>.py`）
- `.archive/CHANGELOG.md`：本子技能历史变更

---

<details>
<summary>📋 原文存档（v0.5 旧版，仅供 git history 追溯）</summary>

# 08 - cover-ai (AI 封面 / 生图 + 中文叠字) — v0.5 已实现

> **对应脚本:** `scripts/ai_cover.py`(1 个,两步法:先生成视觉 + 后叠中文)
> **实测状态:** ✅ 验证通过

```bash
python scripts/ai_cover.py \
  --prompt "A man on a fitness journey, cinematic dramatic lighting, NO TEXT" \
  --title-main "DAY 1" \
  --subtitle "减脂日记" \
  --output cover.jpg
```

---

## 触发词

"封面"、"做封面"、"设计封面"、"AI 生图"、"AI 封面"、"缩略图"、"thumbnail"

## 输入 / 输出

- **输入**: 主题描述 / 参考图(可选)
- **输出**: 1080x608 或 1920x1072 的封面图(JPG)

## 工作流(两步)

**AI 生图对中文支持差**,所以采用"先生成视觉 + 后叠中文"的两步方案。

### Step 1: AI 生视觉图

```bash
mavis mcp call matrix matrix_generate_image --file req.json
```

`req.json` 示例:
```json
{
  "requests": [{
    "prompt": "A dramatic fitness transformation cover image, 16:9. A man's silhouette standing on a body weight scale, dark moody background with red lighting. NO TEXT in image. Clean composition with strong negative space for text overlay.",
    "aspect_ratio": "16:9",
    "resolution": "2K"
  }]
}
```

**Prompt 设计要点:**
- ✅ 描述场景(人物 + 背景 + 光线)
- ✅ 指定 NO TEXT(关键!)
- ✅ 指定 negative space 留白
- ✅ 指定风格(cinematic / fitness / motivational)
- ✅ 指定 aspect ratio(16:9 适合 B 站)

### Step 2: PIL 叠中文文字

```python
from PIL import Image, ImageDraw, ImageFont

def overlay_text(image_path, output_path, texts):
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    for text_info in texts:
        font = ImageFont.truetype(text_info["font"], text_info["size"])
        draw.text(
            (text_info["x"], text_info["y"]),
            text_info["content"],
            font=font,
            fill=text_info["color"]
        )
    
    img.save(output_path, quality=92)

# 调用示例
overlay_text(
    "matrix-output.png",
    "cover_final.jpg",
    [
        {"content": "184", "x": 1080, "y": 320, "size": 150,
         "font": "C:/Windows/Fonts/msyhbd.ttc", "color": (255, 56, 56)},
        {"content": "→", "x": 1380, "y": 350, "size": 130,
         "font": "C:/Windows/Fonts/msyhbd.ttc", "color": (255, 255, 255)},
        {"content": "139.9", "x": 1500, "y": 320, "size": 150,
         "font": "C:/Windows/Fonts/msyhbd.ttc", "color": (255, 215, 0)},
        {"content": "Day 1 · 4 个月挑战", "x": 1080, "y": 530, "size": 56,
         "font": "C:/Windows/Fonts/msyh.ttc", "color": (255, 255, 255)},
    ]
)
```

## 配色方案(从第一性原理)

**激励/热血类(健身、挑战):**
- 警示红: `RGB(255, 56, 56)` 或 `#FF3838`
- 目标金: `RGB(255, 215, 0)` 或 `#FFD700`
- 主体白: `RGB(255, 255, 255)` 或 `#FFFFFF`

**治愈/生活类(旅行、美食):**
- 主色暖橙: `RGB(255, 146, 43)` 或 `#FF922B`
- 副色深蓝: `RGB(77, 171, 247)` 或 `#4DABF7`

**专业/知识类(教程、财经):**
- 主色深蓝: `RGB(77, 107, 247)` 或 `#4D6BF7`
- 副色亮金: `RGB(255, 215, 0)`

## 字号参考(1920x1080 画布)

| 元素 | 字号 | 位置 |
|---|---|---|
| 主标题数字 | 130-180 px | 居中 / 右上 |
| 副标题 | 50-70 px | 主标题下方 |
| 系列名 | 40-60 px | 角落 / 底部 |
| 标签 | 30-40 px | 角落 |

## 字体选择

```python
# Windows 自带字体
"C:/Windows/Fonts/msyh.ttc"        # 微软雅黑(默认)
"C:/Windows/Fonts/msyhbd.ttc"      # 微软雅黑 Bold(主标题)
"C:/Windows/Fonts/simhei.ttf"      # 黑体(更现代)
"C:/Windows/Fonts/simsun.ttc"      # 宋体(传统)
```

## 完整脚本

封装到 `scripts/ai_cover.py`,支持:
- 自动调用 matrix 生图
- 自动叠中文
- 自动配色(根据主题)
- 输出 JPG(95% 质量)

## 调用示例

```
用户: "给我做个减肥挑战的封面,184 到 139.9 斤"
→ cover-ai --theme fitness --main "184→139.9" --subtitle "Day 1 · 4 个月挑战"
```

## 输出规格

- **比例:** 16:9(B 站标准,实际 1146x717 也可)
- **分辨率:** 2K(2752x1536)
- **格式:** JPG(95% 质量)
- **大小:** < 2 MB(B 站上传限制)
- **文件名:** `cover_final.jpg`

## 进阶:img2img(图生图)

matrix 支持 input_files 做图生图,可以基于真实照片生成封面变体:

```json
{
  "requests": [{
    "prompt": "Same person, cinematic dramatic lighting, dark background, motivational atmosphere",
    "input_files": ["path/to/original.jpg"]
  }]
}
```

这能让你保持"主角一致性",封面和视频里的真人看起来是同一个人。

</details>
