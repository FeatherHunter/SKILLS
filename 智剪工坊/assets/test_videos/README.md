# test_videos/

标准化测试视频,用于子技能脚本自测。

## 需要的样片

| 文件 | 时长 | 分辨率 | 用途 |
|---|---|---|---|
| `test_30s_1080p.mp4` | 30s | 1920x1080 | 通用测试(剪切、转场、调色) |
| `test_60s_4k.mp4` | 60s | 3840x2160 | Step 1 降分辨率测试 |
| `test_5s_short.mp4` | 5s | 1920x1080 | xfade 转场测试(需要 2 段) |
| `test_various_fps/` | 任意 | 1080p | 60fps / 30fps / 23.976fps 多帧率,测 Bug 2 |

## 如何获得测试样片

```bash
# 从你的真实视频里抽 30 秒做测试
ffmpeg -ss 0 -i real_video.mp4 -t 30 -vf "scale=1920:1080,fps=30" test_30s_1080p.mp4

# 生成 4K 测试片(用 lavfi)
ffmpeg -f lavfi -i "testsrc2=size=3840x2160:rate=30:duration=60" -c:v libx264 test_60s_4k.mp4

# 生成不同帧率
ffmpeg -f lavfi -i "testsrc2=size=1920x1080:rate=60:duration=30" -c:v libx264 test_60fps.mp4
ffmpeg -f lavfi -i "testsrc2=size=1920x1080:rate=23.976:duration=30" -c:v libx264 test_24fps.mp4
```

## 自测命令

```bash
# 测 cut 脚本
python ../scripts/cut.py trim --input test_30s_1080p.mp4 --ss 0 --t 10 --out out.mp4

# 测 xfade 脚本
python ../scripts/xfade.py --a test_5s_short.mp4 --b test_5s_short.mp4 --type fade --duration 1 --out joined.mp4

# 测 step1 降分辨率
python ../scripts/pipeline_vlog.py step1 --input test_60s_4k.mp4 --output 1080p.mp4
```

## 当前状态

🚧 **空目录** —— 需要从你的真实视频抽 30 秒样片放这里。
