# scripts/ 目录索引

> **v1.2 命名规范**：所有脚本按 `<维度>_<动作>.py` 命名，AI 看到文件名就能识别属于哪个能力维度。
>
> **维度**（按技术栈/子系统分类，跟 SKILL.md §14 子技能索引不同）：
> - `video_*` — 视频处理（依赖 ffmpeg）
> - `audio_*` — 音频处理（依赖 ffmpeg / matrix TTS）
> - `ai_*` — AI 能力（依赖 matrix MCP / mediapipe）
> - `batch` — 跨域批量编排
> - `edit` — 14 原子操作（CLI 多子命令）
> - `pipeline_*` — 阶段流程编排（v1.0 step1~5）

**AI 路由路径**：**不要按文件名猜能力**——回到 SKILL.md §14 子技能索引找对应子技能。

---

## 视频处理（video_*）

| 脚本 | 旧名 | 对应子技能 |
|---|---|---|
| `video_trim.py` | cut.py | 01 cutting（剪切 + 拼接） |
| `video_xfade.py` | xfade.py | 02 transitions（转场） |
| `video_fx.py` | fx.py | 03 effects（视觉特效） |
| `video_keyframe.py` | keyframe.py | 03 effects |
| `video_speed.py` | speed.py | 04 cinematic（变速） |
| `video_reverse.py` | reverse.py | 04 cinematic（倒放） |
| `video_multicam.py` | multicam.py | 04 cinematic（多机位） |
| `video_color.py` | color_style.py | 05 color（调色） |
| `video_hdr.py` | hdr_io.py | 05 color（HDR） |
| `video_style.py` | style_transfer.py | 05 color（风格迁移） |
| `video_scene.py` | scene_detect.py | 09 ai-features（场景检测） |
| `video_mask.py` | mask.py | 09 ai-features（蒙版） |
| `video_overlay.py` | overlay.py | 09 ai-features（画中画） |
| `video_reframe.py` | reframe.py | 09 ai-features（重新构图） |
| `video_subtitle.py` | auto_subtitle.py | 06 text（自动字幕） |
| `video_opening.py` | opening_text.py | 06 text（片头文字） |

## 音频处理（audio_*）

| 脚本 | 旧名 | 对应子技能 |
|---|---|---|
| `audio_bgm.py` | bgm_loop.py | 07 audio（BGM 循环 + 淡入淡出 + 降噪） |
| `audio_beat.py` | beat_sync.py | 07 audio（节拍卡点） |
| `audio_voice.py` | voice_change.py | 06 text（变声） |

## AI 能力（ai_*）

| 脚本 | 旧名 | 对应子技能 |
|---|---|---|
| `ai_beauty.py` | beauty.py | 12 beauty（美颜） |
| `ai_fillers.py` | remove_fillers.py | 09 ai-features（去水词） |
| `ai_cover.py` | cover_ai.py | 08 cover（AI 封面） |
| `ai_digital_human.py` | digital_human.py | 15 digital-human（数字人） |
| `ai_quotes.py` | quotes.py | 09 ai-features（金句检测） |
| `ai_cutout.py` | cutout.py | 09 ai-features（AI 抠图） |
| `ai_rewrite.py` | rewrite_audio.py | 13 rewrite-audio（改词翻唱） |
| `ai_text_to_video.py` | text_to_video.py | 14 text-to-video（文字成片） |
| `ai_translate.py` | translate.py | 06 text（翻译） |

## 批量处理（batch）

| 脚本 | 旧名 | 对应子技能 |
|---|---|---|
| `batch.py` | batch.py | 10 batch |

## 14 原子操作（edit）

| 脚本 | 旧名 | 对应子技能 |
|---|---|---|
| `edit.py` | edit.py | 16 edit（14 子命令） |

## 流程编排（pipeline_*）

| 脚本 | 旧名 | 调用于 |
|---|---|---|
| `pipeline_step1_check.py` | step1_check_intent.py | §阶段 2 Step 1（解析 + 自检） |
| `pipeline_step2_asr.py` | step2_1_asr.py | §阶段 2 Step 2.1（ASR 优先） |
| `pipeline_step2_process.py` | step2_2_process.py | §阶段 2 Step 2.2（单视频处理） |
| `pipeline_step3_assemble.py` | step3_assemble.py | §阶段 2 Step 3（sequence 拼接） |
| `pipeline_step4_review.py` | step4_fallback.py | §阶段 2 Step 4（模糊项兜底） |
| `pipeline_step5_decide.py` | step5_decision.py | §阶段 2 Step 5（决策报告） |

---

## 命名约定（v1.2 起）

```
<dimension>_<action>.py
```

- **dimension**：6 个值之一（`video` / `audio` / `ai` / `batch` / `edit` / `pipeline`）
- **action**：动词短语（小写 + 下划线），描述"做什么"
- **不适用**：单字名（`cut.py`、`fx.py`）、混合风格名（`color_style.py`、`bgm_loop.py`）已废弃

## 添加新脚本 checklist

1. 选 dimension（video/audio/ai/batch/edit/pipeline）
2. 命名 `<dimension>_<动作>.py`
3. 加 SKILL.md §14 子技能索引（如是新能力）或 §主体流程（如是 step 脚本）
4. 加 references/XX.md（如需详细文档）
5. 在本 README.md 表格加一行

## 调用约定

```bash
# 标准调用
python scripts/<script>.py --input in.mp4 --output out.mp4 [options]

# 短选项（v1.2 起）
python scripts/video_trim.py -i in.mp4 -o out.mp4 --start 30 --duration 20

# 子命令（edit.py）
python scripts/edit.py remove -i v.mp4 -o out.mp4 --mode head --seconds 3

# 流程（pipeline）
python scripts/pipeline_step1_check.py /path/to/intent.json
```