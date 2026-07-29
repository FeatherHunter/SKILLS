# time_segments ops schema · 段级操作定义

> **v3.0 修订(2026-07-29)**: `videos[i].time_segments[j].ops` 字段定义,段内 op 白名单与 spec §7 对齐。
> **何时加载**: HTML 渲染段操作面板时 + AI 解析 intent.json 时
> **目的**: 单一真相源,HTML 与 AI 共享同一份 op 列表

## 1. 设计原则

1. **未设置时** → 段继承 `videos[i].video_ops`(整段操作)
2. **设置时** → 段用 `time_segments[j].ops` 覆盖
3. **每个 op 必须带 `note` 字段**(用户人类语言填写,JSON 解析后供 LLM 讨论)
4. **段内 op 白名单**(spec §7 校验规则):`mute` / `speed-up` / `slow-down` / `reverse` / `color-grade`(5 个)
   - 不在白名单 = HTML `validateIntent` + JSON Schema 都拒绝
   - 常见误用:`color`(无 `-grade` 后缀) → 拒绝,应改 `color-grade`;`user`(HTML 拆段内部标记) → 不应进 JSON

## 2. 段级 op 白名单(spec §7 · v3.0 校验通过)

| op 名 | 参数 | 路由 CLI | 适用场景 |
|---|---|---|---|
| `mute` | `{on}` | `audio_bgm.py --video-volume 0` | 段内静音 |
| `speed-up` | `{on, factor>1}` | `video_speed.py` | 段内加速 |
| `slow-down` | `{on, factor<1}` | `video_speed.py` | 段内减速 |
| `reverse` | `{on}` | `video_reverse.py` | 段内倒放 |
| `color-grade` | `{on, preset}` | `video_color.py` | 段内调色(13 预设,如 warm/cool/cinematic/vintage 等) |
| `note` *(每 op)* | 任意自然语言 | — | 自由文本,JSON 解析后供 LLM 讨论 |

> **历史说明**:v1.x 时段内 op 有 14 个(含 `fade-in/out`/`asr-*`/`audio-*`/`voice-filler-removed` 等)。**v3.0 收敛到 5 个核心白名单**,其他 op 改在 `videos[i].video_ops` 顶层整段生效(D1 + D7)。若需"段内降噪 / 段内 ASR"等场景,改在 `video_ops` 整段应用。

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

### 3.2 多 op 范式(同段多个独立 op,均在白名单内)

```json
{
  "time_segments": [
    {
      "id": "seg_1_2",
      "start_sec": 5.0,
      "end_sec": 20.0,
      "ops": {
        "speed-up": { "on": true, "factor": 1.5, "note": "段内整体加速" },
        "color-grade": { "on": true, "preset": "warm", "note": "段内暖色调" }
      }
    }
  ]
}
```

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

### 3.2 多 op 范式(同段多个独立 op,均在白名单内)

```json
{
  "time_segments": [
    {
      "id": "seg_1_2",
      "start_sec": 5.0,
      "end_sec": 20.0,
      "ops": {
        "speed-up": { "on": true, "factor": 1.5, "note": "段内整体加速" },
        "color-grade": { "on": true, "preset": "warm", "note": "段内暖色调" }
      }
    }
  ]
}
```

> **历史示例**(v1.x 写法,已不推荐):以下 op 不在 v3.0 段内白名单 → 改在 `video_ops` 整段生效
>
> ```jsonc
> // ❌ 不再允许(段内 asr-transcribe)
> "time_segments": [{
>   "ops": {
>     "asr-transcribe": { "on": true, "model": "medium" }  // v1 允许,v3.0 拒绝
>   }
> }]
>
> // ✅ 改法:整段生效
> "video_ops": {
>   "asr-transcribe": { "on": true, "model": "medium" }
> }
> ```

### 3.3 voice 模式(段级音频策略 · **D1 已迁移到 video_ops**)

> **2026-07-29 修订(D1)**:`voice.mode` 不再在 `time_segments[].ops` 下,改在 `videos[i].video_ops.voice.mode` 顶层生效。

```json
{
  "videos": [{
    "video_ops": {
      "voice": { "mode": "keep-with-filler-removed" },
      "voice_note": "整段保留对话但去水词"
    }
  }]
}
```

`voice.mode` 枚举(整段型):

| 值 | 含义 | 路由 |
|---|---|---|
| `keep` | 保留原声 | `audio_bgm.py` 默认 |
| `keep-with-filler-removed` | 保留 + 去水词 | `scripts/ai/fillers.py`(已实装) |
| `mute` | 静音 | `audio_bgm.py --video-volume 0` |
| `bgm-only` | 只留 BGM | `audio_bgm.py --mix bgm` |
| ~~`original-with-bgm`~~ | ~~原声 + BGM 混合~~ | v3.0 删除,如需用 `video_ops.add-bgm` 叠加 |

## 4. AI 路由表(段内 op 路由 · spec §7 白名单)

> AI 看到 `time_segments[j].ops.<op_name>` 时(白名单内 5 个),复用以下 CLI。
> 参数起始时间从 0 改为段内偏移(seg.start_sec)。

| `time_segments[j].ops.<op>` | atomic CLI | 段内偏移说明 |
|---|---|---|
| `speed-up` / `slow-down` | `video_speed.py` | 整段应用,无需偏移 |
| `reverse` | `video_reverse.py` | 整段 |
| `mute` | `audio_bgm.py --video-volume 0` | 整段 |
| `color-grade` | `video_color.py` | 整段应用(13 preset:warm/cool/cinematic/vintage/bw/high-contrast/noir/comic/sketch/faded/punchy/vhs/dream/sharpen) |

> **不再支持的段内 op**:v1.x 段内还允许 `fade-in` / `fade-out` / `asr-*` / `audio-*` / `voice-filler-removed` 等(v2 待实现说明)。
> v3.0 这些 op 全部从段内白名单移除 —— 改在 `video_ops` 整段生效(D1 + D7)。

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
