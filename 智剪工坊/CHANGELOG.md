# 智剪工坊 · 变更日志

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
- **`scripts/text_to_video.py`** —— 文字成片(默认接 mmx matrix MCP,免费)
  - `matrix_gen_videos` text-to-video 模式
  - 6s/10s 时长,1080P/768P 分辨率
  - 自动下载 CDN URL 到本地
  - 其他 API(kling/vidu/runway/svd)框架保留(占位)
- **`scripts/digital_human.py`** —— 数字人(用真人头像 + 文案/音频)
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
- **`scripts/rewrite_audio.py`** —— 改词翻唱 L2(agent-driven)
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
- **`scripts/beauty.py`** —— 美颜 L2 标准版
  - 4 个独立子能力:磨皮 + 美白 + 瘦脸 + 大眼
  - 5 个 preset:`off` / `slight` / `natural` / `strong` / `max`
  - 底层:mediapipe 0.10 tasks.FaceLandmarker(478 关键点)
  - 算法:脸部 oval mask + 三角剖分 + 仿射变形
  - 自动下载模型(3.7MB 一次性)
  - 视频逐帧处理 + 音频自动 mux
  - 图片 + 视频双模式
- **`scripts/remove_fillers.py`** —— AI 去水词(两段式,无 LLM token 依赖)
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
- **`scripts/rewrite_audio.py`** —— 改词翻唱 L2(agent-driven)
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
