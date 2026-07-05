# 02 - transitions (转场 / xfade) — v0.5 已实现

> **对应脚本:** `scripts/xfade.py`(1 个,60+ 转场)
> **实测状态:** ✅ 验证通过

```bash
python scripts/xfade.py --a clip1.mp4 --b clip2.mp4 --type fade --duration 1 --output joined.mp4
```

---

## 触发词

"转场"、"淡入淡出"、"溶解"、"擦除"、"切换"、"黑场"、"白闪"、"圆形转场"、"像素化"、"径向"

## 输入 / 输出

- **输入**: 2 个视频(片段 A 和片段 B)
- **输出**: A → 转场 → B 合并后的视频

## 参数

| 参数 | 说明 | 默认 |
|---|---|---|
| `--a` | 输入视频 A | 必填 |
| `--b` | 输入视频 B | 必填 |
| `--type` | 转场类型 | fade |
| `--duration` | 转场时长(秒) | 1 |
| `--offset` | 转场起始时间(相对 A) | A 的时长 - duration |
| `--output` | 输出文件 | 必填 |

## 支持的转场类型

| 类型 | 效果 |
|---|---|
| `fade` | 淡入淡出(经典) |
| `dissolve` | 溶解 |
| `wipeleft` / `wiperight` | 左右擦除 |
| `wipeup` / `wipedown` | 上下擦除 |
| `slideleft` / `slideright` | 左右滑动 |
| `slideup` / `slidedown` | 上下滑动 |
| `circleopen` / `circleclose` | 圆形打开/关闭 |
| `fadeblack` | 黑场过渡 |
| `fadewhite` | 白闪过渡 |
| `radial` | 径向 |
| `squeeze` | 挤压 |
| `pixelize` | 像素化 |
| `hlslice` / `hrslice` | 横向分割 |
| `vuslice` / `vdslice` | 竖向分割 |
| `diagtl` / `diagtr` | 对角线 |

ffmpeg 支持 **60+ 种转场**,完整列表参见 [ffmpeg xfade docs](https://ffmpeg.org/ffmpeg-filters.html#xfade)。

## 核心命令

```bash
ffmpeg -i [a.mp4] -i [b.mp4] \
  -filter_complex "xfade=transition=[type]:duration=[duration]:offset=[offset]" \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 128k \
  [output.mp4]
```

## 调用示例

```
用户: "把这两段加个 1 秒淡入淡出转场"
→ xfade --a clip1.mp4 --b clip2.mp4 --type fade --duration 1 --output joined.mp4
```

```
用户: "用黑场过渡"
→ xfade --a a.mp4 --b b.mp4 --type fadeblack --duration 0.5
```

## 限制 / 注意

1. **A 和 B 分辨率必须一致**(否则需要先 scale 统一)
2. **A 和 B 帧率必须一致**(否则需要先 fps 统一)
3. **offset**:转场起始时间,默认是 A 时长 - duration(让转场正好在拼接点)
4. **音频**:ffmpeg xfade 默认不处理音频,需要手动 `acrossfade` 处理

## 音频转场(可选)

```bash
ffmpeg -i a.mp4 -i b.mp4 \
  -filter_complex "[0:a]afade=t=out:st=4:d=1[a0];\
                   [1:a]afade=t=in:st=0:d=1[a1];\
                   [a0][a1]concat=n=2:v=0:a=1[a]" \
  -c:v libx264 ... \
  [output.mp4]
```

## 进阶:多段转场链

3+ 段视频需要逐个 xfade + overlay,比较复杂,推荐用 **剪映手动** 或写 Python 脚本批量生成。