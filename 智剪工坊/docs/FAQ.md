# 智剪工坊 · 常见问题(FAQ)

## 基础问题

### Q1: ffmpeg 在哪?

A: 默认配的本机路径:
```
D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe
```

如果不存在,装一个放 PATH,或修改 `lib/common.py` 的 `DEFAULT_FFMPEG`。

### Q2: 如何查看 ffmpeg 版本?

```bash
ffmpeg -version
```

### Q3: 如何看视频的 fps、分辨率、时长?

```bash
ffmpeg -i video.mp4 2>&1 | findstr "Duration|Stream"
```

## 运行问题

### Q4: 报错 "ffmpeg 失败"?

A: 看 stderr 末尾 500 字符,常见原因:
- 输入文件不存在 → 检查路径
- 输出目录无权限 → 改路径
- 编码参数不兼容 → 改用 libx264

### Q5: 报错 "Access Violation 0xC0000005"?

A: NVENC 崩溃,改用 libx264(已是默认值)。如果是用户手动加的,去掉 `-c:v h264_nvenc`。

### Q6: 视频时长变成 8 小时?

A: 帧率不一致 bug!不同原始视频 fps 不同(60 vs 23.976)会导致拼接异常。

**修复:** 剪切时强制 `fps=30`:
```bash
-vf "...,fps=30"
```

`scripts/cut.py` 默认已加。

### Q7: 字幕显示为方框/乱码?

A: 字体问题。Windows 确认 `C:\Windows\Fonts\msyh.ttc` 存在。

如果用其他字体,改 `lib/common.py` 的 `DEFAULT_FONT`。

### Q8: AI 生图中文显示奇怪?

A: AI 生图对中文支持差(从第一性原理:训练数据里中文/数字比例低)。

**修复:** 改用 "先生成视觉 + 后叠中文"两步法,见 `scripts/cover_ai.py`。

## 输出问题

### Q9: 输出视频比预期大?

A: 默认 crf=20(质量较高)。改 crf=23 文件小 30%。

```bash
python scripts/cut.py trim --input in.mp4 --t 30 --out out.mp4 \
  --crf 23  # (如果加了 --crf 参数)
```

### Q10: 音频和视频不同步?

A: 可能是变速后音频未处理。setpts 改了视频时长,音频需要 atempo。

```bash
-vf "setpts=0.5*PTS" -af "atempo=2.0"
```

### Q11: 输出视频没有声音?

A: 编码参数 `-c:a aac` 没传,或音频流不存在。检查源视频:
```bash
ffprobe -i video.mp4
```

## 性能问题

### Q12: 处理太慢?

A: 几个加速技巧:
- 用 `libx264 -preset ultrafast`(快 5 倍,质量略降)
- 用 `libx264 -crf 23`(质量略低,文件更小,编码更快)
- 减少视频尺寸(从 1080p 降到 720p)
- 避免 `minterpolate`(插帧很慢)

### Q13: GPU 没用上?

A: ffmpeg 默认 CPU(libx264)。要用 GPU:
```bash
-c:v h264_nvenc
```
但 NVENC 不稳定,谨慎用。

## 进阶问题

### Q14: 怎么把多个转场串起来?

A: 3+ 段需要逐个 xfade 拼接。写 Python 脚本:
```python
result = clip1
for c in clips[1:]:
    result = xfade(result, c, "fade", 1)
```

### Q15: 怎么跑 GPU Whisper?

A: 装 faster-whisper(已在 requirements.txt),自动用 GPU:
```python
model = WhisperModel("medium", device="cuda")
```

### Q16: 怎么把多个 skill 组合成"工厂"?

A: 用 `pipeline_vlog.py run`,把多步串起来。或写自己的 Python 脚本调用各子技能。

## 设计决策

### Q17: 为什么不直接调 ffmpeg,要做这个 skill?

A: 三个理由:
1. **统一接口** —— 各子技能统一参数和错误处理
2. **复用代码** —— 公共库避免每个脚本写一遍
3. **AI 友好** —— 自然语言触发,Mavis 路由

### Q18: 能不能加 XXX 功能?

A: 提需求,根据通用性决定是否加。子技能粒度:每个原子能力 = 一个脚本。

### Q19: 性能瓶颈在哪?

A: 主要是 ffmpeg。瓶颈顺序:
1. 视频编码(crf 越低越慢)
2. 滤镜(zoompan / minterpolate)
3. AI(rembg / Whisper)

## 已知 bug(持续更新)

| Bug | 描述 | 状态 |
|---|---|---|
| NVENC 崩溃 | Access Violation 0xC0000005 | 已用 libx264 规避 |
| 8 小时视频 | fps 不一致导致 | 已强制 fps=30 |
| AI 中文乱码 | 生图对中文支持差 | 已用后叠中文 |
| 大文件处理慢 | 4K 视频处理慢 | 待优化(分块处理) |
| 移动端兼容性 | 某些 codec 移动端不播 | 待测试 |
