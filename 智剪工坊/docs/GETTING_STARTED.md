# 智剪工坊 · 新手引导

5 分钟跑通你的第一个视频。

## 前置要求

- **ffmpeg** —— 已默认配本机路径 `D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe`
- **Python 3.10+**
- **可选:** faster-whisper(GPU 转录), Pillow(封面叠字)

## 30 秒跑通

### 1. 装基础依赖

```bash
pip install Pillow faster-whisper
```

### 2. 试一个剪切

```bash
# 切 30 秒到 60 秒,保存为 out.mp4
python scripts/cut.py trim --input your_video.mp4 --ss 30 --t 30 --output out.mp4
```

### 3. 试一个转场

```bash
# 把 clip1 + clip2 加 1 秒淡入淡出
python scripts/xfade.py --a clip1.mp4 --b clip2.mp4 --type fade --duration 1 --out joined.mp4
```

### 4. 试一个封面

```bash
# AI 生图 + 中文叠字
python scripts/cover_ai.py \
  --prompt "A man on a fitness journey, cinematic dramatic lighting, NO TEXT" \
  --title-main "DAY 1" \
  --subtitle "减脂日记" \
  --out cover.jpg
```

---

## 常用工作流

### A. 完整 vlog 一条龙(7 步)

```bash
# 1. 把所有素材放到 videos/ 目录
# 2. 跑流水线
python scripts/pipeline_vlog.py run \
  --input videos/ \
  --output day1/ \
  --theme "Day 1" \
  --bgm bgm.mp3 \
  --concat-list clips.txt \
  --subtitle-srt day1_subtitle.srt
```

### B. 单视频加 BGM

```bash
python scripts/bgm_loop.py --video vlog.mp4 --bgm bgm.mp3 --volume 0.18 --out vlog_with_bgm.mp4
```

### C. 批量加转场

(待实现 `batch.py`)

---

## 子技能速查

| 想做 | 用这个 |
|---|---|
| 剪切 | `scripts/cut.py trim` |
| 拼接 | `scripts/cut.py concat` |
| 转场 | `scripts/xfade.py` |
| 慢动作 | `scripts/effect_slowmo.py`(待) |
| 推镜头 | `scripts/effect_zoom.py`(待) |
| 调色 | `scripts/color_lut.py`(待) |
| 烧字幕 | `scripts/text_anim.py`(待) |
| 加 BGM | `scripts/bgm_loop.py` |
| AI 封面 | `scripts/cover_ai.py` |
| AI 抠图 | `scripts/ai_features.py`(待) |
| 批量 | `scripts/batch.py`(待) |
| 完整 vlog | `scripts/pipeline_vlog.py` |

---

## 下一步

- 看 [VS_JIANYING.md](VS_JIANYING.md) —— 了解 vs 剪映的能力对比
- 看 [FAQ.md](FAQ.md) —— 常见问题排查
- 看 `references/*.md` —— 各子技能详细文档
