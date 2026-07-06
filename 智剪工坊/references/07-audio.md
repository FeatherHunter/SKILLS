# 07-audio - 音频 — v1.2 已实现

> **对应脚本**: `scripts/audio_bgm.py` + `scripts/audio_beat.py`
> **触发词**: "BGM"、"加音乐"、"配乐"、"背景音乐"、"循环"、"淡入"、"淡出"、"混音"、"音量"、"音频降噪"
> **实测状态**: ✅ 验证通过

---

## 1. 调用范式

### 场景 1

```bash
# BGM 循环混音
python scripts/audio_bgm.py --video v.mp4 --bgm bgm.mp3 --volume 0.18 --output out.mp4

# 节拍卡点
python scripts/audio_beat.py --video v.mp4 --bgm bgm.mp3 --output out.mp4
```

### 场景 2

```bash
ffmpeg -i video.mp4 -i bgm.mp3 \
  -filter_complex "[1:a]volume=0.5[bgm];\
                   [0:a][bgm]amix=inputs=2:duration=first[a]" \
  -map 0:v -map [a] \
  -c:v copy -c:a aac -b:a 128k \
  out.mp4
```

### 场景 3

```bash
ffmpeg -i video.mp4 -stream_loop -1 -i bgm.mp3 \
  -filter_complex "[0:a]volume=1.0[a0];\
                   [1:a]volume=0.18,aloop=loop=-1:size=2e9[a1];\
                   [a0][a1]amix=inputs=2:duration=first:dropout_transition=0[a]" \
  -map 0:v -map [a] \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 128k \
  out.mp4
```

## 2. 参数

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--input` | `-i` | (必填) | 输入视频/音频/图片 |
| `--output` | `-o` | (必填) | 输出路径 |

## 3. 常见错误 / 限制

1. **音量平衡**:BGM 音量 < 0.3,确保不盖过原始人声
2. **dropout_transition=0**:避免 amix 在 BGM 结束时产生噪声
3. **stream_loop 在 filter 链外**:ffmpeg 命令行参数 -stream_loop 和 filter 内 aloop 都要加

## 4. 相关参考

- **SKILL.md §14 子技能索引**：本子技能的路由表
- **scripts/README.md**：scripts/ 目录命名规范（`<维度>_<动作>.py`）
- `.archive/CHANGELOG.md`：本子技能历史变更

---

<details>
<summary>📋 原文存档（v0.5 旧版，仅供 git history 追溯）</summary>

# 07 - audio (音频处理 / BGM / 混音) — v0.5 已实现

> **对应脚本:** `scripts/audio_bgm.py` + `scripts/audio_beat.py`(2 个)
> **实测状态:** ✅ 验证通过

```bash
# BGM 循环混音
python scripts/audio_bgm.py --video v.mp4 --bgm bgm.mp3 --volume 0.18 --output out.mp4

# 节拍卡点
python scripts/audio_beat.py --video v.mp4 --bgm bgm.mp3 --output out.mp4
```

---

## 触发词

"BGM"、"配乐"、"背景音乐"、"加音乐"、"混音"、"音量"、"淡入"、"淡出"、"循环"、"音频降噪"、"节拍"

## 输入 / 输出

- **输入**: 视频文件 + 音频文件(BGM)
- **输出**: 混音后的视频

## A. 加 BGM(基础)

```bash
ffmpeg -i video.mp4 -i bgm.mp3 \
  -filter_complex "[1:a]volume=0.5[bgm];\
                   [0:a][bgm]amix=inputs=2:duration=first[a]" \
  -map 0:v -map [a] \
  -c:v copy -c:a aac -b:a 128k \
  out.mp4
```

参数:
- `volume=0.5`:BGM 音量(0.5 = 原始音量的 50%)
- `duration=first`:混音时长跟随第一个输入(视频)
- `inputs=2`:两个输入

## B. BGM 循环(关键!)

**问题:** 生成的 BGM 通常只有 30-60 秒,但视频可能 3-5 分钟,需要循环。

```bash
ffmpeg -i video.mp4 -stream_loop -1 -i bgm.mp3 \
  -filter_complex "[0:a]volume=1.0[a0];\
                   [1:a]volume=0.18,aloop=loop=-1:size=2e9[a1];\
                   [a0][a1]amix=inputs=2:duration=first:dropout_transition=0[a]" \
  -map 0:v -map [a] \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 128k \
  out.mp4
```

**关键参数:**
- `-stream_loop -1`:无限循环 BGM 输入
- `aloop=loop=-1`:filter 内也无限循环
- `volume=0.18`:BGM 音量调低(避免盖过人声)
- `dropout_transition=0`:避免 BGM 结束时突变

## C. BGM 淡入淡出

```bash
# BGM 在视频开头 3 秒淡入
ffmpeg -i video.mp4 -i bgm.mp3 \
  -filter_complex "[1:a]volume=0.5,afade=t=in:st=0:d=3[bgm];\
                   [0:a][bgm]amix=inputs=2:duration=first[a]" \
  -map 0:v -map [a] \
  out.mp4
```

```bash
# BGM 在视频结尾 3 秒淡出
ffmpeg -i video.mp4 -i bgm.mp3 \
  -filter_complex "[1:a]volume=0.5,afade=t=out:st=END-3:d=3[bgm];\
                   [0:a][bgm]amix=inputs=2:duration=first[a]" \
  -map 0:v -map [a] \
  out.mp4
```

## D. 音频降噪

```bash
# 基础降噪(去除背景噪音)
ffmpeg -i noisy.mp3 -af "highpass=f=200,lowpass=f=3000" out.mp3

# 高级降噪(用 afftdn)
ffmpeg -i noisy.mp3 -af "afftdn=nf=-25" out.mp3
```

## E. 音量标准化

```bash
# 响度标准化(-16 LUFS,B 站 / 抖音标准)
ffmpeg -i in.mp4 -af "loudnorm=I=-16:TP=-1.5:LRA=11" out.mp4

# 仅音频
ffmpeg -i in.mp3 -af "loudnorm=I=-16:TP=-1.5:LRA=11" out.mp3
```

## F. 提取 / 替换音频

```bash
# 提取音频
ffmpeg -i video.mp4 -vn -c:a copy audio.aac

# 替换音频
ffmpeg -i video.mp4 -i new_audio.mp3 \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac \
  out.mp4
```

## G. AI 生成 BGM(矩阵工具)

使用 matrix MCP 生成专属 BGM:

```bash
# 通过 matrix 生成音乐(英文 prompt 效果更好)
mavis mcp call matrix matrix_batch_text_to_music '{
  "requests": [{
    "prompt": "Cinematic motivational instrumental BGM, 3 minutes 30 seconds, 120 BPM. Piano lead with soft strings and light percussion. Calm intro, energetic middle, warm hopeful ending.",
    "format": "mp3"
  }]
}'
```

生成的 BGM 在:
- `C:\Users\辰辰洋洋\.mavis\agents\mavis\workspace\matrix-media-*.mp3`

## 调用示例

```
用户: "给视频配一段 BGM,循环到结尾"
→ audio --bgm bgm.mp3 --volume 0.18 --loop
```

```
用户: "让 BGM 在结尾淡出"
→ audio --bgm bgm.mp3 --fade-out 3
```

## 限制 / 注意

1. **音量平衡**:BGM 音量 < 0.3,确保不盖过原始人声
2. **dropout_transition=0**:避免 amix 在 BGM 结束时产生噪声
3. **stream_loop 在 filter 链外**:ffmpeg 命令行参数 -stream_loop 和 filter 内 aloop 都要加

</details>
