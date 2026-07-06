# 图片转视频 - 静态图KenBurns效果

> **对应脚本**: `scripts/image_to_video.py`
> **触发词**: "图片"、"照片"、"插图"、"配图"、"静态图"、"Ken Burns"、"推近"、"拉远"
> **实测状态**: ✅ 验证通过（v1.3 8 场景严格测试 0 BUG, 集成 concat 通过）

---

## 1. 为什么需要

`xfade_concat` / `concatenate_simple` 都假设输入是 h264 + aac 的 mp4 视频流。**图片流不能直接进**。

AI 在 §阶段 2 编排时,遇到图片素材**必须先调 `image_to_video.py`** 转成 mp4,再进 concat。

## 2. 调用范式

```bash
# 默认: 3秒静态图, 1920x1080, 30fps
python scripts/image_to_video.py --image photo.jpg --output photo.mp4

# 自定义时长 5秒
python scripts/image_to_video.py --image photo.jpg --output photo.mp4 --duration 5

# Ken Burns 推近 (1.0 → 1.15 倍, 5秒)
python scripts/image_to_video.py --image photo.jpg --output photo.mp4 --duration 5 --ken-burns-in

# Ken Burns 拉远 (1.15 → 1.0 倍, 5秒)
python scripts/image_to_video.py --image photo.jpg --output photo.mp4 --duration 5 --ken-burns-out

# 自定义分辨率 (9:16 项目)
python scripts/image_to_video.py --image photo.jpg --output photo.mp4 --width 1080 --height 1920
```

## 3. 参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `--image` | path | (必填) | 输入图片文件（.jpg/.png/.webp/.bmp）|
| `--output` | path | (必填) | 输出视频文件（.mp4）|
| `--duration` | float | 3.0 | 片段时长（秒）|
| `--width` | int | 1920 | 输出宽度（按项目 aspect_ratio 选）|
| `--height` | int | 1080 | 输出高度 |
| `--fps` | int | 30 | 帧率（与 video_normalize 保持一致）|
| `--ken-burns-in` | flag | off | Ken Burns 推近（1.0 → 1.15 倍）|
| `--ken-burns-out` | flag | off | Ken Burns 拉远（1.15 → 1.0 倍）|

**互斥约束**: `--ken-burns-in` 和 `--ken-burns-out` 不能同时为 True。

## 4. 行为细节

- **缩放 + letterbox**: `force_original_aspect_ratio=decrease` + 黑边居中（不变形）
- **音频**: 自动加 `anullsrc=r=44100:cl=stereo` 静音音轨（保证后续 concat 不报错）
- **Ken Burns**: 用 `zoompan` filter 实现,缩放变化温和（5% 范围, 适合静态图增动感）
- **输出**: h264 + aac + 30fps + yuv420p + faststart, 与 video_normalize 默认对齐

## 5. AI 编排流程

1. 读取 `sequences[i].photos[]` 列表
2. 对每个 photo 元素,调 `image_to_video.py`:
   - 转换结果保存到 `workspace/00_智剪/粗加工/photo_<idx>.mp4`
   - 转换时按 `photos[i].effect` 决定 Ken Burns:
     - `static` (默认) → 静态图
     - `ken-burns-in` → 推近
     - `ken-burns-out` → 拉远
   - 转换时按 `photos[i].duration` 决定时长（默认 3.0s）
3. 转完所有 photo 后,把它们作为 mp4 加入 `sequences[i].videos[]` 列表
4. 走 §G.2 (transitions / xfade_concat / concatenate_simple)

## 6. 严格测试已通过（8 场景 0 BUG）

| 场景 | 期望 | 实际 |
|---|---|---|
| 静态图默认 3s | 3.0s | 3.00s |
| 自定义时长 5s | 5.0s | 5.00s |
| Ken Burns 推近 5s | 5.0s | 5.00s |
| Ken Burns 拉远 5s | 5.0s | 5.00s |
| 极小图 100x100 | 3.0s | 3.00s |
| 竖图 1080x1920 letterbox | 3.0s | 3.00s |
| 不支持格式 .txt | 拒绝 | 拒绝 ✅ |
| **集成: 图片+视频混合拼接** | 16s | **16.04s** |

## 7. intent.html 字段对照

| 字段 | 路径 | 类型 | 可选值 / 格式 | 说明 |
|---|---|---|---|---|
| `file` | `sequences[i].photos[i].file` | string | 文件名 | 图片素材文件名 |
| `duration` | `sequences[i].photos[i].duration` | float | **秒**,默认 `3.0` | 图片作为片段的时长 |
| `effect` | `sequences[i].photos[i].effect` | string | `static` / `ken-burns-in` / `ken-burns-out`,默认 `static` | Ken Burns 效果 |

**注意**: `ken-burns-in` 命名带 `ken-burns-` 前缀,避免和 `transitions[].type='zoom-in'` 混淆。

## 8. 常见错误

- **图片格式不支持**: `.txt` / `.gif` / `.svg` / `.heic` 会被拒绝（支持 .jpg/.png/.webp/.bmp）
- **GIF 特殊处理**: GIF 应先转 mp4（用 ffmpeg image2 或更高级的 gifsicle）,再走 image_to_video
- **HEIC 特殊处理**: iPhone 照片常用 .heic,需先转 .jpg（用 ffmpeg 或 exiftool）

## 9. 相关参考

- **SKILL.md §G.1.b**: image_to_video 简要说明
- **SKILL.md §H**: 字段枚举表 photos
- **references/主流程-阶段编排.md**: §阶段 2 处理图片素材的详细流程
