# Jargon 大白话词典

> 本词典记录用户口语 → 智剪工坊路由的映射。
> SKILL.md 路由表精简版见 §子技能索引；详细路由见本文件 + `references/AI路由表-意图JSON字段枚举.md`。

## 用户口语 → 路由

| 用户说的 | 实际指 | 路由 |
|---|---|---|
| "剪头/剪尾" | trim-head / trim-tail | `scripts/video/trim.py` (旧 `processing.py` v1.7 改名) |
| "去掉中间" | cut-middle | `scripts/video/trim.py` (旧 `processing.py` v1.7 改名) |
| "保留某段" | pin-range | `scripts/video/trim.py` (旧 `processing.py` v1.7 改名) |
| "加转场" | sequences[].transitions | `scripts/video/xfade.py` |
| "加 BGM" | audio-mix | `scripts/audio/mix.py` |
| "变声" | audio-voice | `scripts/audio/voice.py` |
| "节拍卡点" | audio-beat | `scripts/audio/beat.py` |
| "提取音频" | audio-extract | `scripts/audio/extract.py` |
| "音频降噪/降噪" | audio-denoise | `scripts/audio/denoise.py` |
| "声源分离/提取人声" | audio-separate | `scripts/audio/separate.py` (v1.7 调 `lib/separate_demucs.py` GPU) |
| "说话人分离/谁说了什么" | audio-diarize | `scripts/audio/diarize.py` (v1.7 调 `lib/asr/pyannote.py` 需 HF token) |
| "ASR/语音转文字" | asr-transcribe | `scripts/asr/transcribe.py` (v1.7 调 `lib/asr/whisper.py` GPU) |
| "环境检查/环境体检/智剪工坊检查/检查环境" | env-check | `tools/download_whisper_model.py --status` + 检查 3 个 HF env(触发 SKILL.md "🤖 AI 加载技能主动环境体检"小节) |
| "烧字幕" | asr-burn | `scripts/asr/burn_subtitle.py` (v1.6 调 `lib/ffmpeg/video/subtitle.py`) |
| "带说话人的字幕" | asr-speaker | `scripts/asr/speaker_srt.py` |
| "去水词/去口头禅/嗯啊" | voice-filler-removed | **（v1.19 待实现）** HTML UI 已加, CLI 待写 |
| "配字幕" | subtitle | `scripts/asr/transcribe.py` + `scripts/asr/burn_subtitle.py` |
| "做封面" | cover | `scripts/ai/cover.py` |
| "调色" | color | `scripts/video/color.py` |
| "推镜头" | speed-up / cinematic-zoom | `scripts/video/speed.py` (旧 `processing.py` v1.7 改名) |
| "加文字" | opening-text / ending.text | `scripts/video/opening.py` |
| **counter-rotate** | 像素反转（抵消 metadata）| `lib/video_processing.py` 自动处理（旧 `processing.py` v1.7 改名）|
| **aspect-fill / aspect-fit** | 填满 vs 加黑边 | `lib/video_processing.py`（旧 `processing.py` v1.7 改名）|

## 使用方法

1. AI 收到用户口语化指令
2. 在本词典查匹配项
3. 路由到对应 `scripts/*.py`
4. 不匹配项 → 标记为 F 象限（不支持），告知用户