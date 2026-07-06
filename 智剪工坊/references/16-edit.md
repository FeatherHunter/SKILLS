# 16-edit - 14 原子操作 — v1.2 已实现

> **对应脚本**: `scripts/edit.py`
> **触发词**: "去头去尾"、"调音量"、"静音"、"黑边"、"缩放"、"裁剪"、"旋转"、"翻转"、"提音"、"淡入淡出"
> **实测状态**: ✅ 验证通过

---

## 1. 调用范式

### 场景 1

```bash
# 1. remove - 去头/去尾/去中间(可多段)
python scripts/edit.py remove --input v.mp4 --mode head --seconds 3 --output out.mp4
python scripts/edit.py remove --input v.mp4 --mode tail --seconds 5 --output out.mp4
python scripts/edit.py remove --input v.mp4 --mode regions --exclude "10-5,20-3" --output out.mp4
# 模式:head / tail / regions
# regions 的 --exclude 格式: "ss1-t1,ss2-t2" 逗号分隔

# 2. volume - 调音量(0=静音, 1=不变, 2=2倍)
python scripts/edit.py volume --input v.mp4 --factor 0.5 --output out.mp4

# 3. mute - 静音/删除音轨
python scripts/edit.py mute --input v.mp4 --output out.mp4

# 4. letterbox - 加黑边
python scripts/edit.py letterbox --input v.mp4 --width 1080 --height 1920 --bg black --output out.mp4

# 5. scale - 缩放
python scripts/edit.py scale --input v.mp4 --width 320 --height 240 --output out.mp4

# 6. crop - 裁剪
python scripts/edit.py crop --input v.mp4 --x 100 --y 50 --width 200 --height 200 --output out.mp4

# 7. rotate - 旋转 90/180/270
python scripts/edit.py rotate --input v.mp4 --degrees 90 --output out.mp4

# 8. flip - 翻转(水平/垂直)
python scripts/edit.py flip --input v.mp4 --mode h --output out.mp4
# mode: h (水平) / v (垂直)

# 9. extract-audio - 提取音频
python scripts/edit.py extract-audio --input v.mp4 --output audio.mp3 --format mp3
# format: mp3 / wav / aac

# 10. fade-audio - 音频淡入淡出
python scripts/edit.py fade-audio --input v.mp4 --fade-in 2 --fade-out 3 --output out.mp4

# 11. watermark - 加 logo 水印
python scripts/edit.py watermark --input v.mp4 --logo logo.png --position topright --opacity 0.7 --output out.mp4
# position: topleft / topright / bottomleft / bottomright

# 12. multi-res - 多分辨率输出
python scripts/edit.py multi-res --input v.mp4 --output-dir out/ --resolutions "480:360,720:540,1080:1920"

# 13. gif - GIF 导出
python scripts/edit.py gif --input v.mp4 --output out.gif --width 480 --fps 15
# 可选: --start 0 --duration 全片

# 14. thumbnail - 抽 1 帧作为缩略图
python scripts/edit.py thumbnail --input v.mp4 --output thumb.jpg --time 5
# time: 抽哪一秒
```

### 场景 2

```bash
for f in videos/*.mp4; do
  python scripts/edit.py volume --input "$f" --factor 0.5 --output "out/$f"
done
```

## 2. 参数

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--input` | `-i` | (必填) | 输入视频/音频/图片 |
| `--output` | `-o` | (必填) | 输出路径 |

## 3. 常见错误 / 限制

- `remove` 用 trim + concat,段数多时慢(>5 段建议合并)
- `multi-res` 不支持 `-vcodec` 覆盖(都用 libx264)
- `gif` 默认 fps=15,质量调高需要 `--fps 24` 但文件大
- `watermark` 的 logo 必须是 PNG(透明背景)
---

## 4. 相关参考

- **SKILL.md §14 子技能索引**：本子技能的路由表
- **scripts/README.md**：scripts/ 目录命名规范（`<维度>_<动作>.py`）
- `.archive/CHANGELOG.md`：本子技能历史变更

---

<details>
<summary>📋 原文存档（v0.5 旧版，仅供 git history 追溯）</summary>

# 子技能 16 · edit(14 个原子操作) — v0.6 已实现

> **对应脚本:** `scripts/edit.py`(1 个,14 个子命令 P0 8 + P1 6)
> **实测状态:** ✅ 17/17 冒烟测试通过(包含 watermark)
> **架构选择:** 14 个原子操作放 1 个脚本(避免 14 个新文件),按子命令分类

```bash
# 1. remove - 去头/去尾/去中间(可多段)
python scripts/edit.py remove --input v.mp4 --mode head --seconds 3 --output out.mp4
python scripts/edit.py remove --input v.mp4 --mode tail --seconds 5 --output out.mp4
python scripts/edit.py remove --input v.mp4 --mode regions --exclude "10-5,20-3" --output out.mp4
# 模式:head / tail / regions
# regions 的 --exclude 格式: "ss1-t1,ss2-t2" 逗号分隔

# 2. volume - 调音量(0=静音, 1=不变, 2=2倍)
python scripts/edit.py volume --input v.mp4 --factor 0.5 --output out.mp4

# 3. mute - 静音/删除音轨
python scripts/edit.py mute --input v.mp4 --output out.mp4

# 4. letterbox - 加黑边
python scripts/edit.py letterbox --input v.mp4 --width 1080 --height 1920 --bg black --output out.mp4

# 5. scale - 缩放
python scripts/edit.py scale --input v.mp4 --width 320 --height 240 --output out.mp4

# 6. crop - 裁剪
python scripts/edit.py crop --input v.mp4 --x 100 --y 50 --width 200 --height 200 --output out.mp4

# 7. rotate - 旋转 90/180/270
python scripts/edit.py rotate --input v.mp4 --degrees 90 --output out.mp4

# 8. flip - 翻转(水平/垂直)
python scripts/edit.py flip --input v.mp4 --mode h --output out.mp4
# mode: h (水平) / v (垂直)

# 9. extract-audio - 提取音频
python scripts/edit.py extract-audio --input v.mp4 --output audio.mp3 --format mp3
# format: mp3 / wav / aac

# 10. fade-audio - 音频淡入淡出
python scripts/edit.py fade-audio --input v.mp4 --fade-in 2 --fade-out 3 --output out.mp4

# 11. watermark - 加 logo 水印
python scripts/edit.py watermark --input v.mp4 --logo logo.png --position topright --opacity 0.7 --output out.mp4
# position: topleft / topright / bottomleft / bottomright

# 12. multi-res - 多分辨率输出
python scripts/edit.py multi-res --input v.mp4 --output-dir out/ --resolutions "480:360,720:540,1080:1920"

# 13. gif - GIF 导出
python scripts/edit.py gif --input v.mp4 --output out.gif --width 480 --fps 15
# 可选: --start 0 --duration 全片

# 14. thumbnail - 抽 1 帧作为缩略图
python scripts/edit.py thumbnail --input v.mp4 --output thumb.jpg --time 5
# time: 抽哪一秒
```

---

## 14 个子命令详解

### P0 基础画面/音频(8 个)

| # | 子命令 | ffmpeg 实现 | 用户场景 |
|---|---|---|---|
| 1 | `remove` | trim + concat(多段) | 切头切尾切中间,删水词前的准备 |
| 2 | `volume` | `volume filter` | vlog 自己声太响/太轻 |
| 3 | `mute` | `-an` | 关闭原声只保留 BGM |
| 4 | `letterbox` | scale + pad | 加字幕后调比例(上下加黑边) |
| 5 | `scale` | `scale filter` | 缩放分辨率(转 720p) |
| 6 | `crop` | `crop filter` | 切掉水印/不需要的边 |
| 7 | `rotate` | `transpose filter` | 横屏转竖屏 |
| 8 | `flip` | `hflip/vflip filter` | 镜像自拍 |

### P1 扩展(6 个)

| # | 子命令 | 实现 | 用户场景 |
|---|---|---|---|
| 9 | `extract-audio` | `-vn + acodec` | 提取视频里的 BGM |
| 10 | `fade-audio` | `afade filter` | BGM 淡入淡出 |
| 11 | `watermark` | overlay + alpha | 加 logo 角标 |
| 12 | `multi-res` | scale 多次 | 一次输出 480/720/1080 |
| 13 | `gif` | palettegen + paletteuse | 转 GIF 分享 |
| 14 | `thumbnail` | `-vframes 1` | 抽帧作封面图 |

---

## 设计选择(从第一性原理)

**为什么 14 个放 1 个脚本(而不是 14 个文件)?**
- 子命令都是"原子操作",逻辑相似(都是 ffmpeg 调用 + 统一 vf + 编码)
- 14 个独立文件 = 14 个 README / 14 个 help,管理成本高
- 1 个文件 + 14 个子命令 = 集中维护,统一接口
- 用户用 `--help` 看一次就知道所有能力

**为什么 `remove` 用 1 个子命令 + 3 个 mode(而不是 3 个子命令)?**
- 用户心智:"我要去掉 X"是 1 个意图
- 实现上:head/tail 是 regions 的特例(mode=head 等于"去掉 0-N",mode=tail 等于"去掉 dur-N 到 dur")
- 1 个子命令 + mode 参数 = 接口更简洁

---

## 已知限制

- `remove` 用 trim + concat,段数多时慢(>5 段建议合并)
- `multi-res` 不支持 `-vcodec` 覆盖(都用 libx264)
- `gif` 默认 fps=15,质量调高需要 `--fps 24` 但文件大
- `watermark` 的 logo 必须是 PNG(透明背景)

---

## 常见问题

**Q: `remove --mode regions --exclude "10-5,20-3"` 啥意思?**
A: 去掉 10-15s 段 + 20-23s 段,其他保留。逗号分隔多区间。

**Q: `letterbox` 和 `scale` 区别?**
A: `scale` 直接缩放(可能变形);`letterbox` 等比缩放后加黑边(不变形)。

**Q: `multi-res` 输出文件名规则?**
A: `{input_stem}_{w}x{h}.mp4`,例:input=test.mp4 → test_320x240.mp4, test_640x480.mp4。

**Q: 14 个子命令可以 batch 吗?**
A: 暂时不支持,需要用 shell 循环:
```bash
for f in videos/*.mp4; do
  python scripts/edit.py volume --input "$f" --factor 0.5 --output "out/$f"
done
```

---

## 相关脚本

- 依赖:无
- 同类:`scripts/video_trim.py`(trim/concat) — 部分重叠但语义不同
- 前置:无
- 后置:无


</details>
