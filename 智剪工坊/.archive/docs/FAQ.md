# 智剪工坊 · 常见问题(FAQ)

> v0.5 更新(2026-07-03)— 含 5 个 AI 增强功能(美颜/去水词/改词/文字成片/数字人)

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

## 安装与验证

### Q4: setup.bat 跑完有哪些产物?

- 安装 9 个实依赖(Pillow, faster-whisper, opencv-python, mediapipe, librosa, numpy, openai-whisper, requests, mavis)
- 生成 `assets/config.json`(含 ffmpeg 路径)
- 下载 mediapipe face_landmarker.task 模型(若缺失,fallback `C:\zhijian_models\`)
- 跑 `verify.py --fast` 确认 29/29 脚本可导入

### Q5: verify.py 报 "脚本导入失败" 怎么办?

```bash
python verify.py --fast --verbose
```

常见原因:
- mediapipe 没装 → `pip install mediapipe==0.10.35`
- faster-whisper 没装 → `pip install faster-whisper`
- 路径含中文(本项目无此问题,脚本有 fallback)

### Q6: mavis MCP 用不了(配额用完)?

- mmx 视频生成:每天 ~3 次
- mmx TTS / 数字人:配额独立
- 查剩余配额:`mavis mcp call matrix matrix_get_voice_list '{}'`

## 运行问题

### Q7: 报错 "ffmpeg 失败"?

A: 看 stderr 末尾 500 字符,常见原因:
- 输入文件不存在 → 检查路径
- 输出目录无权限 → 改路径
- 编码参数不兼容 → 改用 libx264(已默认)

### Q8: 报错 "Access Violation 0xC0000005"?

A: NVENC 崩溃,改用 libx264(已是默认值)。如果是用户手动加的,去掉 `-c:v h264_nvenc`。

### Q9: 视频时长变成 8 小时?

A: 帧率不一致 bug!不同原始视频 fps 不同(60 vs 23.976)会导致拼接异常。

**修复:** 剪切时强制 `fps=30`:
```bash
-vf "...,fps=30"
```

`scripts/cut.py` 默认已加。

### Q10: 字幕显示为方框/乱码?

A: 字体问题。Windows 确认 `C:\Windows\Fonts\msyh.ttc` 存在。

如果用其他字体,改 `lib/common.py` 的 `DEFAULT_FONT`。

### Q11: AI 生图中文显示奇怪?

A: AI 生图对中文支持差(从第一性原理:训练数据里中文/数字比例低)。

**修复:** 改用 "先生成视觉 + 后叠中文"两步法,见 `scripts/cover_ai.py`。

### Q12: beauty.py 报 "FileNotFoundError: face_landmarker.task"?

A: mediapipe 0.10.35 模型(~3.7MB)缺失,自动从 Google 下载。失败时手动:
1. 下载 https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
2. 放到 `C:\zhijian_models\face_landmarker.task`

### Q13: remove_fillers.py 报 "未检测到水词"?

A: 这是**正常**的!说明这段视频的说话人本来就没有"嗯啊那个"。不是错误。

如果实际有很多水词,可能是:
- Whisper 模型太小(small),换 medium
- word_timestamps 没开(脚本已默认 True)

### Q14: text_to_video.py 一直转圈?

A: mmx 视频生成一般 1-3 分钟(10s 视频最长),不要以为卡死。

看进度:`mavis mcp call matrix matrix_get_task_status '{"task_id": "..."}'`

## 输出问题

### Q15: 输出视频比预期大?

A: 默认 crf=20(质量较高)。改 crf=23 文件小 30%。

beauty / xfade / cut 脚本暂未直接暴露 `--crf` 参数。
可手动后处理:
```bash
ffmpeg -i in.mp4 -c:v libx264 -crf 23 -c:a copy out.mp4
```

### Q16: 音频和视频不同步?

A: 可能是变速后音频未处理。setpts 改了视频时长,音频需要 atempo。

```bash
-vf "setpts=0.5*PTS" -af "atempo=2.0"
```

### Q17: 输出视频没有声音?

A: 编码参数 `-c:a aac` 没传,或音频流不存在。检查源视频:
```bash
ffprobe -i video.mp4
```

## 性能问题

### Q18: 处理太慢?

A: 几个加速技巧:
- 用 `libx264 -preset ultrafast`(快 5 倍,质量略降)
- 用 `libx264 -crf 23`(质量略低,文件更小,编码更快)
- 减少视频尺寸(从 1080p 降到 720p)
- 避免 `minterpolate`(插帧很慢)
- 美颜慢(逐帧 mediapipe),小批量优先

### Q19: GPU 没用上?

A: ffmpeg 默认 CPU(libx264)。要用 GPU:
```bash
-c:v h264_nvenc
```
但 NVENC 不稳定,谨慎用。

## AI 功能专属问题

### Q20: 美颜效果不自然?

A: 调小强度:
```bash
python scripts/beauty.py --input v.mp4 --output v.mp4 --preset slight
# 或
python scripts/beauty.py --input v.mp4 --output v.mp4 \
  --smooth 0.3 --whiten 0.15 --slim 0.2 --enlarge 0.2
```

预设参考:
- `slight` (轻微) - 几乎看不出,稳妥
- **`natural` (默认)** - 推荐
- `strong` - 明显美颜
- `max` - 极限,可能失真

### Q21: 去水词后画面跳?

A: 正常现象(切掉了帧)。两个方法缓解:
- 选水词时,留 ±50ms 缓冲(脚本默认)
- 用 cut 而不是 trim(脚本用的是 cut,无缓冲跳)

### Q22: 改词翻唱后音画不同步?

A: 检查合成 TTS 时长 vs 原视频时长。
- 改写后文案 < 原文案 → 视频尾段静音
- 改写后文案 > 原文案 → 末尾超长

**建议:** 改写后用 ffmpeg 修剪到匹配时长,或重新生成 BGM 铺底。

### Q23: 数字人嘴型不准?

A: 已知限制。mmx subject 模式只能"保持人脸动",不保证嘴型精准对齐。

要精准嘴型用 L3 方案(待补):
- SadTalkers(本地开源)
- Wav2Lip(开源)

### Q24: 文字成片 6s 太短?

A: 多次生成后拼接(脚本待加 batch 版),或:
```bash
# 先生成多段
for i in {1..3}; do
  python scripts/text_to_video.py --prompt "..." --out "part_$i.mp4"
done
# ffmpeg 拼接
echo "file 'part_1.mp4'" > list.txt
echo "file 'part_2.mp4'" >> list.txt
echo "file 'part_3.mp4'" >> list.txt
ffmpeg -f concat -i list.txt -c copy out.mp4
```

## 进阶问题

### Q25: 怎么把多个转场串起来?

A: 3+ 段需要逐个 xfade 拼接。写 Python 脚本:
```python
import subprocess
clips = ["c1.mp4", "c2.mp4", "c3.mp4"]
result = clips[0]
for c in clips[1:]:
    out = "tmp.mp4"
    subprocess.run([
        "python", "scripts/xfade.py",
        "--a", result, "--b", c,
        "--type", "fade", "--duration", "1",
        "--out", out
    ])
    result = out
```

### Q26: 怎么跑 GPU Whisper?

A: 装 faster-whisper(已在 requirements.txt),自动用 GPU:
```python
model = WhisperModel("medium", device="cuda")
```

### Q27: 怎么把多个 skill 组合成"工厂"?

A: 用 `pipeline_vlog.py run`,把多步串起来。或写自己的 Python 脚本调用各子技能。

## 设计决策

### Q28: 为什么不直接调 ffmpeg,要做这个 skill?

A: 三个理由:
1. **统一接口** — 各子技能统一参数和错误处理
2. **复用代码** — 公共库避免每个脚本写一遍
3. **AI 友好** — 自然语言触发,Mavis 路由

### Q29: 能不能加 XXX 功能?

A: 提需求,根据通用性决定是否加。子技能粒度:每个原子能力 = 一个脚本。

### Q30: 性能瓶颈在哪?

A: 主要是 ffmpeg。瓶颈顺序:
1. 视频编码(crf 越低越慢)
2. 滤镜(zoompan / minterpolate)
3. AI(rembg / Whisper / mediapipe 美颜)

## 高频 bug(用户会问,Q&A 形式)

### Q31: 视频处理后变 8 小时 / 时长错乱?

A: 帧率不一致 bug!不同原始视频 fps 不同(60 vs 23.976)会导致拼接/剪切异常。

**修复:** 剪切时强制 `fps=30`,所有片段统一。`scripts/cut.py` 默认已加。

如果还遇到:看 [HANDOFF.md §Bug 2](../HANDOFF.md) 完整分析。

### Q32: 封面 / AI 生图中文显示奇怪 / 乱码?

A: AI 生图对中文/数字支持差(从第一性原理:训练数据里中文/数字比例低)。

**修复:** 改用"先生成视觉(无文字)+ 后叠中文(PIL)"两步法,见 `scripts/cover_ai.py`。

### Q33: 报 "Access Violation 0xC0000005" 崩溃?

A: NVENC 硬件编码随机崩溃。**解法:** 用 `libx264`(CPU 编码,稳)。本工具默认就是 libx264。

如果是你手动加的 `-c:v h264_nvenc`,去掉即可。

## 已知限制(短期内不修)

| 限制 | 描述 | 影响 |
|---|---|---|
| 数字人嘴型不准 | mmx subject 模式只"保持人脸动",不保证嘴型精准对齐 | 数字人演示能用,生产级不行。L3 待补 SadTalkers/Wav2Lip |
| 4K 大文件处理慢 | 逐帧 mediapipe + ffmpeg 编码 | 建议先降分辨率到 1080p |
| 移动端兼容性 | 某些 codec 移动端不播 | 待测试(可先压成 H.264 baseline) |
| 跨平台 | setup.sh 写好但只测 Windows | Mac/Linux 需自行验证 |
| 声音克隆 | matrix MCP 不支持自训 | 需自训模型,投入大,不补 |

**其他已修 bug**(开发内部,无需用户关心):见 [HANDOFF.md §1.3](../HANDOFF.md) v0.3 → v0.6 修复记录。

## edit.py 14 个原子操作(2026-07-03 v0.6 新增)

### Q34: 怎么去头/去尾/去中间?

A: 用 `edit.py remove`,三种 mode:

```bash
# 去头 3 秒
python scripts/edit.py remove --input v.mp4 --mode head --seconds 3 --output out.mp4

# 去尾 5 秒
python scripts/edit.py remove --input v.mp4 --mode tail --seconds 5 --output out.mp4

# 去多个区间(逗号分隔,格式 ss-t)
python scripts/edit.py remove --input v.mp4 --mode regions --exclude "10-5,20-3" --output out.mp4
# 去掉 10-15s 和 20-23s,其他保留
```

### Q35: 怎么调音量 / 加黑边 / 缩放?

A: `edit.py` 有对应子命令:

```bash
# 音量 0.5x(自己声太响)
python scripts/edit.py volume --input v.mp4 --factor 0.5 --output out.mp4

# 静音(关原声,只留 BGM)
python scripts/edit.py mute --input v.mp4 --output out.mp4

# 加黑边(竖屏 1080x1920)
python scripts/edit.py letterbox --input v.mp4 --width 1080 --height 1920 --output out.mp4

# 缩放到 720p
python scripts/edit.py scale --input v.mp4 --width 1280 --height 720 --output out.mp4
```

### Q36: 怎么转 GIF / 抽缩略图 / 一次性输出多分辨率?

A: `edit.py` P1 子命令:

```bash
# GIF(质量调高用 --fps 24)
python scripts/edit.py gif --input v.mp4 --output out.gif --width 480 --fps 15

# 抽 5 秒处的帧作为缩略图
python scripts/edit.py thumbnail --input v.mp4 --output thumb.jpg --time 5

# 一次性输出 3 个分辨率
python scripts/edit.py multi-res --input v.mp4 --output-dir out/ \
  --resolutions "480:360,720:540,1080:1920"
```
