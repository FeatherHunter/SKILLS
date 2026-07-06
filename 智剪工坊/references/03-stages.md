# 03-stages - 阶段 1-4 详细编排（v1.3 AI 编排版）

> **何时加载**: AI 准备执行某个阶段时,加载对应的 §N 段
> **目的**: 详细说明每个阶段 AI 编排的具体步骤,避免"读 SKILL.md 看不完"的问题

---

## §阶段 1 — 读 intent.html / intent.json

**AI 必做**:
1. 读 `intent.json`（项目根目录）
2. **逐字段**查 `references/02-routing.md` 的字段枚举表
3. 非法值 / 模糊项 → 问用户（不要瞎猜）
4. 自由文本字段（`notes` / `overall_intent`）→ AI 文本解析 → 路由表匹配 → 用户确认

**加载 references**:
- `references/02-routing.md`（必读）

## §阶段 2 — 处理素材（按视频/图片分类）

**AI 必做**:
1. 遍历 `videos[]` 列表
2. 对每个 video 调 `process_video(video, workspace, output_path, ...)`
3. 如果有 `sequences[i].photos[]`,先转图片成视频（见下）

**加载 references**:
- `references/04-cut.md`（pin-range / cut-middle）
- `references/05-image.md`（image_to_video）
- `references/07-audio.md`（audio_bgm）
- `references/02-transitions.md`（视频内转场, 实际很少用,通常在阶段 3 序列内做）

### §阶段 2.1 — 处理视频

```python
from processing import process_video

for i, video in enumerate(intent['videos']):
    output_path = workspace / f"00_智剪/粗加工/视频_{i:02d}.mp4"
    out, profile, success = process_video(
        video, workspace, output_path,
        target_aspect=intent.get('output', {}).get('aspect_ratio', '16:9'),
        aspect_handling=intent.get('output', {}).get('aspect_handling', 'aspect-fit'),
    )
```

**自动 video_normalize**: `process_video` 末尾自动调 `video_normalize` 归一化到 30fps / yuv420p / aac 44100 stereo。

### §阶段 2.2 — 处理图片素材（v1.3 新增）

```python
from image_to_video import image_to_video

# 收集所有 sequences 的 photos
all_photos = []
for seq in intent.get('sequences', []):
    for photo in seq.get('photos', []):
        all_photos.append(photo)

# 转图成视频
for i, photo in enumerate(all_photos):
    output_path = workspace / f"00_智剪/粗加工/photo_{i:02d}.mp4"
    image_to_video(
        image=workspace / photo['file'],
        output=str(output_path),
        duration=photo.get('duration', 3.0),
        width=width, height=height,  # 按项目 aspect
        ken_burns_in=(photo.get('effect') == 'ken-burns-in'),
        ken_burns_out=(photo.get('effect') == 'ken-burns-out'),
    )
```

### §阶段 2.3 — 视频内音频处理

```python
from audio_bgm import add_bgm

# per-video audio（BGM 原声混音等）
for i, video in enumerate(intent['videos']):
    ops = video.get('ops', {})
    if 'audio' in ops and ops['audio'].get('on'):
        add_bgm(
            video=str(粗加工输出),
            bgm=ops['audio']['file'],
            output=str(最终输出),
            bgm_volume=ops['audio'].get('volume', 0.18),
            start=ops['audio'].get('start', 0),
            end=ops['audio'].get('end'),  # None = 视频结尾
            bgm_fade_in=ops['audio'].get('bgm_fade_in', 0),
            bgm_fade_out=ops['audio'].get('bgm_fade_out', 0),
            match_mode=ops['audio'].get('match_mode', 'loop'),
        )
```

**注意**: 阶段 2 调 audio 通常是 per-video 提前混合; 阶段 4 还有"全片 BGM 混合"（一次给整片加 BGM）。

## §阶段 3 — 序列拼接（AI 编排核心）

**AI 必做**:
1. 按 `sequences[i].videos[]` 顺序组织播放列表
2. 按 `sequences[i].transitions[]` 选择转场:
   - `none` / `cut` → 走 `concatenate_simple`（硬切）
   - 其他 8 种 → 走 `xfade_concat`
3. 序列间默认用 `concatenate_simple` 拼

**加载 references**:
- `references/02-transitions.md`（9 种转场）
- `references/05-image.md`（图片已转视频,这里按视频处理）

### §阶段 3.1 — 单序列拼接

```python
from processing import xfade_concat, concatenate_simple

videos = [workspace / v for v in intent['sequences'][0]['videos']]
transitions = intent['sequences'][0].get('transitions', [])

# 累积拼接
current = videos[0]
for i, next_v in enumerate(videos[1:], 1):
    # 找这段之后的转场
    t = next((t for t in transitions if t['after'] == i-1), None)
    if t and t.get('type') not in (None, 'none', 'cut'):
        # xfade 转场
        out = workspace / f"00_智剪/拼接/seq_seg_{i}.mp4"
        xfade_concat(str(current), str(next_v), t, str(out))
        current = out
    else:
        # 硬切
        out = workspace / f"00_智剪/拼接/seq_seg_{i}.mp4"
        concatenate_simple([str(current), str(next_v)], str(out))
        current = out
```

### §阶段 3.2 — 序列间拼接

```python
# 拼完所有 sequence 后,把所有 sequence 输出再用 concatenate_simple 拼
seq_outputs = [...]  # 各 sequence 拼完的 mp4
final = workspace / "00_智剪/拼接/vlog_no_bgm.mp4"
concatenate_simple([str(p) for p in seq_outputs], str(final))
```

## §阶段 4 — 拼成片

**AI 必做**:
1. 烧字幕（如果有文字稿）
2. BGM 混合（如果有 BGM）
3. 生成封面
4. 拼成片 + 命名

**加载 references**:
- `references/07-audio.md`（BGM 阶段 4 用法）
- `references/08-cover.md`（封面生成）
- `references/06-text.md`（字幕烧录）

### §阶段 4.1 — 烧字幕

```python
from video_subtitle import burn_subtitle
# 对每个 video 烧字幕
```

### §阶段 4.2 — BGM 混合（成片级）

```python
from audio_bgm import add_bgm

add_bgm(
    video=成片路径,
    bgm=intent['output']['bgm'],
    output=成片_with_bgm,
    bgm_volume=0.18,
    match_mode=intent.get('output', {}).get('bgm_match_mode', 'loop'),
)
```

**AI 必读规则**:
- BGM 混合前 AI 必须问用户"加什么 BGM / 音量多少"（操作清单 D 象限已确认则直接用）
- **BGM 时长不匹配处理（v1.3 新增）**: AI 必须先看 BGM 和视频时长差, 按 `output.bgm_match_mode` 调用

### §阶段 4.3 — 封面生成

按 `intent.cover.prompt` 调 `ai_cover.py`（推荐）或 `cover_text.py`（纯文字）。

### §阶段 4.4 — 拼成片 + 命名

**文件名（v1.3 新增）**:
- 优先用 `project.title`（用户填的成片标题）
- fallback 用 `project.name`（项目名）
- 都没有 → fallback 到 `vlog_final.mp4`（向后兼容）

```python
from lib.filename import get_output_path

output_path = get_output_path(
    workspace=workspace,
    project_title=intent.get('project', {}).get('title'),
    project_name=intent.get('project', {}).get('name'),
    suffix='',  # 可选: '_draft' / '_v2' 等
)
```

## §完整流程总览

```
阶段 1 读 intent.json / 路由表匹配 / 问用户
  ↓
阶段 2 处理素材
  ├── 2.1 处理视频 (process_video, 自动 video_normalize)
  ├── 2.2 处理图片 (image_to_video, 阶段 2 转换)
  └── 2.3 per-video 音频 (audio_bgm)
  ↓
阶段 3 序列拼接
  ├── 3.1 单序列拼接 (xfade_concat / concatenate_simple)
  └── 3.2 序列间拼接 (concatenate_simple)
  ↓
阶段 4 拼成片
  ├── 4.1 烧字幕
  ├── 4.2 成片 BGM 混合
  ├── 4.3 封面生成
  └── 4.4 拼成片 + 命名
  ↓
输出成片
```

## 相关参考

- **SKILL.md §主体流程**: 一句话目标 + 工具端 + 工作区
- **SKILL.md §AI 协作协议**: AI 必读规则
- **references/02-routing.md**: 字段枚举 + 路由表
