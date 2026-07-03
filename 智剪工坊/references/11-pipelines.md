# 11 - pipelines (大流程模板)

## 触发词

"完整 vlog"、"一条龙"、"7 步流水线"、"从素材到发布版"、"全自动"

## 已实现的大流程

### pipeline-vlog(7 步 vlog 流水线)

**适用场景:** 从零散的拍摄素材,自动产出可发布的 vlog 视频。

**输入:**
- 一个文件夹路径,包含 N 段原始视频(MP4/MOV)
- 主题描述(可选)

**输出:**
- `final.mp4` —— 完整成片(竖屏 1080x1920,30fps,带字幕 + BGM)
- `cover.jpg` —— AI 生成封面
- `subtitles.srt` —— 字幕文件
- `pipeline_log.md` —— 处理日志

**7 步流程:**

```
[Step 1] 4K → 1080p 降分辨率
  ↓
[Step 2] Whisper GPU 转录所有段(带时间戳)
  ↓
[Step 3] 抽关键帧(每 15s 一帧)
  ↓
[Step 4] AI 分析生成剪辑建议(SRT + 帧 → markdown)
  ↓
[Step 5] 用户勾选保留秒数(4 选 1)
  ↓
[Step 6] ffmpeg 拼接 + 烧字幕 + BGM + 压缩
  ↓
[Step 7] 抽封面 + 输出最终交付物
```

**调用方式:**

```bash
# 一行命令触发整个流程
python scripts/pipeline_vlog.py \
  --input videos/ \
  --theme "Day 1 减肥日记" \
  --output day1_vlog/
```

**运行时间预估:**
- 10 段视频(共 30 分钟):约 15-20 分钟
- 30 段视频(共 90 分钟):约 40-60 分钟

### pipeline-fitness(健身专属)

基于 pipeline-vlog,但针对健身内容做了优化:
- 自动识别"暴汗"瞬间(用 OpenCV 检测肤色变化)
- 自动添加心率/卡路里字幕
- 自动应用"运动风" LUT 调色

### pipeline-edu(教程类)

针对知识分享类视频优化:
- 自动识别"重点句"(NLP 分析)
- 自动添加标题卡(片头 / 章节标记)
- 自动应用"教学风"调色

## 子技能组合关系

```
pipeline-vlog =
  cut
  + ai-features (Whisper 转录)
  + ai-features (抽关键帧)
  + cover-ai
  + text (烧字幕)
  + audio (BGM 循环混音)

pipeline-fitness =
  pipeline-vlog
  + effects (运动特效)
  + color (健身 LUT)

pipeline-edu =
  pipeline-vlog
  + text (标题卡)
  + color (教学 LUT)
```

## 流水线设计原则

1. **失败可重试**:每步独立,失败可单独重跑
2. **中间产物保留**:`_clips/` `_subtitles/` `_frames/` 不删除
3. **进度可视化**:每步打印状态,用户能看到进度
4. **人工干预点**:Step 5(用户勾选)必须有,不能让 AI 100% 自主
5. **验证机制**:ffprobe 验证每步输出,确保不出现"假成功"

## 未来扩展

- [ ] pipeline-travel(旅行 vlog 模板)
- [ ] pipeline-food(美食 vlog 模板)
- [ ] pipeline-tech(科技评测模板)
- [ ] pipeline-music(MV 模板)
- [ ] pipeline-business(商业宣传片模板)

## 调用示例

```
用户: "做一段完整 vlog,从素材到发布版"
→ pipeline-vlog --input videos/ --theme "Day 1" --output day1/
```

```
用户: "健身 vlog 流水线"
→ pipeline-fitness --input videos/ --theme "Day 2 健身"
```

## 关键 bug 教训(详见 SKILL.md)

1. **NVENC 随机崩溃** → 用 libx264
2. **fps 不一致 → 8 小时视频** → 强制 fps=30
3. **AI 中文乱码** → 后叠中文
4. **脚本"假成功"** → 必须 ffprobe 验证