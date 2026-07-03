# 10 - batch (批量处理)

## 触发词

"批量"、"100 个视频都..."、"批处理"、"批量转码"、"批量加转场"、"批量调色"

## 为什么批量重要

剪映一辈子也做不完的事,代码 5 分钟搞定:
- 100 个视频加同一个转场
- 100 个视频统一格式转码
- 100 张图片统一加水印
- 100 个音频统一响度

## 输入 / 输出

- **输入**: 文件夹路径 + 通配符模式(如 `*.mp4`)
- **输出**: 处理后的文件(可保持原名 / 重命名)

## A. 批量剪切(统一时长)

```python
# scripts/batch_cut.py
import subprocess
from pathlib import Path

def batch_trim(input_dir, output_dir, duration=30):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for video in input_dir.glob("*.mp4"):
        output = output_dir / video.name
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-t", str(duration),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,\
                    pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            str(output)
        ]
        subprocess.run(cmd, capture_output=True)
        print(f"[done] {video.name} -> {output.name}")
```

## B. 批量加转场(配对处理)

```python
# scripts/batch_xfade.py
import subprocess
from pathlib import Path

def batch_xfade(input_dir, output_file, transition="fade", duration=1):
    """把所有视频按顺序用转场串起来"""
    videos = sorted(Path(input_dir).glob("*.mp4"))
    
    # 构建 filter_complex
    inputs = []
    for v in videos:
        inputs.extend(["-i", str(v)])
    
    # 简化:只支持 2 段(更多段需要递归)
    if len(videos) < 2:
        return
    
    filter_str = f"xfade=transition={transition}:duration={duration}:offset=9"
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_str,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        str(output_file)
    ]
    subprocess.run(cmd, capture_output=True)
```

## C. 批量转码

```python
# scripts/batch_convert.py
import subprocess
from pathlib import Path

def batch_convert(input_dir, output_dir, target_format="mp4"):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for video in input_dir.glob(f"*.{target_format}"):
        # 例如 mkv -> mp4
        output = output_dir / (video.stem + "_converted.mp4")
        cmd = [
            "ffmpeg", "-y", "-i", str(video),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(output)
        ]
        subprocess.run(cmd, capture_output=True)
```

## D. 批量加封面图(视频叠加图片)

```python
# scripts/batch_cover.py
import subprocess
from pathlib import Path

def batch_add_cover(video_dir, image_path, output_dir, duration=3):
    """给每个视频开头加 3 秒封面"""
    video_dir = Path(video_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for video in video_dir.glob("*.mp4"):
        output = output_dir / video.name
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(duration), "-i", image_path,
            "-i", str(video),
            "-filter_complex", "[0:v]scale=1080:1920[s];\
                                [1:v]scale=1080:1920:force_original_aspect_ratio=decrease,\
                                pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black[m];\
                                [s][m]concat=n=2:v=1:a=0[v];\
                                [0:a][1:a]concat=n=2:v=0:a=1[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            str(output)
        ]
        subprocess.run(cmd, capture_output=True)
```

## E. 并行处理(加速)

```python
# scripts/batch_parallel.py
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing

def process_one(video_path):
    # 单个视频的处理函数
    pass

def batch_parallel(input_dir, max_workers=None):
    if max_workers is None:
        max_workers = multiprocessing.cpu_count()
    
    videos = list(Path(input_dir).glob("*.mp4"))
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_one, videos)
```

## F. AI 批量处理

```python
# scripts/batch_ai.py
# 用 Whisper 转录一个文件夹里所有视频
import subprocess
from pathlib import Path

def batch_transcribe(video_dir, output_dir):
    """所有视频批量 Whisper 转录"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for video in Path(video_dir).glob("*.mp4"):
        srt_output = output_dir / (video.stem + ".srt")
        # 用 faster-whisper CLI
        cmd = [
            "faster-whisper", str(video),
            "--model", "medium",
            "--device", "cuda",
            "--output_dir", str(output_dir),
            "--output_format", "srt"
        ]
        subprocess.run(cmd, capture_output=True)
```

## 调用示例

```
用户: "这个文件夹里所有视频都裁剪成前 30 秒"
→ batch --task trim --input videos/ --duration 30
```

```
用户: "把所有视频都加上同一个封面图"
→ batch --task cover --input videos/ --cover cover.jpg
```

```
用户: "批量把所有 mkv 转成 mp4"
→ batch --task convert --input videos/ --format mp4 --from mkv
```

## 限制 / 注意

1. **CPU/GPU 占用**:批量处理会占满所有资源,可能让电脑变卡
2. **并行数**:ProcessPoolExecutor 适合 CPU 密集,ThreadPoolExecutor 适合 I/O 密集
3. **错误处理**:批量处理时单个失败不应该中断整个批次
4. **进度条**:建议加 tqdm 显示进度