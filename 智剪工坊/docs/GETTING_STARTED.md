# 智剪工坊 · 新手引导

5 分钟跑通你的第一个视频。

## 前置要求

- **Python 3.10+** — 推荐 3.13
- **ffmpeg** — 已默认配本机路径 `D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe`,无需单独装
- **可选:** faster-whisper(GPU 转录)/ mediapipe(美颜)/ matrix MCP(AI 视频/TTS/数字人)

## 30 秒跑通

### 1. 一键安装(推荐)

**Windows:**
```bat
setup.bat
```

**Mac/Linux:**
```bash
bash setup.sh
```

自动完成:
- pip install 9 个实依赖(Pillow, faster-whisper, opencv-python, mediapipe, librosa, numpy, openai-whisper, requests, mavis)
- 验证 ffmpeg / mediapipe / mavis MCP

### 2. 环境验证(5 秒快检)

```bash
python verify.py --fast
```

应该看到 `29/29 脚本 OK`。

### 3. 试一个剪切

```bash
python scripts/cut.py trim --input your_video.mp4 --ss 30 --t 30 --output out.mp4
```

### 4. 试一个转场

```bash
python scripts/xfade.py --a clip1.mp4 --b clip2.mp4 --type fade --duration 1 --out joined.mp4
```

### 5. 试一个 AI 封面

```bash
python scripts/cover_ai.py \
  --prompt "A man on a fitness journey, cinematic dramatic lighting, NO TEXT" \
  --title-main "DAY 1" \
  --subtitle "减脂日记" \
  --out cover.jpg
```

---

## 常用工作流(2026 v0.5)

### A. 完整 vlog 一条龙(7 步流水线)

```bash
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

### C. 批量加转场 / 调色 / 转码

```bash
# 批量加转场
python scripts/batch.py --input videos/ --task xfade --type fade --duration 0.5 --out out/

# 批量调色(cinematic preset)
python scripts/batch.py --input videos/ --task color --preset cinematic --out out/

# 批量转码(1080p)
python scripts/batch.py --input videos/ --task reencode --resolution 1920:1080 --out out/
```

### D. AI 美颜

```bash
# 预设(natural 是默认,推荐)
python scripts/beauty.py --input face.mp4 --output face_beauty.mp4 --preset natural

# 自定义强度
python scripts/beauty.py --input face.mp4 --output face.mp4 \
  --smooth 0.5 --whiten 0.25 --slim 0.3 --enlarge 0.3
```

### E. AI 去水词(L2 word-level)

```bash
# Step 1: 转录(生成 SRT + words.json)
python scripts/remove_fillers.py transcribe --input vlog.mp4 --srt vlog.srt

# Step 2: (Mavis 读 words.json,告诉你 10 个词要删)
# Step 3: 切掉水词
python scripts/remove_fillers.py cut --input vlog.mp4 --srt vlog.srt --output clean.mp4 --remove-words "1,3,11,12,19,28,37,38,39,45"
```

### F. AI 改词翻唱

```bash
# 1. transcribe
python scripts/rewrite_audio.py transcribe --input v.mp4 --srt v.srt

# 2. (Mavis 改写文案,选 voice_id)
# 3. synthesize
python scripts/rewrite_audio.py synthesize --text "改写后的文案" --voice male-qn-jingying --out v_new.mp3

# 4. replace
python scripts/rewrite_audio.py replace --video v.mp4 --audio v_new.mp3 --out v_final.mp4
```

### G. 文字成片 / 数字人

```bash
# 文字成片
python scripts/text_to_video.py --prompt "A man running on a treadmill, cinematic" --out out.mp4

# 数字人
python scripts/digital_human.py --avatar avatar.jpg --script "大家好我是帅猎羽" --out out.mp4
```

---

## 子技能速查(30 脚本,2026 v0.5)

| 想做 | 用这个 | 子技能 |
|---|---|---|
| 剪切 | `scripts/cut.py trim` | 01 cutting |
| 拼接 | `scripts/cut.py concat` | 01 cutting |
| 转场 | `scripts/xfade.py` | 02 transitions |
| 慢动作 / 推镜头 / 关键帧 | `scripts/fx.py` / `scripts/keyframe.py` | 03 effects |
| J-cut / L-cut / 倒放 / 多机位 | `scripts/speed.py` / `scripts/reverse.py` / `scripts/multicam.py` | 04 cinematic |
| 调色 / 风格迁移 / HDR | `scripts/color_style.py` / `scripts/style_transfer.py` / `scripts/hdr_io.py` | 05 color |
| 烧字幕 / 变声 / 翻译 | `scripts/auto_subtitle.py` / `scripts/voice_change.py` / `scripts/translate.py` | 06 text |
| BGM 循环 / 节拍卡点 | `scripts/bgm_loop.py` / `scripts/beat_sync.py` | 07 audio |
| AI 封面 | `scripts/cover_ai.py` | 08 cover |
| AI 抠图 / 金句 / 场景 / 蒙版 / 画中画 / 重新构图 | `scripts/cutout.py` / `scripts/quotes.py` / `scripts/scene_detect.py` / `scripts/mask.py` / `scripts/overlay.py` / `scripts/reframe.py` | 09 ai-features |
| **去水词** | `scripts/remove_fillers.py` | 09 ai-features |
| **美颜** | `scripts/beauty.py` | 🆕 12 beauty |
| **改词翻唱** | `scripts/rewrite_audio.py` | 🆕 13 rewrite-audio |
| **文字成片** | `scripts/text_to_video.py` | 🆕 14 text-to-video |
| **数字人** | `scripts/digital_human.py` | 🆕 15 digital-human |
| 批量处理 | `scripts/batch.py` | 10 batch |
| 完整 vlog 流水线 | `scripts/pipeline_vlog.py` | 11 pipelines |

---

## 下一步

- 看 [VS_JIANYING.md](VS_JIANYING.md) — vs 剪映的能力对比(智剪工坊 5 个差异化功能)
- 看 [FAQ.md](FAQ.md) — 常见问题排查
- 看 [FEATURE_COMPARISON.md](FEATURE_COMPARISON.md) — vs 剪映/Pr/Resolve/FCP 全维度对比
- 看 `references/*.md` — 各子技能详细文档
