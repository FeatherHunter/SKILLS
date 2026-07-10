# 字幕文字 - Whisper烧字幕片头变声

> **对应脚本**: `scripts/video/subtitle.py` + `scripts/video/opening.py` + `scripts/audio/voice.py` + `scripts/ai/translate.py`
> **触发词**: "字幕"、"烧字幕"、"字幕动效"、"打字机"、"打字效果"、"淡入"、"弹跳"、"跑马灯"、"标题"、"文字"
> **实测状态**: ✅ 验证通过

---

## 1. 调用范式

### 场景 1

```bash
# 自动字幕(Whisper 转录 + 烧录)
python scripts/video/subtitle.py --input v.mp4 --srt v.srt --burn --output v_subtitled.mp4

# 片头说明文字（v1.0 新增, 9 宫格简写 + 淡入淡出 + 自动中文字体）
python scripts/video/opening.py add --input v.mp4 --output v_with_text.mp4 \
    --text "晨间体重 新的一天" --region bottom-left --duration 2

# 变声 12 种
python scripts/audio/voice.py --input v.mp4 --pitch +2 --output v_chipmunk.mp4

# 翻译(占位,完整版用 rewrite_audio)
python scripts/ai/translate.py --input v.srt --target en --output v_en.srt
```

### 场景 2

```bash
ffmpeg -i in.mp4 \
  -vf "subtitles=sub.srt:\
force_style='FontName=Microsoft YaHei,\
FontSize=22,\
PrimaryColour=&H00FFFFFF,\
OutlineColour=&H00000000,\
Outline=2,\
Shadow=1,\
MarginV=30,\
Alignment=2'" \
  -c:v libx264 -preset medium -crf 20 \
  -c:a copy \
  out.mp4
```

### 场景 3

```bash
# 文字"Hello"在 1-3 秒逐字显示
ffmpeg -i in.mp4 \
  -vf "drawtext=text='Hello':fontfile=/path/font.ttf:\
fontsize=60:fontcolor=white:\
x=(w-text_w)/2:y=(h-text_h)/2:\
enable='gte(t,1)':\
alpha='if(lt(t,3),(t-1)/2,1)'" \
  out.mp4
```

## 2. 参数

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--input` | `-i` | (必填) | 输入视频/音频/图片 |
| `--output` | `-o` | (必填) | 输出路径 |

## 3. 常见错误 / 限制

1. **drawtext 性能**:复杂 drawtext 会显著降低 ffmpeg 速度
2. **中文字体**:Windows 自带 `C:\Windows\Fonts\msyh.ttc` / `msyhbd.ttc`
3. **转义**:PowerShell 调用注意 `$` 转义,单引号包含参数

## 4. 相关参考

- **SKILL.md §14 子技能索引**：本子技能的路由表
- **scripts/README.md**：scripts/ 目录命名规范（`<维度>_<动作>.py`）
- `.archive/CHANGELOG.md`：本子技能历史变更

---

<details>
<summary>📋 原文存档（v0.5 旧版，仅供 git history 追溯）</summary>

# 06 - text (文字动画 + 烧字幕 + 片头文字) — v1.0 已实现

> **对应脚本:** `scripts/video_subtitle.py` + `scripts/video_opening.py` + `scripts/audio_voice.py` + `scripts/ai_translate.py`(4 个)
> **实测状态:** ✅ 验证通过

```bash
# 自动字幕(Whisper 转录 + 烧录)
python scripts/video_subtitle.py --input v.mp4 --srt v.srt --burn --output v_subtitled.mp4

# 片头说明文字（v1.0 新增, 9 宫格简写 + 淡入淡出 + 自动中文字体）
python scripts/video_opening.py add --input v.mp4 --output v_with_text.mp4 \
    --text "晨间体重 新的一天" --region bottom-left --duration 2

# 变声 12 种
python scripts/audio_voice.py --input v.mp4 --pitch +2 --output v_chipmunk.mp4

# 翻译(占位,完整版用 rewrite_audio)
python scripts/ai_translate.py --input v.srt --target en --output v_en.srt
```

---

## 触发词

"字幕"、"烧字幕"、"文字"、"打字机"、"打字效果"、"淡入"、"弹跳"、"跑马灯"、"标题"、"字幕动效"

## 输入 / 输出

- **输入**: 视频 + SRT 字幕文件 / 文字内容
- **输出**: 烧录或叠加文字后的视频

## A. 烧字幕(force_style)

```bash
ffmpeg -i in.mp4 \
  -vf "subtitles=sub.srt:\
force_style='FontName=Microsoft YaHei,\
FontSize=22,\
PrimaryColour=&H00FFFFFF,\
OutlineColour=&H00000000,\
Outline=2,\
Shadow=1,\
MarginV=30,\
Alignment=2'" \
  -c:v libx264 -preset medium -crf 20 \
  -c:a copy \
  out.mp4
```

### 常用 style 参数

| 参数 | 说明 | 示例 |
|---|---|---|
| FontName | 字体 | Microsoft YaHei, SimHei |
| FontSize | 字号 | 22 |
| PrimaryColour | 字体颜色 | &H00FFFFFF(白) / &H0000FF(红) |
| OutlineColour | 描边颜色 | &H00000000(黑) |
| Outline | 描边宽度 | 2 |
| Shadow | 阴影 | 1 |
| MarginV | 垂直边距 | 30(底部) |
| Alignment | 对齐方式 | 2(底部居中) / 5(顶部居中) |
| Bold | 加粗 | -1 |

颜色格式: `&H00BBGGRR`(BGR 顺序,不是 RGB)

## B. 打字机效果

```bash
# 文字"Hello"在 1-3 秒逐字显示
ffmpeg -i in.mp4 \
  -vf "drawtext=text='Hello':fontfile=/path/font.ttf:\
fontsize=60:fontcolor=white:\
x=(w-text_w)/2:y=(h-text_h)/2:\
enable='gte(t,1)':\
alpha='if(lt(t,3),(t-1)/2,1)'" \
  out.mp4
```

`alpha` 表达式控制透明度,实现"淡入"或"逐字"效果。

## C. 淡入淡出文字

```bash
# 文字在 1-3 秒淡入,5-7 秒淡出
ffmpeg -i in.mp4 \
  -vf "drawtext=text='重要提示':fontfile=font.ttf:fontsize=50:fontcolor=yellow:\
x=(w-text_w)/2:y=100:\
alpha='if(lt(t,1),t,if(lt(t,5),1,if(lt(t,7),(7-t)/2,0)))'" \
  out.mp4
```

## D. 跑马灯(滚动文字)

```bash
# 文字从右向左滚动
ffmpeg -i in.mp4 \
  -vf "drawtext=text='滚动字幕':fontfile=font.ttf:fontsize=40:fontcolor=white:\
x='w-mod(t*100,w+text_w)':y=h-50" \
  out.mp4
```

## E. 弹跳 / 缩放文字

```bash
# 文字缩放进入
ffmpeg -i in.mp4 \
  -vf "drawtext=text='弹跳':fontfile=font.ttf:fontsize=80:fontcolor=white:\
x=(w-text_w)/2:y=(h-text_h)/2:\
fontsize='if(lt(t,1),80*sin(t*PI/2),80)'" \
  out.mp4
```

## F. 多行文字

```bash
# 多行文字(用 \n 换行)
ffmpeg -i in.mp4 \
  -vf "drawtext=text='第一行\n第二行\n第三行':\
fontfile=font.ttf:fontsize=40:fontcolor=white:\
x=(w-text_w)/2:y=(h-text_h)/2:\
line_spacing=20" \
  out.mp4
```

## G. 时间码 / 时间戳叠加

```bash
# 显示当前时间码
ffmpeg -i in.mp4 \
  -vf "drawtext=text='%{pts\\:hms}':fontfile=font.ttf:fontsize=30:fontcolor=white:\
x=20:y=20" \
  out.mp4
```

## 调用示例

```
用户: "给视频加字幕"
→ text --input in.mp4 --subtitle sub.srt --burn
```

```
用户: "做个打字机效果,显示'开始'"
→ text --type typewriter --content "开始" --duration 2
```

## 限制 / 注意

1. **drawtext 性能**:复杂 drawtext 会显著降低 ffmpeg 速度
2. **中文字体**:Windows 自带 `C:\Windows\Fonts\msyh.ttc` / `msyhbd.ttc`
3. **转义**:PowerShell 调用注意 `$` 转义,单引号包含参数

## 字体路径参考

```python
# Windows 系统字体
"C:\Windows\Fonts\msyh.ttc"        # 微软雅黑
"C:\Windows\Fonts\msyhbd.ttc"      # 微软雅黑 Bold
"C:\Windows\Fonts\simhei.ttf"      # 黑体
"C:\Windows\Fonts\simsun.ttc"      # 宋体
"C:\Windows\Fonts\arial.ttf"       # Arial
```

</details>
