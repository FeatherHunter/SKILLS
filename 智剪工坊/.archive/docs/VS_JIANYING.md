# 智剪工坊 vs 剪映 —— 能力对比(2026 v0.5)

> 5 个剪映没有的差异化能力:去水词 / 美颜 CLI / 文字成片 / 数字人 / 改词翻唱

## 核心定位

| 维度 | 智剪工坊 | 剪映 |
|---|---|---|
| **形态** | 代码 / 命令行 | 图形化 App |
| **触发方式** | 自然语言(AI 路由) | 鼠标点击 |
| **适合** | 自动化、批量、API | 单条精细剪辑 |
| **学习曲线** | 中(懂 ffmpeg + Python) | 低(所见即所得) |
| **价格** | 免费(自建) | 免费 |
| **AI 能力** | 强(可定制) | 强(内置) |
| **生态** | ffmpeg 全功能 | 剪映模板库 |

## 功能对比表

| 功能 | 智剪工坊 | 剪映 |
|---|---|---|
| 剪切 | ✅ 精确到帧 | ✅ 拖拽 |
| 拼接 | ✅ concat demuxer | ✅ |
| 转场 | ✅ **60+ 种** | ✅ ~30 种 |
| 慢动作 | ✅ + 插帧(可丝滑) | ✅ 基础 |
| 推镜头 | ✅ zoompan 自动 | ✅ 关键帧 |
| 调色 | ✅ LUT + curves + 18 预设 | ✅ LUT + 滑块 |
| 烧字幕 | ✅ ffmpeg drawtext | ✅ |
| 加 BGM | ✅ 自动循环 | ✅ |
| BGM 节拍卡点 | ✅ librosa 自动 | ✅ 智能卡点 |
| AI 抠图 | ✅ rembg(开源) | ✅ 内置 |
| AI 字幕 | ✅ Whisper | ✅ 内置 |
| 封面 AI 生图 | ✅ matrix MCP + 中文叠字 | ❌ |
| J/L cut | ✅ adelay | ✅ 拖音频 |
| Speed ramp | ✅ setpts 曲线 | ✅ |
| 倒放 | ✅ setpts | ✅ |
| 多机位 | ✅ 4 路 sync | ✅ 拖拽 |
| 场景检测 | ✅ OpenCV 帧差 | ⚠️ 基础 |
| 重新构图 | ✅ face detection | ✅ 智能 |
| 风格迁移 | ✅ 矩阵卷积 | ❌ |
| **批量自动化** | ✅ **100 视频一次性** | ❌ 一个个做 |
| **金句自动检测** | ✅ NLP | ❌ |
| **🆕 去水词** | ✅ **word-level 精准切**(L2) | ❌ 只能手动剪 |
| **🆕 美颜 CLI** | ✅ 5 预设(磨皮/美白/瘦脸/大眼) | ✅ GUI 更强 |
| **🆕 文字成片** | ✅ matrix GenVideos | ✅ AI 成片 |
| **🆕 数字人** | ✅ matrix subject + TTS | ✅ 内置数字人 |
| **🆕 改词翻唱** | ✅ agent 改写 + 327 TTS 声音 | ✅ AI 改词 |
| 视频翻译 | ⚠️ 占位(走 rewrite_audio + auto_subtitle) | ✅ 内置 |
| 关键帧动画 | ✅ ffmpeg 表达式 | ✅ |
| HDR | ✅ 导入导出 | ⚠️ 部分支持 |

## 5 个智剪工坊独有的能力(剪映做不到/做不好)

### 1. **去水词 word-level 精准切**

**剪映:** 只能手动剪,且只能整句剪。

**智剪工坊:**
```bash
# 1. 转录(生成 SRT + words.json)
python scripts/ai_fillers.py transcribe --input vlog.mp4 --srt vlog.srt
# 2. Mavis agent 读 SRT,标水词
# 3. 切掉水词(只切那几个字,不动其他帧)
python scripts/ai_fillers.py cut --input vlog.mp4 --srt vlog.srt \
  --output clean.mp4 --remove-words "1,3,11,12,19,28,37,38,39,45"
```

20s vlog → 16.7s,精准切 10 个"嗯啊"水词。

### 2. **美颜 CLI 化(批量美颜)**

**剪映:** 单条精修,无法批量。

**智剪工坊:**
```bash
# 批量对 100 个视频美颜(改 batch.py 接入 beauty task)
for f in videos/*.mp4; do
  python scripts/ai_beauty.py --input "$f" --output "out/$f" --preset natural
done
```

### 3. **改词翻唱 agent-driven**

**剪映:** AI 改词是内置功能,不能定制。

**智剪工坊:**
```bash
# 1. transcribe
# 2. Mavis 读 SRT,改写成你想要的风格
# 3. synthesize(327 个 matrix 声音可选)
# 4. replace 音轨
```

**优势:** 改写风格完全由你(通过 Mavis 自然语言)控制,比如"改成小红书种草风" / "改成更幽默"。

### 4. **文字成片 + 数字人 自由组合**

**剪映:** AI 成片/数字人是黑盒,不可定制。

**智剪工坊:**
```bash
# 文字成片
python scripts/ai_text_to_video.py --prompt "..." --out part1.mp4

# 数字人
python scripts/ai_digital_human.py --avatar my_face.jpg --script "..." --out part2.mp4

# 拼接
python scripts/video_trim.py concat --list clips.txt --out final.mp4
```

**优势:** prompt 自由写,头像自由选,声音自由选。

### 5. **批量自动化(100+ 视频)**

**剪映:** 一个一个手动做。

**智剪工坊:**
```bash
# 批量加转场
python scripts/batch.py --input videos/ --task xfade --type fade --duration 0.5 --out out/

# 批量调色(cinematic preset)
python scripts/batch.py --input videos/ --task color --preset cinematic --out out/

# 进度条
[████░░░░░░░░░░░░░░░] 20% (5/25) ... 已完成 out/001.mp4
```

## 何时用哪个

### 用智剪工坊

- ✅ **批量处理** — 100 个视频统一加转场/调色
- ✅ **重复任务** — 每天/每周固定流程
- ✅ **AI 能力定制** — 你想加剪映没有的功能
- ✅ **API 集成** — 接其他系统自动跑
- ✅ **精确控制** — 帧级精度
- ✅ **去水词 / 改词 / 数字人** — 剪映做不到或不准
- ✅ **学习 ffmpeg** — 顺便学一门手艺

### 用剪映

- ✅ **单条精修** — 调色关键帧、复杂 mask
- ✅ **所见即所得** — 边看边改
- ✅ **模板丰富** — 节日、婚礼、Vlog
- ✅ **快速出片** — 5 分钟出片
- ✅ **手机端** — 拍完直接剪
- ✅ **声音克隆** — L3 能力剪映有,智剪工坊没做

## 推荐组合

```
日常 vlog / 单条:
  粗剪(智剪工坊 7 步流水线) → 去水词 → 精细调色/特效(剪映手动)

批量:
  智剪工坊 100% 自动化

AI 能力:
  智剪工坊(可定制,接 API)
  - 去水词 / 改词 / 数字人 → 智剪工坊
  - 声音克隆 / AI 成片 / 内置数字人 → 剪映

个人创作:
  剪映(上手快,模板多)
```

## 关键 bug 对比

| 问题 | 智剪工坊 | 剪映 |
|---|---|---|
| 视频损坏 | ⚠️ 偶尔(fps/编码 bug,已修) | ✅ 几乎不会 |
| 进度显示 | ✅ 进度条 + ETA | ✅ 进度条 + ETA |
| 失败排查 | ✅ safe_run 增强(5 种错误类型)+ 文件日志 | ✅ 弹窗提示 |

---

## 总结

- **剪映**:易上手、模板多、所见即所得、声音克隆强
- **智剪工坊**:可编程、批量化、AI 能力强(去水词 / 改词 / 文字成片 / 数字人)

**最佳实践:** 智剪工坊做粗活(批量 + 去水词 + 改词),剪映做精修(关键帧调色 + 声音克隆)。

🎯 **一句话:剪映做不了的(批量 + 去水词 + word-level 改词),用智剪工坊;剪映做得到的(单条精修 + 声音克隆),用剪映。**
