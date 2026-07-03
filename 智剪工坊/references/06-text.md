# 06 - text (文字动画 + 烧字幕)

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