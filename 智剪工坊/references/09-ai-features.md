# 09-ai-features - AI 智能剪辑 — v1.2 已实现

> **对应脚本**: `scripts/ai_cutout.py` + `scripts/ai_quotes.py` + `scripts/video_scene.py` + `scripts/video_mask.py` + `scripts/video_overlay.py` + `scripts/video_reframe.py` + `scripts/ai_fillers.py`
> **触发词**: "AI 剪辑"、"智能剪辑"、"AI 抠图"、"自动找金句"、"金句"、"节拍卡点"、"自动字幕"、"人脸追踪"、"换背景"、"去水词"
> **实测状态**: ✅ 验证通过

---

## 1. 调用范式

### 场景 1

```bash
# AI 抠图(rembg)
python scripts/ai_cutout.py --input v.mp4 --output no_bg.mp4

# 金句检测(NLP)
python scripts/ai_quotes.py --input v.mp4 --top 5

# 场景检测(OpenCV 帧差)
python scripts/video_scene.py --input v.mp4 --threshold 0.3

# 蒙版(face / box)
python scripts/video_mask.py --input v.mp4 --type face --output masked.mp4

# 画中画(overlay)
python scripts/video_overlay.py --base a.mp4 --overlay b.mp4 --position top_right --output pip.mp4

# 重新构图(9:16 / 1:1 / 16:9)
python scripts/video_reframe.py --input v.mp4 --target 9:16 --output reframed.mp4

# 🆕 去水词(L2 word-level,需要 agent 标水词)
python scripts/ai_fillers.py transcribe --input vlog.mp4 --srt vlog.srt
python scripts/ai_fillers.py cut --input vlog.mp4 --srt vlog.srt --output clean.mp4 --remove-words "1,3,11"
```

### 场景 2

```bash
pip install faster-whisper rembg mediapipe librosa opencv-python
```

## 2. 参数

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--input` | `-i` | (必填) | 输入视频/音频/图片 |
| `--output` | `-o` | (必填) | 输出路径 |

## 3. 常见错误 / 限制

1. **AI 处理慢**:rembg / MediaPipe 比 ffmpeg 慢得多,慎用全片
2. **依赖包**:rembg / mediapipe / librosa 需要单独安装
3. **GPU 加速**:部分 AI 库支持 CUDA,配置复杂
4. **准确度**:AI 自动剪辑的金句不一定都好用,需要人工筛选

## 4. 相关参考

- **SKILL.md §14 子技能索引**：本子技能的路由表
- **scripts/README.md**：scripts/ 目录命名规范（`<维度>_<动作>.py`）
- `.archive/CHANGELOG.md`：本子技能历史变更

---

<details>
<summary>📋 原文存档（v0.5 旧版，仅供 git history 追溯）</summary>

# 09 - ai-features (AI 智能剪辑) — v0.5 已实现

> **对应脚本:** 7 个 — `cutout.py` / `quotes.py` / `scene_detect.py` / `mask.py` / `overlay.py` / `reframe.py` / `remove_fillers.py`
> **实测状态:** ✅ 验证通过

```bash
# AI 抠图(rembg)
python scripts/ai_cutout.py --input v.mp4 --output no_bg.mp4

# 金句检测(NLP)
python scripts/ai_quotes.py --input v.mp4 --top 5

# 场景检测(OpenCV 帧差)
python scripts/video_scene.py --input v.mp4 --threshold 0.3

# 蒙版(face / box)
python scripts/video_mask.py --input v.mp4 --type face --output masked.mp4

# 画中画(overlay)
python scripts/video_overlay.py --base a.mp4 --overlay b.mp4 --position top_right --output pip.mp4

# 重新构图(9:16 / 1:1 / 16:9)
python scripts/video_reframe.py --input v.mp4 --target 9:16 --output reframed.mp4

# 🆕 去水词(L2 word-level,需要 agent 标水词)
python scripts/ai_fillers.py transcribe --input vlog.mp4 --srt vlog.srt
python scripts/ai_fillers.py cut --input vlog.mp4 --srt vlog.srt --output clean.mp4 --remove-words "1,3,11"
```

---

## 触发词

"AI 剪辑"、"智能剪辑"、"金句"、"自动找金句"、"节拍卡点"、"AI 抠图"、"自动字幕"、"人脸追踪"、"换背景"

## 包含的 AI 能力

| 能力 | 工具 | 用途 |
|---|---|---|
| 自动找金句 | Whisper + NLP | 从视频中找"最有冲击力"的几句话 |
| 节拍卡点 | librosa | 分析 BGM 节拍,自动剪切对齐 |
| AI 抠图 | rembg | 把人物从背景抠出来 |
| 人脸追踪 | OpenCV / MediaPipe | 跟踪人脸,自动添加贴纸/放大 |
| 自动字幕 | Whisper + ffmpeg drawtext | 转录音频 + 烧字幕 |
| 风格迁移 | OpenCV / Stable Diffusion | 把视频风格转成参考视频风格 |

## A. 自动找金句(从第一性原理)

**核心逻辑:**
1. Whisper 转录所有音频,获取每句话 + 时间戳
2. NLP 分析:情绪强度、关键词、数字、修辞
3. 排序选 Top-N"金句",输出时间戳列表
4. ffmpeg 按时间戳剪切 + 拼接

```python
# scripts/find_quotes.py
import json
from faster_whisper import WhisperModel

def transcribe_with_timestamps(audio_path):
    model = WhisperModel("medium", device="cuda")
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    
    result = []
    for segment in segments:
        result.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": [{"word": w.word, "start": w.start, "end": w.end} 
                      for w in segment.words]
        })
    return result

def score_quality(segment):
    text = segment["text"]
    score = 0
    
    # 含数字(金句常用)
    if any(c.isdigit() for c in text):
        score += 2
    
    # 短句(< 10 字)更有冲击力
    if len(text) < 10:
        score += 1
    
    # 关键词加权
    keywords = ["坚持", "放弃", "3650", "一定", "相信", "为什么"]
    for kw in keywords:
        if kw in text:
            score += 3
    
    return score
```

## B. 节拍卡点(对位 BGM)

```python
# scripts/audio_beat.py
import librosa
import numpy as np

def get_beats(audio_path):
    y, sr = librosa.load(audio_path)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return beat_times, tempo

def cut_to_beats(video_path, beat_times, output_path):
    """按节拍点剪切视频(每个 beat 一段)"""
    # 用 ffmpeg 按 beat_times 切片
    pass
```

## C. AI 抠图(rembg)

```python
# scripts/ai_cutout.py
from rembg import remove
import cv2

def remove_background(input_path, output_path):
    img = cv2.imread(input_path)
    out = remove(img)
    cv2.imwrite(output_path, out)
```

或者用 OpenCV + GrabCut(传统方法):

```python
import cv2
import numpy as np

def grabcut_cutout(input_path, output_path):
    img = cv2.imread(input_path)
    mask = np.zeros(img.shape[:2], np.uint8)
    
    # 定义前景矩形(用户大致框选)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    rect = (50, 50, img.shape[1]-50, img.shape[0]-50)
    
    cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask==2)|(mask==0), 0, 1).astype('uint8')
    
    result = img * mask2[:, :, np.newaxis]
    cv2.imwrite(output_path, result)
```

## D. 人脸追踪(OpenCV / MediaPipe)

```python
# scripts/face_track.py
import cv2
import mediapipe as mp

def track_face_centers(video_path):
    cap = cv2.VideoCapture(video_path)
    mp_face = mp.solutions.face_detection
    
    centers = []
    with mp_face.FaceDetection() as face_detector:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detector.process(rgb)
            
            if results.detections:
                det = results.detections[0]
                bbox = det.location_data.relative_bounding_box
                x = int(bbox.xmin * frame.shape[1])
                y = int(bbox.ymin * frame.shape[0])
                w = int(bbox.width * frame.shape[1])
                h = int(bbox.height * frame.shape[0])
                cx, cy = x + w//2, y + h//2
                centers.append((cx, cy))
    
    cap.release()
    return centers
```

## E. 自动字幕(已经做过)

详见 [06-text.md](06-text.md)。流程:
1. Whisper 转录(带时间戳)
2. 生成 SRT
3. ffmpeg subtitles filter 烧录

## F. 风格迁移(进阶)

```python
# scripts/video_style.py
import cv2
import numpy as np

def transfer_style(frame, style_frame):
    # 用 OpenCV 实现简单风格迁移
    # 或者调用 Stable Diffusion API
    pass
```

## 调用示例

```
用户: "从这段视频里自动找出 5 句金句"
→ ai-features --task find-quotes --input video.mp4 --top 5
```

```
用户: "把这段视频按 BGM 节拍剪成 30 段"
→ ai-features --task beat-sync --input video.mp4 --bgm bgm.mp3 --segments 30
```

```
用户: "把视频里的人从背景抠出来"
→ ai-features --task cutout --input video.mp4 --output no_bg.mp4
```

## 限制 / 注意

1. **AI 处理慢**:rembg / MediaPipe 比 ffmpeg 慢得多,慎用全片
2. **依赖包**:rembg / mediapipe / librosa 需要单独安装
3. **GPU 加速**:部分 AI 库支持 CUDA,配置复杂
4. **准确度**:AI 自动剪辑的金句不一定都好用,需要人工筛选

## 依赖安装

```bash
pip install faster-whisper rembg mediapipe librosa opencv-python
```

</details>
