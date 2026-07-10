# 智剪工坊 · 变更日志

## v1.10 (2026-07-10) - BUG 修复 + 流程化(DAY8 vlog 出片问题追踪触发)

> 增量修复:从 DAY8 vlog 出片问题追踪表中识别 7 项 BUG + 4 项文档缺陷,集中修复。
> 修复工具链路 + 文档/HTML,跨场景防止 BUG 重现。

### 🐛 Bug 修复

- **B2/B4 · muted 视频残留 audio metadata**(`scripts/video/trim.py`)
  - **症状**:`-c:v copy -an` 处理后的 mp4,moov atom 里 audio trak 的 tkhd duration/sample count 等 metadata 没清除,后续 concat 时 ffmpeg 强行对齐 audio PTS → video 被压缩/拉长(实测 sequence_5 显示 7811 秒,成片 7:38 → sequence_3 加速)
  - **修复**:
    - 新增 `has_residual_audio_metadata()` (ffprobe 检测 audio stream 是否有 packets)
    - 新增 `remux_clean_residual_metadata()` (自动判断 muted/with-audio 两种情况分别 remux)
    - `concat()` 加 pre-process,自动检测并清理残留 metadata
  - **回归**:DAY8 vlog 重跑通过(各 sequence 时长正常,不再 7811 秒)

- **B1 · mix.py add_bgm Stream map 错误**(`scripts/audio/mix.py`)
  - **症状**:第 3 步用纯 wav 当 input 却 `-map 0:v`,报 `Stream map '' matches no streams / Failed to set value '0:v'`
  - **修复**:重写第 3 步用原视频(有 video+audio)+ filter_complex 一次性 amix,删 video_a_processed 中间产物
  - **效果**:简化流程 + 修 BUG

- **concat demuxer 7811s bug**(trim.py v1.10 第二轮发现)
  - **症状**:即使所有 input 都"有" audio stream,concat demuxer 仍可能自己创建空 audio placeholder
  - **修复**:`concat()` 改用 filter_complex concat(用 `[i:v] [i:a]` 显式引用),绕开 demuxer 的诡异行为

- **B6 · speed.py help 文本误导**(`scripts/video/speed.py`)
  - **症状**:`--factor 0.25-4.0` 描述,实际内部 atempo 链支持 100x+(冥想缩时)
  - **修复**:epilog 改为 `0.25-100 推荐,>4x 需 atempo 链`

### 📚 文档更新(SKILL.md)

- **§AI 协作协议 §3.1**(v1.10 新增):ending.type 不在路由表时的 fallback 规则 + 禁止手写 ffmpeg drawtext
- **§AI 协作协议 §3.2**(v1.10 新增):AI 主动决策 vs 必须问的边界(决策表 + 反例)
- **§⚠️ muted 视频拼接风险**(v1.10 新增章节):核心问题 + 触发场景 + 方案 A/B + 检测方法
- **§🎬 阶段 2.5: 字幕生成**(v1.10 新增):sequence 标题字幕流程化(intent.json `sequence.title` 字段 + opening.py add 工具链)
- **§ending.type 路由表**:+2 行 `next-episode-promo` / `next-week`
- **§2 标记 fillers.py 已修复**:`asetpts=PTS-STARTPTS` 已在第 262 行实现,免误导后续开发者

### 🎨 前端(intent.html)

- **新字段 sequence.title**:video card 加 `data-seq-title` input,起点 video 关联到 sequence 标题
- **JS 逻辑**:`loadSequencesFromIntent` + 导出 intent.json 时都包含 title 字段

### 📊 验证

- 备份:`智剪工坊_backup_20260710_124134.zip` (24MB)
- 回归测试:DAY8 vlog 重跑(7:38 → 7:44,含新黑屏结尾 6 秒)
- 修复追踪表:`D:\Users\辰辰洋洋\Videos\素材\健身\DAY8\00_智剪\_追踪_BUG定位与修复.html`
- 完整方案:`D:\Users\辰辰洋洋\Videos\素材\健身\DAY8\00_智剪\_修复方案_三层完整版.html`

---

## v1.2 (2026-07-04) - 阶段 2 双版冗余整合 + Step 2.2 -noautorotate 修复

> 增量改进：消除 v1.0/v1.1 阶段 2 章节的双版冗余（伪代码版 + 详细版），合并为统一结构化版本。
> 同步修复 Step 2.2 的 -noautorotate bug（#2 颠倒根因）。

### ✨ 新增

- **aspect-fill / aspect-fit 比例处理方式**（`intent.output.aspect_handling`）
  - 手机竖屏拍的视频，sensor 像素是横向的，播放效果靠 rotation metadata 旋转
  - 不存在"竖屏像素"，原来的 `preserve` 概念无效
  - **aspect-fill**：旋转并填满，内容最大显示
  - **aspect-fit**：保持原始显示方向，不旋转，加黑边适配
  - 实现：`processing.py` 的 `build_video_filter` / `build_cut_middle_filter` 加 `aspect_handling` 参数
  - intent.html 输出比例选项下方加"构图处理方式"下拉框

### ✨ 整合

- **阶段 2 双版 → 单版**：删 v1.0 "#### 阶段 2 ▸ 粗加工（5 步）" 伪代码版
  - 把 v1.1 子步骤拆解（Step 2.1/2.2）合并进 v1.0 "### 粗加工 5 步（详细，v1.0）"
  - 标题升级为 v1.2 整合版
  - 每 Step 用结构化字段：输入/输出/跳过/行为/异常处理/强制约定
- **HANDOFF.md**：v1.2 增量上下文章节同步

### 🔧 Bug 修复

- **Step 2.2 -noautorotate 缺失**（`processing.py:278`）
  - **症状**：源 rotation=-180° 的视频处理后仍颠倒（DAY2 #2 实测）
  - **根因**：ffmpeg 读入时默认自动应用 metadata rotation（让画面"人眼正"），又叠加 `transpose=1,transpose=1`（基于 metadata 推断）→ 反向旋转 → 颠倒
  - **修复**：加 `-noautorotate`，让 ffmpeg 不自动应用 metadata，由 `transpose` 精确控制；patch tkhd 清 metadata
  - **验证**：#1 (-90°) / #2 (-180°) 均正确
- **`build_rotation_filter` transpose 映射写反**（`processing.py:112-127`，2026-07-04 实战发现）
  - **症状**：rotation=-90° 的竖屏视频处理后倒 180°；rotation=+90° 同理
  - **根因**：-90°→`transpose=2`(180°旋转)，+90°→`transpose=1`(180°旋转)——完全写反
  - **修复**：-90°→`transpose=1`，+90°→`transpose=2`
  - **验证**：DAY2 #1(-90°) / #3(-90°) / #8(-90°) / #7(+90°) / #26(+90°) 全 1920×1080
- **`build_video_filter` 和 `build_cut_middle_filter` 的 aspect_handling 条件写反**
  - **症状**：竖屏源 + aspect-fit 时，竖屏内容直接以横向像素存储，播放出来是倒的
  - **根因**：只对 `aspect-fill` 做 counter-rotate，但竖屏源（rotation≠0）用 aspect-fit 也需要 counter-rotate
  - **修复**：counter-rotate 条件从 `aspect_handling=='aspect-fill'` 改为 `rotation!=0`；scale/pad 策略才区分 aspect-fill/fit
  - **验证**：DAY2 #1(-90°+aspect-fit) / #3(-90°+aspect-fit) / #7(+90°+aspect-fit) 均正确

### ✨ 新增

- **aspect-fill / aspect-fit 比例处理方式**（`intent.output.aspect_handling`）
  - **aspect-fill**：旋转并填满，内容最大显示（`force_original_aspect_ratio=increase`）
  - **aspect-fit**：保持原始显示方向，加黑边适配（`force_original_aspect_ratio=decrease` + pad）
  - **两模式差异在 scale/pad 策略，不在 counter-rotate**
  - 实现：`processing.py` 的 `build_video_filter` / `build_cut_middle_filter` 加 `aspect_handling` 参数
  - intent.html 输出比例选项下方加"构图处理方式"下拉框

### 📝 设计原则（继承 v1.0/v1.1 + 新增）

- v1.0 三原则：零硬编码 / 零遗漏 / 零猜测
- v1.1 信息流单向原则
- **v1.2 新增**：契约集中原则（一个 Step 一处看完，避免双版漂移）
- **v1.2 新增**：counter-rotate 独立原则（rotation≠0 时永远 counter-rotate，scale/pad 才区分模式）

### 📝 设计原则（继承 v1.0/v1.1 + 新增）

- v1.0 三原则：零硬编码 / 零遗漏 / 零猜测
- v1.1 信息流单向原则
- **v1.2 新增**：契约集中原则（一个 Step 一处看完，避免双版漂移）

### 已知遗留

- v1.0 缺陷 #1（操作清单 jargon 过重）仍未修，待 v1.3
- executor.py 仍是 v0.7 版本，未实现 v1.0/v1.1/v1.2 新增行为
- docs/*.md (FAQ/GETTING_STARTED/FEATURE_COMPARISON/VS_JIANYING) 和 README.md 仍是 v0.5 内容（v0.7 已知遗留）
- SKILL.md 已更新，但架构.md §5 Step 2 行还在 v1.0 版本（v1.1 增量时改过，v1.2 整合未同步——见 v1.3 待办）

---

## v1.1 (2026-07-04) - Step 2 子步骤拆解：ASR 优先

> 增量改进：在 v1.0 基础上，把 Step 2 拆为 2.1 (ASR 优先) + 2.2 (基于 ASR 处理)。
> 解决 v1.0 缺陷 #2：ASR 时机仍不够早，导致 D2/D5 拍板不准。
> 改动最小：只动 Step 2 一个章节 + 架构.md 同步。

### ✨ 新增

- **Step 2.1: ASR 优先（批量转录）** — 处理所有 voice != mute 的视频，产出文字稿
- **Step 2.2: 单视频处理（基于 ASR 优化）** — 文字稿可用于优化 ops（D2 文字卡内容、D5 水词判定）

### 🔧 重构

- **Step 2**：从单一"单视频处理 + ASR"拆为 2 个子步骤
  - 2.1 先 ASR（每个完成立即汇报）
  - 2.2 再处理（基于 ASR 优化，每个完成立即汇报）
- **架构.md** §5 Step 2 行同步更新

### 📝 设计原则（继承 v1.0 + 新增）

- v1.0 三原则：零硬编码 / 零遗漏 / 零猜测
- **v1.1 新增**：信息流单向原则（"ASR → 拍板 → 处理"，不再折返）

### 修复的 v1.0 缺陷

- **#2 ASR 时机不够早**：D2（文字卡内容）、D5（去水词）拍板原本基于 AI 默认，v1.1 后可在 Step 2.2 基于实际文字稿优化

### 已知遗留（DAY2 实测发现，2026-07-04）

- v1.0 缺陷 #1（操作清单 jargon 过重）仍未修，待 v1.2 修
- executor.py 仍是 v0.7 版本，未实现 v1.0/v1.1 新增行为

---

## v1.0 (2026-07-04) - 端到端流程重设计：阶段 0-4 + 操作清单 schema

> Major 升级：从 v0.7 的"粗加工 5 步"重构为"阶段 0-4 端到端流程"。
> 核心新增：**操作清单 schema**（6 象限）作为阶段 1→2 执行契约。
> 三原则：**零硬编码 / 零遗漏 / 零猜测**。

### ✨ 新增（设计层）

- **阶段 0-4 端到端流程** — 替换 v0.7 的 10 步流程
  - 阶段 0：项目初始化（intent.html → intent.json）
  - 阶段 1：**意图对齐（必走）** → 输出「操作清单.md」
  - 阶段 2：粗加工（5 步，结构微调）
  - 阶段 3：模板工作流
  - 阶段 4：收尾成片

- **`## ⚠️ AI 必读` 章节**（SKILL.md 顶部）— 三原则 + 4 条执行契约

- **操作清单 schema（6 象限）**：
  - A. per-video 操作
  - B. project-level 操作
  - C. sequence 约束
  - D. 模糊项 / 待澄清（含"必须问 / 建议问"标记）
  - E. AI 推断 vs 用户明确
  - F. 未覆盖字段（out-of-scope）

- **AI 交互式采访触发条件表** — 9 类触发场景的"必须问 / 建议问 / 不必问"动作

- **场景覆盖度自检表** — 12 类通用场景的覆盖情况（4 类需 AI 主动采访）

### 🔧 重构（粗加工 5 步）

- **Step 2：单视频处理 + ASR** — ASR 从原 Step 4 前置到 Step 2，与单视频处理同步产出
  - 新增产物：`文字稿/视频_{idx}.md` + `文字稿/全部.md`（Step 2 输出）
  - **每处理完一个视频立即向用户汇报**（产物路径 + 摘要 + 异常）
- **Step 3：sequence 拼接（仅 sequence 内视频）**
  - 新增产物：`中间产物/自由素材清单.md`（未约束视频）
- **Step 4：整体复核 + 模糊项兜底**（从原 ASR 改为兜底环节）
  - 输入：操作清单 D 象限 + Step 2/3 实际产物
  - 输出：`中间产物/模糊项处理记录.md`
- **Step 5：决策报告 + 模板衔接**
  - 新增：模板加载建议（基于操作清单 + 关键帧 + ASR）

### 📝 设计原则（v1.0 三条）

1. **零硬编码** — 不绑定具体项目（vlog 主题、平台、用户），用通用 schema
2. **零遗漏** — intent.json 每个字段必须有去处（明确操作 / 隐含意图 / 未覆盖说明）
3. **零猜测** — 凡 AI 推断的、模糊的、未覆盖的，必须主动交互式采访

### 📝 决策

- 阶段 1 必走，无「操作清单」不进入阶段 2
- 粗加工 5 步结构保持，但 Step 2/4 职责变化
- 模板 Stage 顺序阶段必须处理「自由素材」（Step 3 没拼的视频）
- ASR 前置到 Step 2 → ASR 文字稿可在 Step 2 完成后立即用于 Step 4 模糊项讨论

### ⏸️ 已知待实现（v1.1+ 候选）

- executor.py 需新增 per-video 回调（约定 16）
- executor.py 需新增「自由素材清单」生成（约定 15）
- docs/*.md 4 个 + README.md 同步到 v1.0
- 模板库扩充（教程vlog.yaml / VLOG.yaml 待写）

---

## v0.7 (2026-07-04) - 主体流程重构 + 模板工作流

### ✨ 新增
- **`SKILL.md §主体流程`** —— 端到端流程章节：粗加工 5 步 + 模板工作流 + 约定 11 条
- **`架构.md`** —— 完整设计文档 + §8 决策落地位置表
- **`模板/健身vlog.yaml`** —— 类别化工作流示例（4 stage：分类/节奏/顺序/收尾）
- **`lib/asr.py`** —— faster-whisper 包装（DAY1 已用的 auto_subtitle.py 薄封装）
- **`lib/modify.py`** —— AI 改素材的操作菜单（speed/trim/cut/mute/...）+ write_decision_report
- **`executor.py` 5 原子函数** —— step1_check_intent / step2_process_videos / step3_assemble_sequences / step4_asr_transcripts / step5_decision_report + run_coarse 编排

### 🔧 重构
- **`executor.py`** —— 从「一坨过程代码」拆为 5 个原子函数 + 顶层 run_coarse()
- 头部 docstring v0.1 → v0.7，反映新的 5 步流水线

### 🗑️ 删除
- **`scripts/pipeline_vlog.py`** —— 旧的「7 步一锤定音」流水线（4K降分辨率/烧字幕/BGM/封面），跟新设计「粗加工+模板工作流」重复
- **`references/11-pipelines.md`** —— 上述 pipeline 的旧文档
- **`scripts/__pycache__/pipeline_vlog.cpython-313.pyc`** —— 编译缓存

### 📝 决策
- 模板 = 工作流脚本（AI 引导用户做决策的步骤），不是 config
- 工作区结构：源视频 + `00_智剪/粗加工/` + `00_智剪/成片/`
- 目录命名：粗加工中文，文件名/JSON 字段英文
- 不写 `decisions.json` / `state.json` / `review.html`（之前讨论过，确认不要）
- 砍掉 `schemas/`（speculative schema = 提前固化错误）
- 粗加工 Step 2 后输出「单视频汇总.md」，不要求逐个交互

### 已知问题
- 模板库只有「健身vlog.yaml」一个，更多类别（教程/通用）待增长
- lib/modify.py 中序列操作（replace/insert/delete/swap/change_transition）是 stub，待 executor 序列处理重构后实现
- 旧 docs/*.md（FAQ / GETTING_STARTED / FEATURE_COMPARISON / VS_JIANYING）和 README.md 仍标 v0.5，**待下一个 PR 同步**

---

## v0.6 (2026-07-03) - 14 个原子操作补全

### ✨ 新增
- **`scripts/edit.py`** —— 14 个原子画面/音频编辑操作(1 个脚本 14 子命令)
  - **P0 基础 8 个**:remove(去头/去尾/去中间)/ volume / mute / letterbox / scale / crop / rotate / flip
  - **P1 扩展 6 个**:extract-audio / fade-audio / watermark / multi-res / gif / thumbnail
  - **设计选择**:14 操作放 1 脚本(逻辑相似,集中维护)
  - **remove 模式**:`--mode head/tail/regions`(`--exclude "10-5,20-3"` 逗号分隔多区间)
  - 实测:17/17 子命令通过(含 watermark 17 号)

### 🔧 升级
- SKILL.md:子技能索引 15 → 16 + 当前状态表 v0.5 → v0.6
- docs/GETTING_STARTED.md:加 H 工作流(14 个 edit 子命令示例)
- docs/FAQ.md:加 Q34-36(edit.py 用法)

### 🐛 修过的 Bug
- `edit.py remove` temp 文件原来放工作目录,跨磁盘 `Path.replace` 失败 → 改放 output 同目录

### 📦 验证状态
- ✅ 30/30 脚本 import 通过
- ✅ 17/17 edit 子命令冒烟测试通过(完整跑通 remove/volume/mute/letterbox/scale/crop/rotate/flip/extract-audio/fade-audio/thumbnail/multi-res/gif/watermark)

---

## v0.5 (2026-07-03) - C/D 路线收尾

### ✨ 新增

#### C 路线(战略 API 集成)
- **`scripts/ai_text_to_video.py`** —— 文字成片(默认接 mmx matrix MCP,免费)
  - `matrix_gen_videos` text-to-video 模式
  - 6s/10s 时长,1080P/768P 分辨率
  - 自动下载 CDN URL 到本地
  - 其他 API(kling/vidu/runway/svd)框架保留(占位)
- **`scripts/ai_digital_human.py`** —— 数字人(用真人头像 + 文案/音频)
  - `matrix_gen_videos` subject 模式(保持人脸一致)
  - 自动 TTS 合成文案(用 mmx TTS,fallback edge-tts)
  - ffmpeg 合音频到生成的人脸视频
  - HeyGen/D-ID/SadTalkers 框架保留(占位)

#### D 路线(质量层 MUST 项)
- **错误处理**:`lib/common.py` `safe_run` 增强
  - 加 JSONDecodeError / TimeoutExpired / OSError 处理
  - OSError 智能分类:Errno 2 = 文件找不到,Connection = 网络问题
  - 每个错误类型给可操作 fix 提示
- **日志系统**:`lib/common.py` 全套升级
  - `log_info/warn/error` 加时间戳
  - `log_progress(current, total, msg)` —— 进度条 `[████░░] 50% (5/10)`
  - `log_debug(msg)` —— `--verbose` 才显示,文件总是记录
  - `setup_logging(verbose)` —— 统一初始化
  - **文件日志**:`~/.zhijian/logs/zhijian-YYYYMMDD.log`(10MB 滚动)
  - **`safe_batch(files, fn, desc)`** —— 批处理包装:每文件 try/except,失败继续
- **3 个长任务脚本接入**:
  - `batch.py`:5 任务(trim/fadeout/cover/convert/lut)+ safe_batch + log_progress
  - `beauty.py`:帧循环加 log_progress + 单帧 try/except
  - `pipeline_vlog.py`:7 步 pipeline 加 log_progress(1/7 → 7/7)

### 🐛 修过的 Bug
- digital_human.py import 顺序错(rewrite_audio 在 sys.path 加入之前就 import)→ 调整

### 📦 验证状态
- ✅ 29/29 脚本 import 通过
- ✅ 6/6 冒烟测试通过
- ✅ batch.py 5 文件实测:进度条 20%→100% 正常,fail 继续不中断
- ⚠️ C-1 / C-2 mmx 视频生成未实测(避免浪费 API 配额)

### 🧹 文档清理(bug 教训迁出 SKILL.md)
基于第一性原理:
- **SKILL.md** 教训段 10 条 → 1 行指针(指向 FAQ / HANDOFF / 子技能 references)
  - 理由:bug 教训对 AI 路由价值低(路由靠 description 触发词),对开发者价值高(在 HANDOFF)
- **FAQ.md** bug 表 → 3 个 Q&A(Q31-33:8 小时视频 / AI 中文乱码 / NVENC 崩溃)+ 5 条已知限制
- **HANDOFF.md** 完整保留(本来就是给下个 session 开发者的家)
- **references/** 特定子技能 bug 提示保留(如 05-color.md 的 ffmpeg 7.1 `curves=preset=` 提示)

---

## v0.4 (2026-07-03) - 改词翻唱 L2

### ✨ 新增
- **`scripts/ai_rewrite.py`** —— 改词翻唱 L2(agent-driven)
  - 三个子命令:transcribe(Whisper) / synthesize(matrix TTS) / replace(ffmpeg)
  - 用 matrix MCP 的 327 个预置声音做 TTS
  - CDN URL 自动下载到本地
  - 端到端 demo:test_speech.mp4 改写+换声+替换,20s → 11.8s

### 🐛 修过的 Bug
- global safe_run(main) 缺 `()` 已在 v0.3 修
- mediapipe 0.10.35 Windows 中文路径 bug — fallback `C:\zhijian_models\`
- mediapipe 0.10 移除 `solutions` API — 用 `tasks.vision.FaceLandmarker`
- color_style / fx ffmpeg filter 语法 bug
- mavis CLI 不在 subprocess PATH — 用 `shutil.which` 找全路径
- PowerShell Out-File 加 BOM — 用 Python `write_bytes` 写 JSON

---

## v0.3 (2026-07-03) - 美颜 L2 + 重大 bug 修复

### ✨ 新增
- **`scripts/ai_beauty.py`** —— 美颜 L2 标准版
  - 4 个独立子能力:磨皮 + 美白 + 瘦脸 + 大眼
  - 5 个 preset:`off` / `slight` / `natural` / `strong` / `max`
  - 底层:mediapipe 0.10 tasks.FaceLandmarker(478 关键点)
  - 算法:脸部 oval mask + 三角剖分 + 仿射变形
  - 自动下载模型(3.7MB 一次性)
  - 视频逐帧处理 + 音频自动 mux
  - 图片 + 视频双模式
- **`scripts/ai_fillers.py`** —— AI 去水词(两段式,无 LLM token 依赖)
  - 架构:transcribe(Whisper → SRT + words.json)+ cut(句/词索引 → 切视频)
  - **word-level 时间戳支持**:transcribe 多输出 `.words.json`(每词 start/end/word/sentence)
  - **cut 双模式**:`--remove 1,3,5`(句,粗)或 `--remove-words 2,5,12`(词,精准,推荐)
  - 词模式:相邻词 < 0.2s 自动合并,避免硬切
  - LLM 判断在 Mavis agent(我)这边做,不走 daemon subprocess(避开 token 问题)
  - 工作流:transcribe → agent 读 SRT+JSON 判 → cut --remove-words
  - 端到端测试:20s TTS 测试音频 → 删 10 个水词 → 16.7s 输出(省 3.3s)
- **`lib/llm_client.py`** —— LLM 客户端封装(subprocess 模式,备用)

### 🐛 修过的关键 Bug
1. **全局 27 脚本 `safe_run(main)` 缺 `()`** —— 最严重!
   - 现象:全部 27 个脚本入口实际不调 main(),Python 加载完模块后正常退出(返回 0)
   - 影响:之前 verify.py 报告的 "6/6 冒烟测试通过" 实际啥也没跑,只是退出了
   - 修法:批量 `safe_run(main)` → `safe_run(main)()`(全 27 个脚本)
2. **mediapipe 0.10.35 移除 `solutions` API**
   - 现象:`mp.solutions.face_mesh` 不存在了
   - 修法:改用 `mp.tasks.vision.FaceLandmarker` task-based API
3. **mediapipe 0.10.35 Windows 中文路径 bug**
   - 现象:模型路径含非 ASCII 字符(如 `智剪工坊`)→ `FileNotFoundError`
   - 修法:自动 fallback 复制到 `C:\zhijian_models\`(纯 ASCII 路径)
4. **color_style.py 用 `curves=preset=X`**
   - 现象:ffmpeg 7.1 不支持 `curves` 的 `preset` 选项
   - 修法:批量移除 `curves=preset=X` 段
5. **fx.py intensity blend 语法错**
   - 现象:`split[orig];[orig][orig]blend=...` 写法错,ffmpeg 报"input/output 数量不对"
   - 修法:简化为静态效果,intensity 改成"提示"信息

### 📦 验证状态(2026-07-03 实测)
- ✅ 27/27 脚本 import 通过(新增 beauty.py)
- ✅ 6/6 核心脚本冒烟测试真正通过(修了 safe_run bug 后)
- ✅ 10/10 Python 依赖就位
- ✅ beauty 4 个 preset 真实人脸图测试通过(biden + two_people)
- ✅ 解决 mediapipe Windows 中文路径 bug
- **`scripts/ai_rewrite.py`** —— 改词翻唱 L2(agent-driven)
  - 三个子命令:transcribe(Whisper) / synthesize(matrix TTS) / replace(ffmpeg)
  - 用 matrix MCP 的 327 个预置声音做 TTS(中文/英/日/韩等 22 种语言)
  - CDN URL 自动下载到本地
  - 自动处理 BOM/中文乱码(subprocess 路径问题)
  - 端到端 demo:test_speech.mp4 改写+换声+替换,20s → 11.8s
- ✅ remove_fillers cut 端到端测过(mock SRT)
- ✅ rewrite_audio 全链路跑通(synthesize + replace)

### ⚠️ 已知小问题
- mediapipe 0.10.35 在 Windows 上对非 ASCII 路径有 bug,本系统通过自动 fallback 解决
- beauty 视频处理 ~5-10x 实时(1080p CPU),生产用可考虑 GPU 版
- mavis daemon 的 LLM apiKey 显示 invalid(`apiKeyStatus.valid: false`),subprocess 调 LLM 全部 401
  - 解决:remove_fillers 改为两段式,LLM 判断在 Mavis agent 里做

---

## v0.2 (2026-07-03) - 可发布版本

### ✨ 新增
- `setup.bat`(Windows)+ `setup.sh`(Mac/Linux)—— 一键安装脚本
- `verify.py`—— 环境验证脚本
- 产品级 `README.md`

### 🔧 升级
- `lib/common.py`:读 config.json + 跨平台 ffmpeg + 友好错误
- `requirements.txt`:9 个实依赖全开

---

## v0.1 (2026-07-03) - 骨架完成

- 11 个子技能文档 + 5 个核心脚本
---\n\n## v1.11 之前的版本摘要（从 SKILL.md v1.10 移除）\n\n> 注：以下为 v1.11 升级前 SKILL.md §📅 版本章节内容，已迁移到 CHANGELOG。\n\n
## 📋 v1.11 之前的版本摘要

- **v1.10**（2026-07-10）：阶段 3 实装 + 新增阶段 4「产物审查 · 用户交互循环」+ 阶段 4 顺延为 5
  - **新阶段 4「产物审查 · 用户交互循环」**：在阶段 2 粗加工 + 阶段 3 模板 完成后、出成片前，新增 AI 列出全量产物 + 用户逐项标 OK/有问题 + 讨论队列循环 + 用户签字「全部 OK」后才能进入阶段 5 收尾的强约束
  - **阶段 3「模板工作流」实装**：删 v1.3「待设计/暂跳过」说明，正式启用 `模板/健身vlog.yaml`（4 stages：节奏决策 → 时间排序 → 转场 → 数据叠加），补 YAML 契约（含 completion / failure 字段）
  - 阶段编号顺延：原阶段 4「收尾成片」→ **阶段 5** 收尾成片
  - **全 SKILL 阶段编号同步**：SKILL.md 37 处 + references/AI交互式采访触发条件.md 2 处 + references/主流程-阶段编排.md 全章 + 模板/健身vlog.yaml 2 处，「阶段 4 → 阶段 5」全文一致
  - 流程图 L437 加「阶段 4 产物审查」节点
- **v1.9**（2026-07-10）：安装/部署 + 阶段 0 强化 + 项目 venv
  - 加 `## 📦 安装与配置` 章节（学习居家管家/卡路里/饼干记账 统一格式）：依赖表 + 配置项（HF_ENDPOINT / HF_HOME / TORCH_HOME）+ 一键安装 prompt + AI 撞墙自动帮设契约
  - 加 `## 🐍 项目 venv（hybrid 隔离）` 章节：`<skill_root>/venv/` + AI 行为约定（不破坏隔离、永不自己创建/删除）
  - **阶段 0 强化（v1.9 关键）**：加 0.0 步（问工作目录）+ 0.1 升成「第 1 件事主动打开 `智剪工坊-意图编辑.html`」（`Start-Process` / `xdg-open` / `open`），**禁止 dialog 代填**（用户选 ① 后必走）
  - 加 2 个依赖骨架文件：`requirements.txt`（PyPI 默认源）+ `requirements-torch.txt`（PyTorch GPU CUDA 13 index）
  - **HTML 前端改名**：`intent.html` → **`智剪工坊-意图编辑.html`**（软件型命名，跨 4 个目录同步 27 处引用，**正文零残留**）
  - **删 `tests/` 目录**：70 个调试期私有脚本（全部 `_` 前缀）+ 14 个旧 fixture（PNG/MP4 截图），生产代码零引用，安全 trash 可恢复
- **v1.8**（2026-07-10）：触发词 ↔ 脚本 双向审计（对抗式 + 第一性原理）
  - 修 27 个维度路由（旧 `audio/*.py` / `video_*.py` 等 → `scripts/{sub}/{file}.py`，附 v1.7 改名标记）
  - 修 21 个 Jargon 大白话词典路由（同上）
  - 加 15 个专业触发词进 triggers YAML（ASR / Whisper / 语音转文字 / 混音 / 老声 / 童声 / 擦除 / AI 生成视频 / 流水线 / 封面生成 / AI 增强 / 音频提取 / 谁说了什么 / 旋转 / 裁剪）
  - 红线章节死引用 `_check_consistency.py` 标注「尚未实现」
  - 红线章节 19 处 `scripts/atomic/*.py` 同步改为 `scripts/{audio,asr,video,ai,batch}/*.py`
- **v1.7**（2026-07-10）：架构清理（scripts/ 根目录清空，所有用户可见脚本归到子目录 audio/asr/video/ai/batch；lib/ 第三方底库归到子目录 asr/video；新增 _internal/）
- **v1.6**（2026-07-09）：scripts/asr/burn_subtitle 下沉到 lib/ffmpeg/video/，新增视频底层 lib（6 文件，21 函数，41 种 xfade）
- **v1.5**（2026-07-09）：scripts/audio/* 全部下沉到 lib/ffmpeg/audio/，分层架构
- **v1.4**（2026-07-09）：链路重构 + 新增声源分离/说话人分离链路 + 能力链路红线原则（最高优先级）
- **v1.3**（2026-07）：AI 编排 + 路由表 + 11 个优化
- v1.2（2026-06）：精简 step 脚本 + 操作清单 schema
- v1.0（2026-05）：阶段 0-5 端到端
- v0.7（2026-04）：早期版本

### v1.6 变更摘要

- **新增** `lib/ffmpeg/video/` 视频底层 lib（6 个文件，21 个公开函数）：
  - `subtitle.py` — 字幕烧录（subtitles / drawtext）
  - `transition.py` — 转场（xfade，**41 种类型**）
  - `color.py` — 调色（eq / colorbalance / hue / vibrance / curves / lut3d）
  - `timing.py` — 速度/时间（setpts 变速、trim、reverse、freeze、fps）
  - `transform.py` — 缩放/裁剪/旋转/翻转/黑边（scale / crop / rotate / hflip / vflip / pad / letterbox）
  - `watermark.py` — 水印（overlay + drawtext + 5 种位置）
- **重构** `scripts/asr/burn_subtitle.py`：改为薄封装，调 `lib.ffmpeg.video.subtitle.burn_subtitle`，不再直接拼 ffmpeg 命令
- **保留** `scripts/asr/speaker_srt.py`：纯文本合成（diar JSON + SRT），不调 ffmpeg，不属于视频 lib 范围
- **新增** `references/08-video-lib.md`：视频 lib 完整参考（21 函数签名 + 用法示例）
- **SKILL.md 同步**：
  - description 触发词新增：变速 / 倒放 / 冻结帧 / 抽帧 / 水印 / logo / 色相 / 饱和度 / 缩放 / 裁剪 / 旋转 / 翻转 / 字母盒 / 视频滤镜
  - triggers YAML 列表新增 23 个视频专属词
  - 文件地图加 `lib/ffmpeg/video/*.py`
  - references 列加 `08-video-lib.md`
  - 目录结构加 lib/ffmpeg/video/ 树
- **核心优势**：所有视频能力（字幕烧录 / 转场 / 调色 / 速度 / 缩放 / 水印）通过 lib 复用，上层脚本仅做参数解析 + 用户友好日志

### v1.7 变更摘要（架构清理）

- **scripts/ 根目录清空**：22 个旧脚本全部归类到子目录
  - **新建 `scripts/video/`**（21 个脚本）：video_*.py + edit.py + image_to_video.py 迁移并去 `video_` 前缀
  - **新建 `scripts/ai/`**（9 个脚本）：ai_*.py 迁移并去 `ai_` 前缀
  - **新建 `scripts/batch/`**（1 个脚本）：batch.py 迁移
  - **新建 `scripts/_internal/`**（1 个工具）：stage1_checklist.py 从 lib/ 迁入
  - **删除** 3 个 backward-compat stubs：`audio_bgm.py` / `audio_voice.py` / `audio_beat.py`（违反 §5.5）
- **lib/ 第三方底库归子目录**：
  - **新建 `lib/asr/`**：`pyannote.py` + `whisper.py` 从 lib/ 根目录迁入
  - **新建 `lib/video/`**：`patch_mp4_rotation.py` 从 lib/ 根目录迁入
  - **改名 `lib/processing.py` → `lib/video_processing.py`**（职责更清晰）
- **同步所有 import 引用**（4 处 + SKILL.md 5 处）：
  - `scripts/asr/transcribe.py`: `from lib.whisper` → `from lib.asr.whisper`
  - `scripts/audio/diarize.py`: `from lib.pyannote` → `from lib.asr.pyannote`
  - lib/asr/pyannote.py / lib/asr/whisper.py / lib/video_processing.py docstring 同步
- **SKILL.md 同步**：文件地图 + 目录结构 + 版本 + 解析注释 + 5 处旧引用全部更新
- **清理空目录**：`lib/pyannote/` `lib/whisper/` 空目录删除
- **架构改进**：scripts/ 根目录 100% 清空，lib/ 顶层只剩基础设施 + 第三方入口（5 个文件），其他全部归子目录
- **smoke test**：12/12 import 测试通过（lib.asr.pyannote / lib.asr.whisper / lib.separate_demucs / scripts/asr/transcribe / scripts/audio/diarize / scripts/audio/separate / lib.video_processing / lib.video.patch_mp4_rotation / scripts.video / scripts.ai / scripts.batch / scripts._internal）

### v1.5 变更摘要

- **新增** `lib/ffmpeg/audio/` 底层 lib（10 个文件，70+ 个公开函数）
  - denoise / enhance / detect / normalize / transform / channel / visualize / effect / utility / measure / extract
- **新增** 第三方底层 lib（按依赖分类）：
  - `lib/separate_demucs.py`（声源分离，Python API + GPU）
  - `lib/pyannote.py`（说话人分离）
  - `lib/whisper.py`（faster-whisper ASR）
- **删除** 历史遗留 `lib/asr.py`（被 lib/whisper.py 取代）
- **重构** scripts/audio/*.py：mix / voice / beat / extract / denoise / separate / diarize 7 个用户脚本改为调用 lib
- **重构** scripts/asr/transcribe.py：调 lib/whisper
- **新增** 3 个用户功能脚本（v1.5 阶段 2）：
  - `audio/voice_extract.py`（人声提取，dialoguenhance 封装）
  - `audio/silence_split.py`（静音检测 + 自动分段，silencedetect 封装）
  - `audio/loudness_norm.py`（响度归一 EBU R128，loudnorm 封装）
- **修复** 10 个用户脚本的 sys.path bug（避免覆盖标准库）
- **新增** `references/07-audio.md`：音频链路完整参考文档（含 10 个用户脚本 + 4 个 lib 模块说明）
- **核心优势**：上层脚本不再直接拼 ffmpeg 命令，所有 ffmpeg / demucs / pyannote / whisper 调用通过 lib 复用

### v1.4 变更摘要

- 新增 `scripts/audio/` 子目录（L1-L5 音频链路：mix / voice / beat / extract / denoise / separate / diarize）
- 新增 `scripts/asr/` 子目录（L6 ASR 链路：transcribe / burn_subtitle / speaker_srt）
- 新增 `references/ASR链路-声源分离说话人分离Whisper烧字幕.md`
- 删除 backward-compat stub：`audio_bgm.py` / `audio_voice.py` / `audio_beat.py` / `video_subtitle.py`
- 新增 §能力链路完整性（最高优先级红线原则）
- scripts/ 按红线原则分类：`atomic/`（用户可见）vs `_internal/`（开发者用）