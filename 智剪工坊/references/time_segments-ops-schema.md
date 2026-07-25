# time_segments ops schema · 段级操作定义

> **v2.0 新增**: `videos[i].time_segments[j].ops` 字段定义
> **何时加载**: HTML 渲染段操作面板时 + AI 解析 intent.json 时
> **目的**: 单一真相源,HTML 与 AI 共享同一份 op 列表

## 1. 设计原则

1. **未设置时** → 段继承 `videos[i].video_ops`(整段操作)
2. **设置时** → 段用 `time_segments[j].ops` 覆盖
3. **每个 op 必须带 `note` 字段**(用户人类语言填写,JSON 解析后供 LLM 讨论)

## 2. 段级 op 完整列表(14 个 + voice mode)

| op 名 | 参数 | 路由 CLI | 适用场景 |
|---|---|---|---|
| `speed-up` | `{on, factor>1}` | `video_speed.py` | 段内加速 |
| `slow-down` | `{on, factor<1}` | `video_speed.py` | 段内减速 |
| `reverse` | `{on}` | `video_reverse.py` | 段内倒放 |
| `mute` | `{on}` | `audio_bgm.py --video-volume 0` | 段内静音 |
| `fade-in` | `{on, sec}` | `video_fade.py --fade-in` | 段开头淡入 |
| `fade-out` | `{on, sec}` | `video_fade.py --fade-out` | 段结尾淡出 |
| `color` | `{on, preset}` | `video_color.py` | 段内调色(13 预设) |
| `asr-transcribe` | `{on, model, lang}` | `asr/transcribe.py` | 段内 ASR 转录 |
| `asr-burn` | `{on, font_size}` | `asr/burn_subtitle.py` | 段内烧字幕 |
| `asr-speaker` | `{on}` | `asr/speaker_srt.py` | 段内说话人标签 |
| `audio-denoise` | `{on}` | `audio/denoise.py` | 段内降噪 |
| `audio-separate` | `{on, model}` | `audio/separate.py` | 段内声源分离 |
| `audio-diarize` | `{on}` | `audio/diarize.py` | 段内说话人分离 |
| `voice-filler-removed` | `{on}` | **暂无 CLI** | 段内去水词(v2 待实现) |
| `voice` *(mode)* | `keep` / `keep-with-filler-removed` / `mute` / `bgm-only` / `original-with-bgm` | `audio_bgm.py` | 段级音频策略 |
| `note` *(every op)* | 任意自然语言 | — | 自由文本,JSON 解析后供 LLM 讨论 |

## 3. 完整 JSON Schema 范式

### 3.1 单 op 范式(每 op 自带 note 字段)

```json
{
  "time_segments": [
    {
      "id": "seg_1_1",
      "label": "静音段",
      "start_sec": 10.0,
      "end_sec": 30.0,
      "ops": {
        "mute": {
          "on": true,
          "note": "原始音频有杂音,客户要求这段静音"
        },
        "speed-up": {
          "on": true,
          "factor": 2.0,
          "note": "加快节奏让短视频更紧凑"
        }
      },
      "note": "本段是开场引子,需要特殊处理"
    }
  ]
}
```

### 3.2 多 op 范式(同段多个独立 op)

```json
{
  "time_segments": [
    {
      "id": "seg_1_2",
      "start_sec": 5.0,
      "end_sec": 20.0,
      "ops": {
        "asr-transcribe": { "on": true, "model": "medium", "lang": "zh", "note": "转录对话内容" },
        "asr-burn":       { "on": true, "font_size": 24, "note": "烧中文字幕" },
        "audio-denoise":  { "on": true, "note": "环境噪音需要降噪" }
      }
    }
  ]
}
```

### 3.3 voice 模式(段级音频策略)

```json
{
  "time_segments": [
    {
      "id": "seg_1_3",
      "start_sec": 30.0,
      "end_sec": 60.0,
      "ops": {
        "voice": { "mode": "keep-with-filler-removed", "note": "保留对话但去水词" }
      }
    }
  ]
}
```

`voice.mode` 枚举:

| 值 | 含义 | 路由 |
|---|---|---|
| `keep` | 保留原声 | `audio_bgm.py` 默认 |
| `keep-with-filler-removed` | 保留 + 去水词 | `asr/remove_filler.py`(v2 待实现) |
| `mute` | 静音 | `audio_bgm.py --video-volume 0` |
| `bgm-only` | 只留 BGM | `audio_bgm.py --mix bgm` |
| `original-with-bgm` | 原声 + BGM 混合 | `audio_bgm.py --mix both` |

## 4. AI 路由表(补充 `time_segments[].ops` 路由)

> 原 `AI路由表-意图JSON字段枚举.md` 的 op 白名单(整段型)v1.19 起扩展为段级支持。
> AI 看到 `time_segments[j].ops.<op_name>` 时,**复用同一组 CLI**,但参数起始时间从 0 改为段内偏移(seg.start_sec)。

| `time_segments[j].ops.<op>` | atomic CLI | 段内偏移说明 |
|---|---|---|
| `speed-up` / `slow-down` | `video_speed.py` | 整段应用,无需偏移 |
| `reverse` | `video_reverse.py` | 整段 |
| `mute` | `audio_bgm.py --video-volume 0` | 整段 |
| `fade-in` | `video_fade.py --fade-in N` | 段开头 N 秒 |
| `fade-out` | `video_fade.py --fade-out N` | 段结尾 N 秒 |
| `color` | `video_color.py` | 整段应用 |
| `asr-transcribe` | `asr/transcribe.py` | 段范围切片 |
| `asr-burn` | `asr/burn_subtitle.py` | 段范围切片 |
| `asr-speaker` | `asr/speaker_srt.py` | 段范围切片 |
| `audio-denoise` | `audio/denoise.py` | 段范围切片 |
| `audio-separate` | `audio/separate.py` | 段范围切片 |
| `audio-diarize` | `audio/diarize.py` | 段范围切片 |
| `voice-filler-removed` | **暂无 CLI**(v2 待实现) | — |
| `voice` | `audio_bgm.py` | 段范围 |

## 5. HTML UI 约定(从 schema 动态渲染)

- 段操作面板(`openSegmentPanel`)从 `SEGMENT_OPS_SCHEMA` 动态生成 UI
- 每个 op:
  - checkbox(`on: true/false`)
  - 参数 input(number / text / select 按 op 类型)
  - textarea(`note` 字段,用户自由填写)
- 删除单个 op:每个 op 行有 × 按钮
- 不硬编码 UI(单一真相源 = `SEGMENT_OPS_SCHEMA`)

## 6. 覆盖优先级(段 vs 整段)

```
执行顺序(AI 必读):
1. 先应用 videos[i].video_ops(整段)
2. 再覆盖 time_segments[j].ops(段级)
   - 如果该 op 在 video_ops 也设置,段级覆盖
   - 如果该 op 只在 video_ops 设置,段继承
   - 如果该 op 只在 time_segments[].ops 设置,段独立
3. 同 op 多次出现 → 取最深的(time_segments[].ops 优先)
```

## 7. 校验规则(AI 必读)

- `time_segments[j].ops` 每个 op **必须**含 `on: bool`(HTML 渲染判定)
- 数字参数(factor/sec/font_size)必须 > 0
- 段区间 `[start_sec, end_sec]` 必须严格在视频时长内
- 多 time_segments 不能重叠(`exclude` 模式除外,v2.5 引入)
