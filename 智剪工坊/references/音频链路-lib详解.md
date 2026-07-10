# 音频链路 — BGM + 变声 + 节拍 + 提取 + 降噪 + 声源分离 + 说话人分离

> **对应脚本**：`scripts/audio/*.py`（7 个用户可见脚本）
> **底层依赖**：`lib/ffmpeg/audio/*.py`（10 个 lib 文件，70+ 个函数）
> **触发词**：BGM / 加音乐 / 混音 / 变声 / 老声 / 童声 / 节拍卡点 / 提取音频 / 音频降噪 / 降噪 / 声源分离 / 提取人声 / 说话人分离 / 区分说话人
> **v1.4 新增链路** | **v1.5 全部下沉到 lib**

---

## 1. 链路架构

```
video / audio file
    ↓
┌─────────────────────────────────────────┐
│ scripts/audio/*.py（用户可见 CLI）     │
│   mix / voice / beat / extract          │
│   denoise / separate / diarize          │
└─────────────────────────────────────────┘
    ↓ 调
┌─────────────────────────────────────────┐
│ lib/ffmpeg/audio/*.py（底层 lib）      │
│   denoise / enhance / detect            │
│   normalize / transform / channel       │
│   visualize / effect / utility / measure│
│   extract                              │
└─────────────────────────────────────────┘
    ↓ 调
ffmpeg
```

**v1.5 之前**：scripts/audio/*.py 直接拼 ffmpeg 命令
**v1.5 之后**：scripts/audio/*.py 调 lib，lib 调 ffmpeg

---

## 2. 7 个用户可见脚本

### 2.1 `mix.py` — BGM 混音（L1 合成）

```bash
# 基本用法
python scripts/audio/mix.py --input v.mp4 --bgm b.mp3 --output out.mp4

# 时间段 + 淡入淡出
python scripts/audio/mix.py --input v.mp4 --bgm b.mp3 \
    --start 10 --end 20 --bgm-fade-in 1 --bgm-fade-out 2 --output out.mp4

# 时长不匹配处理（4 种模式）
python scripts/audio/mix.py --input v.mp4 --bgm b.mp3 \
    --match-mode truncate --output out.mp4
python scripts/audio/mix.py --input v.mp4 --bgm b.mp3 \
    --match-mode silence-end --output out.mp4
```

底层调用：`lib.ffmpeg.audio.{mix_streams, adelay, apad, fade_in_out}`

### 2.2 `voice.py` — 变声（L2 变换）

```bash
python scripts/audio/voice.py --input in.mp4 --type old_man --output out.mp4
python scripts/audio/voice.py --input in.mp4 --pitch 1.5 --output out.mp4
```

预设：old_man / child / robot / female / male / whisper / chipmunk / deep

底层调用：`lib.ffmpeg.audio.transform.{change_pitch, add_tremolo}`

### 2.3 `beat.py` — 节拍分析（L2 变换）

```bash
python scripts/audio/beat.py --analyze --bgm music.mp3 --output beats.json
python scripts/audio/beat.py --input v.mp4 --bgm music.mp3 --output sync.mp4
```

依赖：librosa（不是 ffmpeg，所以不调 lib）

### 2.4 `extract.py` — 音频提取（L3 提取）

```bash
python scripts/audio/extract.py extract -i v.mp4 -o audio.wav
python scripts/audio/extract.py extract -i v.mp4 -o audio.mp3 --format mp3
python scripts/audio/extract.py fade -i v.mp4 -o out.mp4 --fade-in 2 --fade-out 3
```

底层调用：`lib.ffmpeg.audio.extract.{extract_audio, fade_audio}`

### 2.5 `denoise.py` — 降噪（L4 降噪）

```bash
# 6 种模式
python scripts/audio/denoise.py --input noisy.wav --output clean.wav --mode afftdn
python scripts/audio/denoise.py --input noisy.wav --output clean.wav --mode rnnoise
python scripts/audio/denoise.py --input noisy.wav --output clean.wav --mode light
python scripts/audio/denoise.py --input noisy.wav --output clean.wav --mode aggressive
python scripts/audio/denoise.py --input noisy.wav --output clean.wav --mode wavelet
python scripts/audio/denoise.py --input noisy.wav --output clean.wav --mode aap

# 视频降噪 + 提取音频（链式）
python scripts/audio/denoise.py --input v.mp4 --output voice.wav --mode afftdn --extract-voice
```

底层调用：`lib.ffmpeg.audio.denoise.{denoise_fft, denoise_wavelet, denoise_rnn, aap_denoise, ...}`

### 2.6 `separate.py` — 声源分离（L4 分离）

```bash
# Demucs 完整分离
python scripts/audio/separate.py --input audio.wav --output-dir ./separated

# 只提取人声
python scripts/audio/separate.py --input audio.wav --output vocals.wav --stem vocals

# 指定模型
python scripts/audio/separate.py --input audio.wav --output-dir ./separated --model htdemucs_ft
```

依赖：Demucs（不是 ffmpeg）

### 2.7 `diarize.py` — 说话人分离（L5 说话人）

```bash
# pyannote（推荐）
python scripts/audio/diarize.py --input vocals.wav --output diar.json

# 指定说话人数量
python scripts/audio/diarize.py --input vocals.wav --output diar.json \
    --min-speakers 1 --max-speakers 4
```

依赖：pyannote.audio（不是 ffmpeg）

### 2.8 `voice_extract.py` — 人声提取（v1.5 新增）

用 ffmpeg 内置 dialoguenhance 提取人声，无需模型。

```bash
# 基本提取
python scripts/audio/voice_extract.py -i video.mp4 -o voice.wav

# 调整强度（level 0=不处理，1=最强）
python scripts/audio/voice_extract.py -i video.mp4 -o voice.wav --level 0.7
```

底层调用：`lib.ffmpeg.audio.enhance.enhance_dialog`
适用场景：BGM 较小的视频；BGM 很大的复杂场景改用 `separate.py`（Demucs）

### 2.9 `silence_split.py` — 静音检测与自动分段（v1.5 新增）

用 ffmpeg silencedetect 找静音段，自动分段。

```bash
# 只检测（输出 segments.json）
python scripts/audio/silence_split.py detect -i audio.wav -o segments.json

# 检测 + 自动切分（输出 segments/ 目录）
python scripts/audio/silence_split.py split -i audio.wav -o segments/

# 调整参数
python scripts/audio/silence_split.py detect -i audio.wav -o seg.json \
    --threshold -40 --min-duration 1.0
```

底层调用：`lib.ffmpeg.audio.detect.detect_silence`

### 2.10 `loudness_norm.py` — 响度归一（v1.5 新增）

EBU R128 响度标准归一化，适合 podcast / 流媒体 / 跨平台播放。

```bash
# 默认 EBU R128 (-23 LUFS)
python scripts/audio/loudness_norm.py -i audio.wav -o normalized.wav

# 流媒体 (-16 LUFS)
python scripts/audio/loudness_norm.py -i audio.wav -o out.wav --target -16

# 视频
python scripts/audio/loudness_norm.py -i video.mp4 -o video_loud.mp4
```

底层调用：`lib.ffmpeg.audio.normalize.normalize_loudnorm`

支持标准：
- **-23 LUFS**：EBU R128 广播标准（Europe/UK）
- **-16 LUFS**：流媒体（Spotify/Apple Music）
- **-14 LUFS**：YouTube
- **-20 LUFS**：播客常用

---

## 3. lib 底层的 10 个文件

| 文件 | 函数数 | 核心能力 |
|---|---|---|
| `denoise.py` | 6 | FFT/小波/神经网络/仿射投影降噪 |
| `enhance.py` | 7 | 对话增强/去齿音/带通/EQ |
| `detect.py` | 4 | 静音检测/音量/统计/相位 |
| `normalize.py` | 5 | Loudnorm/动态归一/音量 |
| `transform.py` | 12 | 变调/变速/合唱/颤音 |
| `channel.py` | 10 | 立体声扩展/声道映射/amix/amerge |
| `visualize.py` | 8 | 波形/频谱/CQT/音量条 |
| `effect.py` | 9 | 回声/压缩/DC偏移 |
| `utility.py` | 3 | adelay/apad/compensationdelay ⭐ |
| `measure.py` | 4 | PSNR/SDR/互相关 |
| `extract.py` | 2 | extract_audio/fade_audio |
| **合计** | **70** | |

调用范式：

```python
# 顶层统一调用
from lib.ffmpeg.audio import denoise_fft, enhance_dialog

# 子模块调用
from lib.ffmpeg.audio.detect import detect_silence
from lib.ffmpeg.audio.visualize import waveform_video
```

---

## 4. 典型使用场景

### 场景 1: 清理录制视频的音频

```python
from lib.ffmpeg.audio import denoise_fft, normalize_loudnorm

denoise_fft("noisy.wav", "clean.wav", nr=10, nf=-25)
normalize_loudnorm("clean.wav", "final.wav", target_lufs=-23)
```

### 场景 2: 纯 ffmpeg 人声提取（不需要 demucs）

```python
from lib.ffmpeg.audio import enhance_dialog

enhance_dialog("video_with_bgm.mp4", "voice_only.wav", level=0.7)
```

### 场景 3: 多步音频清理

```python
from lib.ffmpeg.audio import (
    denoise_fft,        # 降噪
    highpass,           # 切低频噪音
    normalize_loudnorm, # 响度归一
    detect_silence,     # 检测静音段
)

denoise_fft("raw.wav", "step1.wav")
highpass("step1.wav", "step2.wav", frequency=80)
normalize_loudnorm("step2.wav", "final.wav")

# 检测静音（返回结构化数据，不输出文件）
result = detect_silence("final.wav", threshold=-30)
print(f"静音段数: {result['silence_count']}")
```

---

## 5. 返回值规范

所有 lib 函数统一返回 `(success: bool, output_path_or_dict)`：

| 类型 | 返回 |
|---|---|
| 处理类 | `(True, "/path/to/output.wav")` |
| 检测类 | `(True, {"silence_count": 5, "segments": [...]})` |
| 失败 | `(False, "error message")` |

---

## 6. 完整链路（v1.5 标准）

```
# 多人对话视频 → 带说话人的字幕视频
1. extract.py       → 音频流
2. denoise.py       → 降噪
3. separate.py      → 提取人声
4. diarize.py       → 标记说话人
5. asr/transcribe.py → SRT
6. asr/speaker_srt.py → 带说话人的 SRT
7. asr/burn_subtitle.py → 烧字幕到视频
```

详细链路见 `references/ASR链路-声源分离说话人分离Whisper烧字幕.md`

---

## 7. 历史

- **v1.4**：链路补全，新增降噪/声源分离/说话人分离
- **v1.5**：scripts/audio/*.py 调 lib/ffmpeg/audio/*.py（分层架构）