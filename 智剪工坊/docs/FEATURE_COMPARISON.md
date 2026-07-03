# 智剪工坊 · 功能对比与 Gap 分析

> 2026-07-03 v0.5 更新 · 30 脚本全实现 · 5 个 AI 增强(美颜/去水词/改词/文字成片/数字人)

## 一、四大主流软件核心能力(2025 公开资料)

| 类别 | 剪映 | Premiere Pro 2025 | DaVinci Resolve 20 | Final Cut Pro 11 |
|---|---|---|---|---|
| **剪辑** | 切割/倒放/0.2-100x 变速 | 多机位/3 路剪辑 | Cut/Edit 双页 | 磁性时间线 |
| **转场** | ~30 种 | 90+ GPU 加速 | 100+ | 130+ FxPlug |
| **调色** | 18 预设 + 美颜 | LUT + Curves | **节点式(行业最强)** | 曲线 + 色轮 |
| **字幕** | AI 98.7% / 27 语 | 27 语翻译 | 字幕 + 闭路字幕 | 自动 + 多语 |
| **音频** | 变声 12 种 | 降噪 90% | **Fairlight 2000 轨** | Logic 集成 |
| **特效** | 100+ 滤镜 + 蒙版 | Firefly 视频扩展 | **Fusion 节点** | 200+ 滤镜 + Motion |
| **AI 能力** | AI 成片/改词/数字人 | Generative Extend | IntelliScript / Magic Mask | 智能蒙版/视觉搜索 |
| **VFX/3D** | 蒙版 + 简单 3D | Dynamic Link AE | **Fusion 节点** | USDZ 3D + Motion |
| **协作** | 云协作 | Creative Cloud | Blackmagic Cloud | iCloud |
| **价格** | 免费 | ¥235/月 | **免费(90%功能)** | ¥1998 买断 |

## 二、智剪工坊现状(2026 v0.5)

### ✅ 已实现 15 子技能 / 30 脚本

| # | 子技能 | 脚本数 | 能力 |
|---|---|---|---|
| 01 | cutting | 1 | 剪切(帧级)+ 拼接(concat demuxer) |
| 02 | transitions | 1 | 60+ 转场(fade/wipe/slide/zoom/dissolve) |
| 03 | effects | 2 | 慢动作 / 推镜头(zoompan)/ 关键帧动画 |
| 04 | cinematic | 3 | J-cut / L-cut / 倒放 / speed ramp / 曲线变速 / 多机位 |
| 05 | color | 3 | 18 预设 + LUT + 风格迁移(矩阵卷积)/ HDR 导入导出 |
| 06 | text | 3 | 自动字幕(Whisper 烧字幕)/ 变声 12 种 / 翻译(占位) |
| 07 | audio | 2 | BGM 循环混音 / 节拍卡点(librosa) |
| 08 | cover | 1 | AI 生图 + 中文叠字(两步法) |
| 09 | ai-features | 7 | 抠图(rembg)/ 金句检测 / 场景检测 / 蒙版 / 画中画 / 重新构图 / **去水词**(word-level) |
| 10 | batch | 1 | 进度条 + 5 个 task(xfade/color/reencode/concat/cover) |
| 11 | pipelines | 1 | 7 步 vlog 流水线(转录→分析→拼接→字幕→BGM→封面) |
| 12 | **🆕 beauty** | 1 | **美颜**(磨皮/美白/瘦脸/大眼,5 预设) |
| 13 | **🆕 rewrite-audio** | 1 | **改词翻唱**(Whisper + agent 改写 + matrix TTS 327 声音) |
| 14 | **🆕 text-to-video** | 1 | **文字成片**(mmx matrix_gen_videos) |
| 15 | **🆕 digital-human** | 1 | **数字人**(mmx subject + TTS) |

### ⚠️ 已知限制

- L3 声音克隆(用自己声音)— matrix MCP 只暴露 327 预置声音
- 数字人嘴型精准对齐 — mmx subject 模式只"保持人脸动",不保证嘴型精准
- 4K 大文件处理慢 — 建议降分辨率到 1080p
- 跨平台 — Mac/Linux setup.sh 写好但只测 Windows

## 三、差异化定位(智剪工坊 vs 剪映)

| 维度 | 智剪工坊优势 | 剪映优势 |
|---|---|---|
| **批量** | ✅ 100 视频一键 | ❌ |
| **AI 定制** | ✅ 任意接 API | ⚠️ 闭源 |
| **CLI 自动化** | ✅ 跑定时任务 | ❌ |
| **精确控制** | ✅ 帧级 | ⚠️ 关键帧 |
| **价格** | ✅ 免费 | ✅ 免费 |
| **去水词** | ✅ **word-level 精准切**(剪映做不到) | ❌ 只能手动剪 |
| **美颜 CLI** | ✅ 命令行 + 5 预设 | ✅ GUI 更强 |
| **文字成片 + 数字人** | ✅ 程序员可定制 | ✅ 用户更友好 |
| **改词翻唱** | ✅ 自然语言路由到 agent | ✅ GUI |
| **特效/调色** | ⚠️ 中等 | ✅ 强 |
| **上手难度** | ⚠️ 中(懂命令行) | ✅ 低 |
| **模板生态** | ❌ | ✅ |

## 四、Gap 分析(2026 v0.5 视角)

### P0 已补(2026-07-03 v0.5 前)

| 缺口 | 实现 | 状态 |
|---|---|---|
| 倒放 | `scripts/reverse.py` | ✅ |
| 曲线变速 | `scripts/speed.py` | ✅ |
| 画中画 | `scripts/overlay.py` | ✅ |
| 蒙版(基础) | `scripts/mask.py` | ✅ |
| 变声 | `scripts/voice_change.py` | ✅ |
| 风格化滤镜 | `scripts/color_style.py` | ✅ |
| 节拍卡点 | `scripts/beat_sync.py` | ✅ |

### P1 已补(2026-07-03 v0.5 前)

| 缺口 | 实现 | 状态 |
|---|---|---|
| AI 字幕自动生成 | `scripts/auto_subtitle.py` | ✅ |
| 多机位剪辑 | `scripts/multicam.py` | ✅ |
| AI 场景检测 | `scripts/scene_detect.py` | ✅ |
| 自动重新构图 | `scripts/reframe.py` | ✅ |
| 风格迁移 | `scripts/style_transfer.py` | ✅ |
| 关键帧动画 | `scripts/keyframe.py` | ✅ |
| HDR 导入导出 | `scripts/hdr_io.py` | ✅ |
| AI 抠图 | `scripts/cutout.py` | ✅ |
| 金句检测 | `scripts/quotes.py` | ✅ |
| 批量处理 | `scripts/batch.py` | ✅ |

### P2 战略差异(智剪工坊独有)已补

| 缺口 | 实现 | 状态 |
|---|---|---|
| **批量自动化** | `scripts/batch.py` | ✅ |
| **金句自动检测** | `scripts/quotes.py` | ✅ |
| **AI 抠图** | `scripts/cutout.py` | ✅ |
| **AI 文字成片** | `scripts/text_to_video.py` | ✅ |
| **AI 数字人** | `scripts/digital_human.py` | ✅ |
| **美颜 CLI** | `scripts/beauty.py` | ✅ |
| **去水词** | `scripts/remove_fillers.py` | ✅ |
| **改词翻唱** | `scripts/rewrite_audio.py` | ✅ |
| 视频翻译 | `scripts/translate.py` | ⚠️ 占位(转 TTS 用 rewrite_audio) |

### P3 不补(剪映特色 / 不切实际)

| 缺口 | 不补的理由 |
|---|---|
| 模板市场 | 是产品/社区问题 |
| 团队协作 | 单机工具不需要 |
| 3D 文字 / USDZ | ffmpeg 不擅长 |
| 立体视频 / 空间视频 | 极小众 |
| Compressor 集成 | FCP 专属 |
| 移动端 / iPad 端 | 代码不切实际 |
| L3 声音克隆(用自己的声音) | 需自训模型,投入大 |

## 五、未来 Roadmap

### v0.6(下一步)— 真实 vlog 实测

- [ ] 跑通真实 vlog 全流程(30 分钟)
- [ ] 美颜 / 去水词 / 改词 / 文字成片 / 数字人 5 个 AI 功能真实 vlog 实测
- [ ] 修实测中暴露的 bug
- [ ] 加 mmx 视频生成的 batch 模式

### v0.7 — SadTalkers / Wav2Lip(精准嘴型)

- [ ] 接本地 SadTalkers,数字人嘴型精准对齐
- [ ] Wav2Lip fallback

### v0.8 — 拼装 L3(组合 AI 能力)

- [ ] 视频翻译闭环(Whisper + 翻译 + TTS + 字幕烧录)
- [ ] AI 数字人 + 自动字幕 + BGM 一条龙

### v1.0 — 跨平台

- [ ] Mac/Linux 完整测试
- [ ] Docker 镜像
- [ ] CI/CD(目前单元测试 0%)

## 六、版本记录

- v0.1 (2026-07-03) - 首次对比(5 脚本,6 占位)
- v0.2 (2026-07-03) - A 路线补全(setup/verify/README/requirements)
- v0.3 (2026-07-03) - 美颜 L2 上线(beauty.py)
- v0.4 (2026-07-03) - 去水词 L2 + 改词翻唱 L2(remove_fillers + rewrite_audio)
- **v0.5 (2026-07-03) - 文字成片 + 数字人 + 错误处理 + 日志系统 + 全 30 脚本验证通过**
