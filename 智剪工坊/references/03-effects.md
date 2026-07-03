# 03 - effects (视觉特效 / 慢动作 + 推镜头)

## 触发词

"慢动作"、"慢放"、"0.5 倍速"、"插帧"、"推镜头"、"zoom in"、"推到脸"、"放大"、"缩小"、"模糊"、"抖动"、"镜像"

## 输入 / 输出

- **输入**: 单个视频
- **输出**: 加特效后的视频

## A. 慢动作(slowmo)

### 普通慢动作

```bash
# 2 倍慢(setpts 改变时间戳)
ffmpeg -i in.mp4 -vf "setpts=2*PTS" -an out.mp4
```

### 丝滑慢动作(插帧)

```bash
# 2 倍慢 + minterpolate 插帧(更丝滑)
ffmpeg -i in.mp4 -vf "setpts=2*PTS,minterpolate=fps=60:mi_mode=mci" out.mp4
```

**mi_mode 选项:**
- `dup`: 重复帧(最快,质量差)
- `blend`: 帧混合(中等质量)
- `mci`: 运动补偿插帧(最丝滑,慢)

### 快动作

```bash
# 2 倍快
ffmpeg -i in.mp4 -vf "setpts=0.5*PTS" -an out.mp4
```

## B. 推镜头(zoompan)

### 基础 zoom-in

```bash
# 从中心放大到 1.5 倍
ffmpeg -i in.mp4 -vf "zoompan=z='min(zoom+0.0015,1.5)':d=125:s=1080x1920" out.mp4
```

参数:
- `z`: 缩放表达式(随时间变化)
- `d`: 帧数(zoom 时长)
- `s`: 输出尺寸

### Zoom-out(拉远)

```bash
ffmpeg -i in.mp4 -vf "zoompan=z='if(eq(on,0),1.5,max(1.0010,zoom-0.0015))':d=125:s=1080x1920" out.mp4
```

### 推到指定坐标

```bash
# 推到画面右下角
ffmpeg -i in.mp4 -vf "zoompan=z='1.5':x='iw/2':y='ih/2':d=125:s=1080x1920" out.mp4
```

## C. 模糊 / 锐化

```bash
# 高斯模糊
ffmpeg -i in.mp4 -vf "gblur=sigma=10" out.mp4

# 锐化
ffmpeg -i in.mp4 -vf "unsharp=5:5:1.0:5:5:0.0" out.mp4
```

## D. 抖动 / 震动

```bash
# 画面震动(地震感)
ffmpeg -i in.mp4 -vf "crop=in_w-20:in_h-20:10+random(0)*20:10+random(0)*20" out.mp4
```

## E. 镜像翻转

```bash
# 水平翻转
ffmpeg -i in.mp4 -vf "hflip" out.mp4

# 垂直翻转
ffmpeg -i in.mp4 -vf "vflip" out.mp4
```

## F. 旋转

```bash
# 旋转 90 度
ffmpeg -i in.mp4 -vf "transpose=1" out.mp4
# transpose=1: 90° 顺时针
# transpose=2: 90° 逆时针
# transpose=3: 90° 顺时针 + 垂直翻转
```

## 调用示例

```
用户: "把这段视频做 0.5 倍慢动作"
→ slowmo --input in.mp4 --speed 0.5 --interpolate mci
```

```
用户: "做推镜头效果,推到中段"
→ zoompan --input in.mp4 --from 1.0 --to 1.5 --start 0 --duration 5
```

## 限制 / 注意

1. **minterpolate 慢**:插帧慢动作比普通慢动作慢 5-10 倍,慎用
2. **zoompan + 字幕**:烧字幕要在 zoompan 之后(`-vf "zoompan=...,subtitles=..."`)
3. **filter chain 顺序**:多个特效叠加注意 filter chain 顺序会影响效果

## 进阶:OpenCV 视觉特效

剪映做不到的:
- 自动人脸追踪 + 加贴纸
- 智能抠图(rembg) + 换背景
- 物体识别 + 自动跟踪放大

参考 [09-ai-features.md](09-ai-features.md)。