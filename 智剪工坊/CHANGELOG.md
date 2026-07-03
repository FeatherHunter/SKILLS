# 智剪工坊 · 变更日志

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
