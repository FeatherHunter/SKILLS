# 智剪工坊 · Session Handoff 文档

> **目的:** 用户(帅猎羽)要清空当前 session,这是给下一个 session AI 的完整上下文。
> **写于:** 2026-07-03 16:00 (Asia/Shanghai)（v1.0 增量更新于 2026-07-04 15:20）
> **当前版本:** v1.0(30 脚本,29/29 验证通过,5 个 AI 增强全实现,**端到端流程已重设计**)
> **重要:** 必须读完整个文档再开始动手,尤其是"未完成需求"和"关键 bug"两节。

---

## 🔴 v1.1 增量上下文（2026-07-04 必读）

**v1.1 是 Step 2 子步骤拆解，ASR 优先**。这是对 v1.0 流程的细化改进，**不是 major 升级**。

### v1.0 → v1.1 核心变化
1. **Step 2 拆为 2.1 + 2.2**：
   - Step 2.1：ASR 优先（批量转录所有需要 ASR 的视频）
   - Step 2.2：单视频处理（基于 ASR 文字稿优化 ops）
2. **信息流单向原则**：ASR → 拍板 → 处理（不再折返）
3. **解决 v1.0 缺陷 #2**：D2（文字卡内容）、D5（去水词）拍板不准——v1.1 后 Step 2.2 可基于实际文字稿优化

### 接手时第一件事
1. 读 SKILL.md §Step 2 v1.1 子步骤（比 v1.0 多 2.1/2.2 拆解）
2. 其余流程与 v1.0 一致

### 当前已知遗留
- v1.0 缺陷 #1（操作清单 jargon 过重）仍未修，待 v1.2 修

---

## 🔴 v1.0 增量上下文（2026-07-04 必读）

**v1.0 是端到端流程重设计，major 升级，不是普通版本号变化**。接手 session 前必须先读：

### 关键文件
- `SKILL.md` §⚠️ AI 必读（v1.0 强制，AI 加载 skill 第一件事）
- `SKILL.md` §主体流程 → §完整流程（v1.0 阶段 0-4）
- `SKILL.md` §操作清单 schema（6 象限，阶段 1 → 2 执行契约）
- `SKILL.md` §AI 交互式采访触发条件（9 类规则）
- `SKILL.md` §场景覆盖度自检（12 类场景）
- `架构.md` —— 完整设计 + §8 决策落地位置表
- `CHANGELOG.md` v1.0 段 —— 这次到底改了什么

### v1.0 核心变化（v0.7 → v1.0）
1. **流程重设计**：粗加工 5 步 → **阶段 0-4 端到端**（项目初始化 / 意图对齐 / 粗加工 / 模板 / 收尾）
2. **新增阶段 1（必走）**：意图对齐 → 输出「操作清单.md」（6 象限）作为阶段 2 执行契约
3. **ASR 前置**：原 Step 4 ASR → 合并到 Step 2（单视频处理 + ASR 同步产出）
4. **Step 4 改为兜底环节**：原 Step 4 ASR → 新 Step 4 模糊项兜底（操作清单 D 象限）
5. **新增产物**：`中间产物/操作清单.md` + `中间产物/自由素材清单.md` + `中间产物/模糊项处理记录.md`
6. **AI 必读**：SKILL.md 顶部加 `## ⚠️ AI 必读`，三原则 + 4 条执行契约

### 三原则（v1.0 强制）
- **零硬编码** — 不绑定具体项目，用通用 schema
- **零遗漏** — intent.json 每个字段必须有去处
- **零猜测** — 凡 AI 推断的、模糊的、未覆盖的，必须主动交互式采访

### 接手时第一件事
1. 读 SKILL.md 顶部 `## ⚠️ AI 必读` —— 知道三原则 + 4 条执行契约
2. 读 SKILL.md §完整流程 —— 知道阶段 0-4 端到端怎么跑
3. 读 SKILL.md §操作清单 schema —— 知道阶段 1 输出什么契约
4. 读 SKILL.md §采访触发条件 + 场景覆盖度 —— 知道何时该主动问用户
5. 读 架构.md §8 —— 知道每个决策落地在哪个文件
6. **不要**去找「阶段 1 不输出操作清单」的实现（v0.7 旧流程已废弃）

### v1.0 已知遗留
- `docs/*.md` 4 个文件（FAQ/GETTING_STARTED/FEATURE_COMPARISON/VS_JIANYING）仍标 v0.5/2026 v0.5
- `README.md` 仍标 v0.5 内容
- `lib/modify.py` 序列操作（replace/insert/delete/swap/change_transition）是 stub
- 模板库只有「健身vlog.yaml」一个
- executor.py 仍是 v0.7 版本（5 个原子函数 + run_coarse），**未实现 v1.0 新增行为**：
  - 阶段 1 操作清单生成（待实现）
  - Step 2 per-video 回调（约定 16）
  - 自由素材清单生成（约定 15）

### v1.0 设计缺陷（DAY2 实测发现，2026-07-04 15:37）
- **操作清单 jargon 过重**：DAY2 阶段 1 用户回复"ops 是什么意思"——说明 SKILL.md 操作清单 schema + 采访弹窗大量用 jargon（ops / pin-range / cut-middle / sequence / per-video 等），首次出现没用人话解释。
- **影响**：用户在不看 jargon 解释的情况下，可能猜答案（违反 v1.0 「零猜测」原则的"友好"精神）
- **v1.1 修复方向**：
  - SKILL.md 操作清单 schema 章节加 jargon-glossary（首次出现 jargon 时给大白话）
  - 采访弹窗里所有 jargon 字段（"D6 无 ops"）改写为"视频 #8 #13 intent 里你啥都没写"
  - 考虑提供 v1.1 的 intent.html 表单字段也加 tooltip 说明
- **临时缓解**：DAY2 阶段 1 已切换为人话版对话。操作清单 v2 待补充"jargon 解释附录"。

### v1.0 设计缺陷 #2：ASR 时机仍不够早（DAY2 实测发现，2026-07-04 15:43）
- **问题**：v1.0 把 ASR 前置到 Stage 2 Step 2。但用户在 D 象限讨论时反问"ASR 不是应该提前吗？不然后面处理需要用文字稿帮助处理岂不是不好？"
- **核心洞察**：Stage 1 意图对齐阶段 AI 应该**已有 ASR 文字稿**，才能让模糊项 D2（文字卡内容）、D5（去水词判定）拍板更准。当前 v1.0 设计是"先拍板 → 处理 → 出文字稿 → 才发现拍板不准"的折返。
- **v1.1 修复方向**：
  - 阶段 0 加子步 0.5：批量 ASR（仅对 voice != mute 的视频）
  - 阶段 1 操作清单 schema 加新依赖："基于 ASR 文字稿"
  - D 象限 D2 / D5 改写为"AI 看文字稿后建议 + 用户确认"
  - 流程信息流改为单向："ASR → 拍板 → 处理"（不再折返）
- **DAY2 影响**：Stage 1 已走完，D2/D5 拍板基于 AI 默认（D2=AI 写卡片内容、D5=默认阈值），可接受但非最优。
- **临时缓解**：DAY2 可在 Stage 2 Step 2 之后补 ASR，再用文字稿人工/AI 优化 D2/D5 的处理。
- 旧 HANDOFF.md 第 1 节「当前状态」还是 v0.5/v0.6 的内容（v1.0 概览在 SKILL.md 文件地图节）

---

## 0. 项目起源(前因)

### 0.1 用户身份

- **真名:** 帅猎羽
- **昵称:** 帅烈宇(Whisper 误识别,实际是"帅猎羽")
- **Mavis 昵称:** 用户给 Mavis 起的小名叫"小帅"
- **核心项目:** B 站减脂 vlog 系列(4 个月挑战,Day 1 已发,目标 184 斤 → 139.9 斤)
- **Day 1 起始体重:** 91.95kg(183.9 斤)
- **金句:** "你能克制 3650 天吗?" / "想放弃的时候,依然坚持"

### 0.2 沟通偏好(必读)

- **老朋友式温情** —— 不要激情喊话,不要鸡汤,真实陪伴
- **第一性原理** —— 任何决策都要有"为什么",不要拍脑袋
- **真实感 > 漂亮** —— 不追求花哨,追求能跑
- **保留原稿原话** —— 用户口播用 Whisper 原始转录,错字修正
- **互动式采访模式** —— 重要决策问用户,不替他决定
- **长规划对话主动归档** —— 这次的需求就属于这个
- **minimax agent 询问选项题时用选择框(ask_user 工具)**,带详细文字解释
- **飞书消息 < 2000 字** —— 长消息会被折叠,先写文件 + `<media />`

### 0.3 智剪工坊的起源

- 起因:用户 Day 1 vlog 一条龙(剪切→转录→关键帧→AI 分析→拼装→烧字幕→BGM→封面)成功后,问"代码能不能做剪映那些特效"
- 决策:把"Day 1 一条龙"封装成 Mavis skill 叫"智剪工坊"
- 定位:对标剪映(图形化)+ 扩展(AI 能力)+ 差异化(批量、自动化)

---

## 1. 当前状态(2026-07-03 18:25,v0.6 完成)

### 1.1 已完成

| 维度 | 进度 | 备注 |
|---|---|---|
| 架构设计 | ✅ 100% | 15 子技能 + 1 大流程 |
| SKILL.md | ✅ 100% | YAML frontmatter, 14 子技能索引 + 触发词 |
| References | ✅ 100% | 15 个 .md(11 旧 + 4 新增 12-15),全 prepend v0.5 状态头 |
| 代码框架 | ✅ 100% | 30 个 .py 脚本(29 真实 + pipeline_vlog) |
| 公共库 | ✅ 100% | lib/common.py(safe_run + log_progress + safe_batch + 文件日志) |
| 产品 README | ✅ 100% | 3 分钟快速开始 + 30 脚本速查 |
| 安装脚本 | ✅ 100% | setup.bat(Windows)+ setup.sh(Mac/Linux) |
| 验证脚本 | ✅ 100% | verify.py(5 秒快检 29/29 + 6 冒烟测试) |
| 文档 | ✅ 100% | README + 4 docs/(GETTING_STARTED/FAQ/FEATURE_COMPARISON/VS_JIANYING) |
| 依赖 | ✅ 100% | requirements.txt 9 个实依赖 |
| 验证(实测) | ✅ 100% | 29/29 import + 6/6 冒烟 + batch.py 5 文件进度条 |
| **可发布** | ✅ 100% | A 路线完成,任何人 5 分钟能装上用 |
| **美颜 L2** | ✅ 100% | beauty.py(磨皮+美白+瘦脸+大眼)5 预设,真实人脸测试 |
| **去水词 L2** | ✅ 100% | remove_fillers.py(word-level 时间戳)20s→16.7s demo |
| **改词翻唱 L2** | ✅ 100% | rewrite_audio.py(Whisper+agent+matrix TTS 327 声音)20s→11.8s demo |
| **文字成片** | ✅ 100% | text_to_video.py(接 mmx,免 API key),代码完成未实测 |
| **数字人** | ✅ 100% | digital_human.py(接 mmx subject + TTS),代码完成未实测 |
| **错误处理** | ✅ 100% | safe_run 增强 5 种错误类型(JSON/Timeout/OSError/FileNotFound/Subprocess) |
| **日志系统** | ✅ 100% | log_progress + 文件日志 + safe_batch,3 脚本接入 |
| 跨平台 | ⚠️ 50% | setup.sh 写好但只测 Windows |
| 文档清理 | ✅ 100% | bug 教训从 SKILL.md 迁出,1 行指针;FAQ.md 3 Q&A + 5 限制;HANDOFF.md 完整保留 |
| **edit 14 原子操作** | ✅ 100% | **scripts/edit.py 上线,17/17 测过**;P0 8 + P1 6 补全剪映基础操作 |
| 单元测试 | ❌ 0% | 推迟(用户确认) |
| CI/打包 | ❌ 0% | 推迟(用户确认) |
| AI 视频实测 | ❌ 0% | mmx 配额 3/天,等真 vlog 时测 |

### 1.2 5 个 AI 增强(L2 路线)

| # | 子技能 | 脚本 | 状态 | 实测数据 |
|---|---|---|---|---|
| 12 | **美颜** | `scripts/beauty.py` | ✅ | 真人脸测试通过 |
| 13 | **改词翻唱** | `scripts/rewrite_audio.py` | ✅ | 20s → 11.8s,省 41% 时长 |
| 14 | **文字成片** | `scripts/text_to_video.py` | ⚠️ 代码 ✅ 实测 ❌ | mmx 配额限制 |
| 15 | **数字人** | `scripts/digital_human.py` | ⚠️ 代码 ✅ 实测 ❌ | mmx 配额限制 |
| 09-7 | **去水词** | `scripts/remove_fillers.py` | ✅ | 20s → 16.7s,切 10 个水词 |

**核心创新:** LLM 判断放在 Mavis agent(我)这边,**不走 daemon subprocess,避开 token 失效**。
**word-level 时间戳:** faster-whisper `word_timestamps=True`,精准切单字水词。

### 1.3 v0.3 → v0.5 重大 bug 修复

**Bug 6(全局 `safe_run(main)` 缺 `()`)**
- 现象:27 个脚本入口 `safe_run(main)` 只创建 wrapper 没调 main(),静默退出
- 修法:批量 `safe_run(main)` → `safe_run(main)()`
- 影响:之前所有"冒烟测试通过"都是空跑

**Bug 7(mediapipe 0.10.35 Windows 中文路径)**
- 现象:模型路径含中文 → `FileNotFoundError`
- 修法:lib/common.py 自动 fallback `C:\zhijian_models\`
- 应用:beauty.py 的模型管理

**Bug 8(mediapipe 0.10 移除 solutions API)**
- 现象:`mp.solutions.face_mesh` 不存在
- 修法:改用 `mp.tasks.vision.FaceLandmarker`

**Bug 9(ffmpeg 7.1 不支持 `curves=preset=X`)**
- 现象:ffmpeg 7.1 报错 "Invalid argument"
- 修法:color_style 改用 `colorbalance` + `eq` filter

**Bug 10(fx.py intensity blend 语法错)**
- 现象:`split[orig];[orig][orig]blend=...` 写错
- 修法:简化为静态效果,intensity 改提示信息

**Bug 11(mavis daemon LLM apiKey invalid 401)**
- 现象:走 daemon subprocess 调 LLM 报 401
- 修法:agent-driven 模式,LLM 判断放在 Mavis agent 里

**Bug 12(mavis 不在 subprocess PATH)**
- 修法:`shutil.which('mavis') or <full path>` 兜底

**Bug 13(PowerShell Out-File 加 BOM)**
- 修法:用 Python `write_bytes(json.dumps(...).encode('utf-8'))` 写 JSON

---

## 2. 关键 Bug 教训(必看,不要重蹈覆辙)

### Bug 1:NVENC 崩溃

**现象:** `h264_nvenc` 报 `Access Violation 0xC0000005` 随机崩溃
**解决:** 全部用 `libx264 -preset medium -crf 20`(CPU 编码,稳)
**代码位置:** `lib/common.py` 的 `DEFAULT_ENCODE_ARGS` 已固定用 libx264

### Bug 2:8 小时视频

**现象:** 段 10 是 23.65fps,其他段是 60fps,concat 后时长变 8 小时
**解决:** 剪切时强制 `fps=30` filter,所有片段统一
**代码位置:** `lib/common.py` 的 `UNIFIED_VIDEO_FILTER` 含 `fps=30`

### Bug 3:AI 生图中文乱码

**现象:** matrix 生图对中文/数字支持差(90% 渲染错)
**解决:** 拆成两步 —— 先生成视觉(无文字),后用 PIL 叠中文
**代码位置:** `scripts/cover_ai.py` 已用两步法

### Bug 4:reframe.py 的 f-string 冲突

**现象:** `f"crop={new_w}:{new_h}:({iw-{new_w})/2"` 中 f-string 把 `iw` 当 Python 变量
**解决:** 改成 `(iw-{new_w})/2`(去掉外层 `{}` 让 ffmpeg 解析)
**已修**

### Bug 5:PowerShell 调 Python 行为怪

**现象:** `python scripts\xxx.py --help` 经常没输出
**解决:** 用 `python -c "import sys; sys.path.insert(0, 'lib'); sys.path.insert(0, 'scripts'); ..."` 跨平台方式

---

## 3. 未完成需求(下个 session 关注)

### 3.1 v0.6 真实 vlog 实测 ⭐⭐⭐⭐⭐

**最重要**。5 个 AI 增强 + 流水线在真实 vlog 跑一次:
- 美颜 / 去水词 / 改词 / 文字成片 / 数字人 各跑一次真实 vlog
- 流水线跑完整 Day 2 vlog
- 修实测中暴露的 bug

**mmx 配额限制:** 视频生成每天 3 次,各测试最多 1 个。

### 3.2 P2 战略功能(部分待补)

| 缺口 | 状态 |
|---|---|
| 声音克隆(用自己的声音) | ❌ matrix MCP 不支持,需自训 |
| 数字人嘴型精准对齐 | ⚠️ mmx subject 模式只"保持人脸动",待 L3(SadTalkers/Wav2Lip) |
| 视频翻译(Whisper + 翻译 + TTS) | ⚠️ 占位,完整版用 rewrite_audio 拼装 |
| AI 一键成片(自动剪辑决策) | ❌ 需 ML 模型 |
| AI 转场 | ❌ 待规划 |

### 3.3 "可发布" Checklist(已 ✅)

- ✅ 安装脚本(setup.bat + setup.sh)
- ✅ 验证脚本(verify.py)
- ✅ 友好的错误提示(safe_run 增强)
- ✅ 产品级 README(3 分钟快速开始)

---

## 4. 工作流参考(Day 1 实战验证过的)

### 4.1 7 步流水线

```
Step 1: 4K → 1080p 降分辨率(若有)
Step 2: Whisper GPU 转录所有段(带时间戳)
Step 3: 抽关键帧(每 15s 一帧)
Step 4: AI 分析生成剪辑建议(SRT + 帧 → markdown)
Step 5: 用户勾选保留秒数
Step 6: ffmpeg 拼接 + 烧字幕 + BGM 混合
Step 7: AI 生图封面 + 中文叠字
```

### 4.2 视频输出规格

```
竖屏 1080x1920 · 30fps · libx264 · aac · crf=20 · bitrate=128k
容器 MP4 · faststart(网络优化)
```

### 4.3 关键命令模板

```python
# 统一滤镜(竖屏 + 30fps + 黑色边框)
"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30"

# 烧字幕
"subtitles='sub.srt':force_style='FontName=Microsoft YaHei,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=30'"

# BGM 循环混音
"[0:a]volume=1.0[a0];[1:a]volume=0.18,aloop=loop=-1:size=2e9[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[a]"
```

### 4.4 5 个 AI 增强的 agent-driven 流程

**美颜:**
```bash
python scripts/beauty.py --input v.mp4 --output v_beauty.mp4 --preset natural
```

**去水词(2 段式):**
```bash
# Step 1: 转录(SRT + words.json)
python scripts/remove_fillers.py transcribe --input vlog.mp4 --srt vlog.srt
# Step 2: (Mavis 读 words.json,标水词)
# Step 3: 切掉水词
python scripts/remove_fillers.py cut --input vlog.mp4 --srt vlog.srt --output clean.mp4 --remove-words "1,3,11"
```

**改词翻唱(2 段式):**
```bash
# Step 1: transcribe
python scripts/rewrite_audio.py transcribe --input v.mp4 --srt v.srt
# Step 2: (Mavis 改写文案,选 voice_id)
# Step 3: synthesize
python scripts/rewrite_audio.py synthesize --text "..." --voice male-qn-jingying --out v_new.mp3
# Step 4: replace
python scripts/rewrite_audio.py replace --video v.mp4 --audio v_new.mp3 --out v_final.mp4
```

**文字成片:**
```bash
python scripts/text_to_video.py --prompt "A man running, cinematic" --out out.mp4
```

**数字人:**
```bash
python scripts/digital_human.py --avatar avatar.jpg --script "大家好" --out out.mp4
```

---

## 5. Mavis 集成

### 5.1 安装方式

```
D:\2Study\StudyNotes\SKILLS\智剪工坊\      ← 主体(给用户改)
C:\Users\辰辰洋洋\.mavis\skills\智剪工坊\ ← Mavis 入口(junction)
```

**junction 命令(Windows 管理员):**
```cmd
mklink /J "C:\Users\辰辰洋洋\.mavis\skills\智剪工坊" "D:\2Study\StudyNotes\SKILLS\智剪工坊"
```

### 5.2 Mavis 验证

```bash
mavis skill list 2>&1 | Select-String "智剪工坊"
mavis skill show 智剪工坊
```

应该看到:
- `name: 智剪工坊`
- 触发词包含"剪辑/转场/调色/智剪工坊/美颜/去水词/改词/文字成片/数字人"
- location 在 junction 路径

---

## 6. 立即可做(下个 session 第一件事)

### 6.1 工作流

新 session 看到这条消息后的工作流:
1. 读 `智剪工坊/HANDOFF.md`(本文件)
2. 读 `智剪工坊/SKILL.md`(已更新到 v0.5)
3. 读 `智剪工坊/CHANGELOG.md`(已更新到 v0.5)
4. 读 `智剪工坊/docs/FEATURE_COMPARISON.md`(已更新到 v0.5)
5. 读 `智剪工坊/docs/GETTING_STARTED.md`(已更新到 v0.5)
6. 跑 `verify.py --fast` 确认环境
7. 询问用户先做哪个:**真实 vlog 实测 / 新功能(声音克隆/SadTalkers)/ 跨平台测试 / 其他**

### 6.2 第一句问候(参考)

新 session 可以这样问候用户:

> "帅猎羽,看到 HANDO 了。智剪工坊 v0.5 完成,30 脚本全验证,5 个 AI 增强(美颜/去水词/改词/文字成片/数字人)都写完。
> 下一步建议:用你真实的 Day 2 vlog 把 5 个 AI 增强都跑一遍,看实际效果。我列了优先级:
> 1. **真实 vlog 实测**(⭐⭐⭐⭐⭐)— 5 个 AI 增强 + 流水线都跑一次
> 2. **跨平台测试**(⭐⭐⭐)— Mac/Linux 完整测一遍
> 3. **新功能**(⭐⭐)— 声音克隆(自训)/ SadTalkers 精准嘴型
>
> 你想先做哪个?"

---

## 7. 已有文件(下个 session 不要重新写)

```
D:\2Study\StudyNotes\SKILLS\智剪工坊\
├── SKILL.md                          ← 主入口(已识别,v0.5 14 子技能)
├── README.md                         ← 架构说明(v0.2)
├── HANDOFF.md                        ← 本文件(v0.5)
├── CHANGELOG.md                      ← v0.5 版本日志
├── requirements.txt                  ← 9 个实依赖
├── setup.bat / setup.sh              ← 一键安装
├── verify.py                         ← 5 秒快检 29/29 + 6 冒烟
├── config.json                       ← ffmpeg 路径配置
│
├── lib/
│   ├── common.py                     ← 公共库(safe_run + log_progress + safe_batch + 文件日志)
│   └── llm_client.py                 ← LLM 客户端(备用)
│
├── scripts/                          ← 30 个 Python 脚本
│   ├── cut.py / xfade.py / bgm_loop.py / cover_ai.py / pipeline_vlog.py
│   ├── reverse.py / speed.py / overlay.py / mask.py
│   ├── voice_change.py / color_style.py / beat_sync.py
│   ├── auto_subtitle.py / scene_detect.py / fx.py
│   ├── hdr_io.py / reframe.py / keyframe.py / multicam.py / style_transfer.py
│   ├── batch.py / quotes.py / cutout.py
│   ├── text_to_video.py / digital_human.py / translate.py
│   ├── beauty.py                     ← v0.3 美颜 L2
│   ├── remove_fillers.py             ← v0.4 去水词 L2
│   └── rewrite_audio.py              ← v0.4 改词翻唱 L2
│
├── references/                       ← 15 个子技能文档(全 prepend v0.5 状态头)
│   ├── 01-cutting.md ... 11-pipelines.md
│   ├── 12-beauty.md                  ← v0.3
│   ├── 13-rewrite-audio.md           ← v0.4
│   ├── 14-text-to-video.md           ← v0.5
│   └── 15-digital-human.md           ← v0.5
│
├── docs/                             ← 产品文档(全 v0.5)
│   ├── GETTING_STARTED.md            ← 新手引导(30 脚本速查)
│   ├── VS_JIANYING.md                ← vs 剪映(5 差异化能力)
│   ├── FAQ.md                        ← 常见问题(34 Q&A)
│   └── FEATURE_COMPARISON.md         ← vs 剪映/Pr/Resolve/FCP
│
└── assets/
    ├── fonts/  luts/  templates/  test_videos/  output/  cache/
    ├── config.json
    ├── face_landmarker.task          ← mediapipe 模型(自动下载)
    └── README.md
```

---

## 8. 记忆要点(给新 session)

### 8.1 用户绝不能搞错的

- ✅ 飞书消息 < 2000 字(超过会折叠)
- ✅ 长报告写文件 + `<media />` tag
- ✅ 重要选项用 `ask_user` 工具 + 详细文字解释
- ✅ 老朋友式沟通,不要激情喊话
- ✅ 第一性原理思考
- ✅ 用户口播用 Whisper 原话 + 修正错字(不是替换)
- ❌ 不要替用户做决定(选项让他选)
- ❌ 不要激情喊话、不要鸡汤

### 8.2 用户喜欢 / 不喜欢

- ✅ 喜欢:给选项 + 我的建议 + 让他拍板
- ✅ 喜欢:从第一性原理分析
- ✅ 喜欢:数据驱动(统计数字、对比表)
- ✅ 喜欢:简洁、有判断、不绕弯
- ❌ 不喜欢:长篇大论不点题
- ❌ 不喜欢:不告诉他技术细节
- ❌ 不喜欢:用"看情况"这种模糊回答

### 8.3 Mavis 系统关键信息

- skill 位置: `C:\Users\辰辰洋洋\.mavis\skills\`
- 路径冲突:用 junction(无需管理员),不用 symbolic link
- SKILL.md 必含 YAML frontmatter(`name: 智剪工坊` + `description:`)
- 触发词在 description 里,系统用它路由
- mavis CLI 路径:`C:\Users\辰辰洋洋\.mavis\bin\mavis.cmd`(subprocess 找不到,需 `shutil.which` 兜底)

### 8.4 ffmpeg 关键命令

```bash
# 查看视频信息
ffmpeg -i video.mp4 2>&1 | findstr "Duration|Stream|fps"

# 找 ffmpeg
D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe

# 公共 ffmpeg 调用
ffmpeg -y -i in.mp4 -ss 0 -t 5 -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30" -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 128k -movflags +faststart out.mp4
```

---

## 9. 下个 session 必读(优先级)

1. **本文件 Handoff** (5 分钟)
2. **SKILL.md** (1 分钟)
3. **CHANGELOG.md** (1 分钟)
4. **FEATURE_COMPARISON.md** (5 分钟)
5. **GETTING_STARTED.md** (2 分钟)
6. **跑 verify** (1 分钟)
7. **询问用户优先级** (1 分钟)

**总: ~15 分钟上手**

---

## 10. 紧急联系

如果下个 session 出现关键 bug(比如 8 小时视频、NVENC 崩溃、AI 中文乱码、脚本空跑),回看:
- §1.3 v0.3 → v0.5 bug 修复记录
- §2 关键 Bug 教训
- §4.3 关键命令模板

不要瞎试,先看历史方案。

---

**祝下个 session 顺利。** —— 2026-07-03 16:00 当前 session 留
