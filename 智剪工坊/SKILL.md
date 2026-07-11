---
name: 智剪工坊
description: >
  代码视频剪辑工作台,对标剪映(图形化)+ 扩展(AI 能力)。
  触发词:剪辑、剪切、拼接、转场、调色、视频滤镜、慢动作、推镜头、字幕、烧字幕、变速、倒放、冻结帧、抽帧、水印、logo、色相、饱和度、缩放、裁剪、旋转、翻转、字母盒、封面、BGM、流水线、一条龙、智剪工坊、视频工坊、代码剪辑、
  美颜、磨皮、瘦脸、大眼、
  去水词、填充词、口头禅、嗯啊、
  改词、改写、翻唱、配音、换声、改写文案、
  文字成片、AI 生成视频、
  数字人、虚拟人、AI 讲解、
  音频降噪、降噪、噪声处理、
  声源分离、提取人声、人声分离、
  说话人分离、区分说话人、多人对话、谁说了什么。
  包含 30 个原子脚本 + 主体流程(阶段 0-5:项目初始化 / 意图对齐 / 粗加工 / 模板 / 收尾)。
  底层:ffmpeg + OpenCV + mediapipe + mmx matrix MCP(免费 AI 能力)。
triggers:
  - 剪辑
  - 剪切
  - 拼接
  - 转场
  - 淡入淡出
  - 调色
  - LUT
  - 慢动作
  - 推镜头
  - 字幕
  - 烧字幕
  - 封面
  - AI 封面
  - BGM
  - 加音乐
  - 音频降噪
  - 降噪
  - 声源分离
  - 提取人声
  - 人声分离
  - 说话人分离
  - 区分说话人
  - 人声提取
  - 纯人声
  - 对话增强
  - 静音检测
  - 自动分段
  - 说话人切分
  - 响度归一
  - 音量统一
  - LUFS
  - EBU R128
  - 美颜
  - 磨皮
  - 瘦脸
  - 大眼
  - 去水词
  - 填充词
  - 嗯啊
  - 改词
  - 翻唱
  - TTS
  - 配音
  - 换声
  - 文字成片
  - 数字人
  - 虚拟人
  - AI 讲解
  - 批量
  - 智能剪辑
  - 金句
  - 节拍卡点
  # === v1.8 新增（基于触发词审计发现维度索引里的专业词未覆盖） ===
  - ASR
  - Whisper
  - 语音转文字
  - 混音
  - 老声
  - 童声
  - 擦除
  - AI 生成视频
  - 流水线
  - 封面生成
  - AI 增强
  - 音频提取
  - 谁说了什么
  - 旋转
  - 裁剪
  - 自动字幕
  # === 视频底层 lib 触发词（v1.6）===
  - 视频滤镜
  - 加转场
  - xfade
  - 视频转场
  - 色相
  - 饱和度
  - 视频调色
  - 视频亮度
  - 视频对比度
  - 颜色平衡
  - 曲线
  - 变速
  - 倒放
  - 冻结帧
  - 缩放（视频）
  - 视频缩放
  - 视频裁剪
  - 旋转视频
  - 视频旋转
  - 翻转视频
  - 视频翻转
  - 加黑边
  - 字母盒
  - 加水印
  - 视频水印
  - logo 水印
  - logo 叠加
  - 抽帧
  - 改帧率
  # === v1.13 日志查询（新增）===
  - 查看日志
  - 日志在哪
  - 查看 process
  - 日志查询
  - 我刚才的操作
  - 复盘
  - audit
  - log
metadata: { "openclaw": { "emoji": "🎬", "requires": { "python": ">=3.10" } } }
---

# 智剪工坊 — 代码视频剪辑工作台

---

## ⚠️ 能力链路完整性（最高优先级原则）

> **所有修改者（AI / 开发者 / 协作者）必须遵守。本节优先级高于所有其他规则。任何 AI 在加载本技能后第一件事就是读完本节。**

### 1. 链路架构（AI 工作流）

```
SKILL.md（必读，触发词索引）
  ↓ 命中能力
  ├─ 简单调用 → 直接调 scripts/{audio,asr,video,ai,batch}/*.py
  └─ 复杂场景 → 读 references/*.md → 调 scripts/{audio,asr,video,ai,batch}/*.py
```

**scripts/{audio,asr,video,ai,batch}/** 是用户能力，AI 调它前必须确认 SKILL.md 已声明。
**scripts/_internal/** 是内部工具（下划线前缀），AI 不调。

### 2. 核心边界

| 概念 | 范围 |
|---|---|
| **用户可见能力** | SKILL.md 触发词 |
| **AI 可调实现** | `scripts/{audio,asr,video,ai,batch}/*.py`（必须在 SKILL.md 声明）|
| **内部工具** | `scripts/_internal/*.py`（下划线前缀，不进 SKILL.md）|
| **AI 可读文档** | `references/*.md`（按需）|

### 3. 修改契约（违反任意一条视为 SKILL 损坏）

| 修改对象 | 必须同步 | 允许不同步 |
|---|---|---|
| `scripts/{audio,asr,video,ai,batch}/` 新增 / 重命名 | SKILL.md 触发词 + `references/*.md` | — |
| `references/*.md` 新增 / 重命名 | SKILL.md 触发词索引 | — |
| SKILL.md 新增触发词 | `references/*.md` + `scripts/{audio,asr,video,ai,batch}/*.py` | — |
| `scripts/_internal/` 新增 | 无 | 全部（不进 SKILL.md）|

### 4. 禁止红线

- **SKILL.md 列出但 `scripts/{audio,asr,video,ai,batch}/` 没有** → AI 必须告知用户「该能力暂未实现」
- **用户请求的能力在 SKILL.md 没找到** → 不许自己造脚本，先报告
- **`scripts/_internal/` 调成了 `scripts/{audio,asr,video,ai,batch}/`** → 视为 SKILL 损坏，必须报告
- **AI 修改时只改了一处没同步其他** → 严重不一致立即停下报告；轻微不一致自动修 + 报告

### 5. backward-compat

**禁止**。任何修改后整个技能统一使用新路径和新能力，不保留旧路径 stub。
旧调用方需同步更新路径（这是修改的一部分，不是 backward-compat）。

### 6. 执行机制（AI 修改后必须做的自检清单）

**修改任何能力链路相关文件后，AI 必须主动审视全链路，按以下清单逐项打勾：**

```
□ 1. 我改了什么？→ 列出改动清单（哪个文件、改了哪段、为什么）
□ 2. 链路里其他位置是否需要同步？
       - 改 scripts/{audio,asr,video,ai,batch}/ → 同步 SKILL.md 触发词 + references/*.md
       - 改 SKILL.md 触发词 → 同步 references/*.md + scripts/{audio,asr,video,ai,batch}/
       - 改 references/*.md → 同步 SKILL.md 触发词
□ 3. 主动检查（不强求工具脚本）：
       - 读 SKILL.md 触发词索引 → 新能力是否已声明？
       - 读 references/ 对应文档 → 是否覆盖新能力？
       - ls scripts/{audio,asr,video,ai,batch}/ → 新能力是否实际存在？
□ 4. 全部一致 → 标记完成
□ 5. 发现不一致：
       - 严重不一致 → 立即停下报告
       - 轻微不一致 → 自动修 + 在最终回复里报告
```

**不强求调任何脚本。AI 自己读文件、自己比对、自己判断。**

未来扩展：
- 需要更细粒度检查时，可在 `scripts/_internal/` 加工具脚本（AI 可选调用）
- 工具脚本**不替代**这份清单，是这份清单的加速器
- 工具脚本发现的不一致项，必须在最终回复里复述一遍（避免 AI 忽略工具输出）

---

## 🔌 Loading 触发器（AI 必读）

> AI 加载 SKILL.md 后，按本触发器决定**何时加载哪个 references/**。
> 避免一次性加载所有 references/ 导致 context 爆炸。

### 路由命中触发

| 用户口语 / 触发词 | 加载 references/ |
|---|---|
| 美颜/磨皮/瘦脸/大眼 | `美颜-四种人脸美化.md` |
| 调色/LUT/视频调色/调色预设 | `调色预设-18种预设LUT风格迁移.md` |
| ASR/Whisper/语音转文字/说话人分离/声源分离 | `ASR链路-声源分离说话人分离Whisper烧字幕.md` |
| 音频降噪/BGM/混音/节拍卡点 | `音频配乐-BGM循环淡入淡出节拍.md` |
| 转场/淡入/擦除/滑动 | `转场-9种转场类型.md` |
| 字幕/烧字幕/封面文字 | `字幕文字-Whisper烧字幕片头变声.md` |
| 数字人/虚拟人/AI 讲解 | `数字人-AI主播头像说话.md` |
| 改词/翻唱/配音/换声 | `改词翻唱-文案改写TTS替换音轨.md` |
| 文字成片/AI 生成视频 | `文字成片-mmx免key生成6秒片段.md` |
| 抠图/金句/去水词/蒙版 | `AI智能剪辑-抠图金句去水词蒙版.md` |
| 批量/流水线 | `批量处理-多视频统一操作.md` |
| 慢动作/推镜头/倒放 | `电影感剪辑-变速倒放多机位.md` |
| 剪头/剪尾/裁切/分段 | `精剪-剪头剪尾保留段切中间.md` |
| 图片转视频/Ken Burns | `图片转视频-静态图KenBurns效果.md` |
| 旋转/缩放/裁剪/静音/提取音频 | `原子操作-14种基础剪辑指令.md` |
| 封面/AI 封面 | `AI封面-生图叠字两步法.md` |
| 帧级剪切/多段拼接/分段合并 | `剪切拼接-帧级剪切与多段合并.md` |
| 视频特效/调色/字幕/文字叠加 | `视觉特效-慢动作推镜头模糊.md` |

### 行为协议触发

| AI 场景 | 加载 references/ |
|---|---|
| 阶段 0 用户选 ①（从零开始） | `主流程-阶段编排.md` |
| 阶段 1 必读（路由表） | `AI路由表-意图JSON字段枚举.md` |
| 阶段 1 缺失必填字段时 | `AI交互式采访触发条件.md` |
| 阶段 1 决定要不要问用户时 | `场景覆盖度自检.md` |
| **AI 撞异常（任何阶段）** | `异常处理协议.md` |
| **AI 修改 SKILL/md/脚本** | `红线契约-AI触发审查.md` |
| **AI 加载后必读（协议层）** | `AI行为日志协议.md` |
| **Step 7 意图对齐完成** | `意图对齐-操作影响告知.md` |
| 用户口语映射路由 | `Jargon-用户口语映射.md` |
| AI 协作详细条款 | `AI协作协议-详细.md` |
| AI 调用 `lib/ffmpeg/audio` 时 | `音频链路-lib详解.md` |
| AI 调用 `lib/ffmpeg/video` 时 | `视频底层-lib详解.md` |
| AI 遇到 muted video 拼接异常 | `视频拼接-muted风险.md` |
| **AI 处理带 displaymatrix / rotation 的视频源**（手机竖屏拍摄最常见） | `rotation-metadata-处理.md`（3 层坑 + 修复套路） |
| **用户说"查看日志/复盘/audit"** | `commands/查看日志.sh`（shell 优先）+ `AI行为日志协议.md` |
| **AI 进入粗加工（Step 9）** | `粗加工-执行契约.md` |
| **AI 进入精加工（Step 11）** | `精加工-两路径.md` |
| **AI 进行审查（Step 10 / Step 12）** | `审查-用户交互循环.md` |
| **AI 粗加工完成时**（v1.12 强制 announce + 备份提示） | `二次加工-复用工作流.md` |
| **新会话检测粗加工_备份_*** 目录 | `二次加工-复用工作流.md` |

### 加载规则

1. AI 加载 SKILL.md 后，先扫本触发器
2. 按需加载（不要一次性全加载）
3. 加载后，把关键摘要写回 `<workspace>/00_智剪/logs/<task_id>_<timestamp>.md`（避免重复加载，完整路径见 `references/AI行为日志协议.md` §6）

---

## 📂 scripts/ 目录命名约定

> v1.7 引入的下划线前缀约定，AI 必须遵守。

### 目录分类

| 目录前缀 | AI 行为 | 用途 |
|---|---|---|
| `scripts/{audio,asr,video,ai,batch}/` | ✅ 可调 | 用户可见脚本（30+ 个原子 CLI）|
| `scripts/_internal/` | ❌ 不可调 | 内部工具（开发者用，AI 不调）|

### `_internal/` 命名约定

- **下划线前缀** = "AI 不调"的强信号
- 用途：一致性检查脚本、开发期调试工具、auto-fix 工具等
- AI **禁止**调 `scripts/_internal/*.py` —— 调用即视为 SKILL 损坏（详见 §能力链路完整性 §4 红线）
- 例外：仅当 `scripts/_internal/` 中的工具**明确**写入 SKILL.md "工具脚本可加速" 章节时，AI 才可**可选**调用

### AI 行为约束

- ✅ **必须**：路由用户需求到 `scripts/{audio,asr,video,ai,batch}/*.py`
- ❌ **禁止**：自己发现 `scripts/_internal/` 中有工具就直接调用
- ❌ **禁止**：绕过 `_internal/` 直接修改 SKILL/md/scripts（违反红线契约）

---

## 💾 备份目录命名约定（v1.12）

**格式**：`粗加工_备份_<YYYYMMDD_HHMMSS>_<task_id_slug>`

**示例**：
```
00_智剪/粗加工_备份_20260710_140000_fitness-vlog/
00_智剪/粗加工_备份_20260710_141500_健身vlog训练/
```

**规则**：
- YYYYMMDD_HHMMSS = 秒级时间戳（防同日冲突）
- task_id_slug = intent.json.project.title 转 slug（防不同项目冲突）
  - 转小写、空格 → 短横线、保留中文（兼容剪映）
- 备份目录**只读**，AI 复用时不修改
- 详见 `references/二次加工-复用工作流.md`

---

## 📦 安装与配置

### 依赖

- **Python >= 3.10**
- **ffmpeg 7.1+**（系统 PATH 可调用）
- **GPU 链路（可选,推荐）**:CUDA 13.0+ + PyTorch 2.x — 启用 demucs（音频分离）/ whisper（ASR）/ pyannote（说话人分离）
- **Python 包**（按需安装,见下表）

| 能力 | 必需包 | 安装命令 |
|---|---|---|
| 音频分离（demucs）| demucs + torch | `pip install demucs torch --index-url https://download.pytorch.org/whl/cu130` |
| 说话人分离（pyannote）| pyannote-audio + HF token | `pip install pyannote-audio` |
| ASR 转文字（whisper）| faster-whisper | `pip install faster-whisper` |

### 配置项

| 环境变量 | 说明 | 影响范围 |
|---------|------|---------|
| `HF_ENDPOINT` | HuggingFace 镜像源（默认 `https://hf-mirror.com`） | demucs / pyannote / whisper 模型下载;**首次未设会导致 huggingface.co 超时** |
| `HF_HOME` | HF 模型缓存路径（默认 `D:/AI/cache/huggingface`） | 1.5 GB+ 模型缓存到 D 盘,C 盘不动 |
| `TORCH_HOME` | PyTorch 模型缓存路径（默认 `D:/AI/cache/torch`） | demucs 主模型存 D 盘 |

**首次设置**（永久写到 User 注册表,新 shell 自动生效）:

```powershell
[System.Environment]::SetEnvironmentVariable("HF_ENDPOINT", "https://hf-mirror.com", "User")
[System.Environment]::SetEnvironmentVariable("HF_HOME", "D:/AI/cache/huggingface", "User")
[System.Environment]::SetEnvironmentVariable("TORCH_HOME", "D:/AI/cache/torch", "User")
```

### 一键安装 prompt

请帮我安装智剪工坊技能:
1. **检查环境**:Python 版本 + ffmpeg 版本 + GPU（PyTorch 是否可用）+ 检查 3 个 HF 环境变量是否已设
2. **引导配置环境变量**:未设则提示用户授权,授权后用 PowerShell `SetEnvironmentVariable` 写注册表永久生效
3. **显示当前环境变量配置**:逐个 `GetEnvironmentVariable` 输出
4. **验证**:跑一次 `python scripts/audio/voice_extract.py --help` 确认链路通

### 🤖 AI 撞墙自动帮设（契约）

**撞到 `huggingface.co 超时 / ConnectionError / 404 Not Found` 时**:AI 必须按以下流程处理,不要只抱怨

1. **检测**:出现 `huggingface.co` / `HF_ENDPOINT` 相关报错 → 当前 3 个 env var 没设或设错
2. **诊断**:跑 `Get-ChildItem Env:HF_* + Env:TORCH_HOME` 查看当前状态
3. **征求用户授权**:"智剪工坊需要 3 个环境变量才能跑 HF 模型(避免每次撞墙),授权我用 PowerShell 永久写入 User 注册表吗?"
4. **授权后跑 SetEnvironmentVariable**:写完后 `GetEnvironmentVariable` 验证回显,再让用户重新触发业务
5. **未授权**:提示用户手动跑上方"首次设置"代码块,等用户跑完继续业务

> **不变更未经授权的注册表**。AI 默认报错误 + 给出修复命令,只有用户明确同意才动 SetEnvironmentVariable。

---

## ⚠️ muted 视频拼接风险（v1.10 已修，详见 references/）

v1.10 修复 muted 视频拼接时长异常 bug 的**完整技术细节**见 `references/视频拼接-muted风险.md`。

**触发场景摘要**：
- `voice: "mute"` 的 video 后面拼接有 audio 的 video
- 多个 muted segments 互相拼接

**检测命令**：`ffmpeg -i input.mp4 2>&1 | grep -A 1 "Stream #0"`（看 muted mp4 是否还有 audio 行）

---

## ⚠️ Rotation metadata 3 层坑（v1.13 沉淀，详见 references/）

手机竖屏拍摄的视频带 `displaymatrix` rotation metadata,处理有 **3 层隐藏坑**(任何视频处理流程 AI 必读):

| 坑 | 症状 | 修复 |
|---|---|---|
| **1. displaymatrix 残留** | 输出仍带 `displaymatrix: rotation of -90`,部分播放器"再旋转一次" | 调 `lib/video/patch_mp4_rotation.py` 清 tkhd matrix |
| **2. user metadata `rotate=90` 残留** | iOS/微信等优先读 user metadata,可能再旋转 | ffmpeg 加 `-metadata rotate=` + `-map_metadata -1` |
| **3. filter_complex 传播 displaymatrix** | `trim.py concat` / `xfade.py` 内部用 filter_complex,会传播 side data 到 output | 拼接后再 patch 一次 |

**完整处理套路**:
1. 处理前 `ffprobe -i input` 检查 displaymatrix
2. v1 处理:**不加 `-noautorotate`**,让 ffmpeg 自动应用(比手动 transpose 准)
3. ffmpeg 命令加 `-metadata rotate=` 清 user metadata
4. ffmpeg 工序结尾调 `patch_mp4_rotation` 清 tkhd matrix
5. 拼接后再 patch 一次

**绝对不要**:
- ❌ 手动猜 transpose 方向(几乎肯定猜错,见 DAY9 案例)
- ❌ 用 `-noautorotate` 但不 patch(会留 metadata)
- ❌ 拼接后不 patch(filter_complex 传播)

**完整技术细节 + 案例 + 工具用法**见 `references/rotation-metadata-处理.md`(2026-07-11 沉淀)。

**暗坑**: 源无 displaymatrix 但实际是竖屏(老安卓机/截屏常见) — 当前方案无法主动检测,需 user 看到输出后人工发现。
---

## 🐍 项目 venv（hybrid 隔离）

智剪工坊依赖重（GPU/torch/demucs/pyannote/whisper）,**推荐项目本地 venv 隔离**,避免污染全局 Python,出问题重装快。

**venv 路径**:`<skill_root>/venv/`（即 `D:\2Study\StudyNotes\SKILLS\智剪工坊\venv\`）

### 一次性创建 + 装包（已装过可跳过）

```powershell
# 1. 在技能根目录创建 venv（用系统 Python 3.10+）
cd "D:\2Study\StudyNotes\SKILLS\智剪工坊"
python -m venv venv

# 2. 激活 venv（之后所有命令都用 venv 的 Python）
.\venv\Scripts\Activate.ps1

# 3. 先装 torch GPU 版（必须用 PyTorch 专用 index,否则下到 CPU）
pip install -r requirements-torch.txt --index-url https://download.pytorch.org/whl/cu130

# 4. 装其余包（PyPI 默认）
pip install -r requirements.txt

# 5. 验证
python -c "import torch, demucs, pyannote, faster_whisper; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
```

### 日常激活

```powershell
cd "D:\2Study\StudyNotes\SKILLS\智剪工坊"
.\venv\Scripts\Activate.ps1
```

激活后 shell 提示符前会多一个 `(venv)` 标识,这时跑 `python scripts/audio/separate.py ...` 走的就是 venv 里的 Python。

### 模型缓存路径（不重下）

模型**不**放 venv 里,**沿用**`D:\AI\cache\` 路径（HF_HOME / TORCH_HOME 已永久写入 User 注册表）：

| 类型 | 路径 |
|---|---|
| HF 模型（Whisper large-v3 等）| `D:\AI\cache\huggingface\` |
| PyTorch 模型（htdemucs 等）| `D:\AI\cache\torch\` |

venv 只隔离 Python 包,**不隔离模型** — 这样多个 skill 共享同一份模型缓存,省磁盘。

### 🤖 AI 行为约定

- **检测到 venv 不存在**:AI 必须提示用户「需要创建 venv + 装包」,给出上方 5 步命令,**不自动跑**
- **检测到 venv 存在但当前 Python 是系统 Python**:AI 提示「需要先激活 venv」,给上方激活命令
- **不破坏 venv 隔离**:AI 跑测试/集成时**必须**用 `<skill_root>/venv/Scripts/python.exe`,不用全局 python
- **永不自己创建/删除 venv**:venv 由用户控制,AI 只检测状态

---

## 入口模板

加载本技能后，直接输出以下内容给用户，然后在用户答复后进入对应流程：

---

> ⚠️ 开始之前，请把要处理的**所有视频、图片、BGM** 放到**同一个文件夹**里。

### 你今天想做什么？

**① 从零开始做一个完整的视频**（有多个素材，想拼成一个成片）
→ 回答几个问题后，我会帮你规划完整流程

**② 只做一个操作**（比如只剪一刀、只加字幕、只调色）
→ 告诉我你想做什么：
  - "剪掉开头/结尾"
  - "去掉中间一段"
  - "加字幕"
  - "调色/加滤镜"
  - "加背景音乐"
  - "做封面"
  - 其他需求直接说

**③ 多个视频批量处理**（统一剪、统一调色等）
→ 告诉我哪些视频 + 要做什么操作

**④ 用文字生成视频**（没有素材，想用 AI 生成）
→ 说"文字成片"或"AI 生成视频"

**⑤ 数字人讲解**（AI 主播口播）
→ 说"数字人"或"AI 讲解"

---

## v1.3 协议层（核心变化）

**v1.3 架构核心**: **AI 是编排者，原子 CLI 是工具，step 脚本已删除**。

- 阶段 0-5 端到端流程（项目初始化 / 意图对齐 / 粗加工 / 模板 / 收尾）
- 阶段 1 必走：**操作清单 schema**（6 象限）作为阶段 2 执行契约
- 阶段 2-5：**AI 按 SKILL.md + references/ 自己编排原子 CLI**（不再调 step 脚本）
- 三原则：**零硬编码 / 零遗漏 / 零猜测**

---

## 📂 文件地图（v1.4 渐进式披露版）

**AI 第一件事**：读 §能力链路完整性。然后只读 SKILL.md（本文）。**按需加载 references/**——不要一次性全读。

| 文件 | 作用 | 何时读 |
|---|---|---|
| **SKILL.md**（本文件）| 工具契约 + 路由表 + **红线原则** | **必读第一份，优先级最高** |
| `references/剪切拼接-帧级剪切与多段合并.md` | 帧级剪切trim与多段合并concat | 路由命中裁剪时 |
| `references/转场-9种转场类型.md` | 9种转场类型 | 路由命中转场时 |
| `references/AI路由表-意图JSON字段枚举.md` | intent.json字段枚举 | **阶段1必读** |
| `references/视觉特效-慢动作推镜头模糊.md` | 调色/字幕/文字叠加 | 路由命中effects时 |
| `references/主流程-阶段编排.md` | 13 步用户流程视角（v1.12 重构）| **选①时必读** |
| `references/粗加工-执行契约.md` | 粗加工 5 步流程详细（v1.12 新）| AI 进入粗加工时 |
| `references/精加工-两路径.md` | 精加工两路径详细（路径 A 纯语言 + 路径 B 模板）（v1.12 新）| AI 进入精加工时 |
| `references/审查-用户交互循环.md` | 粗加工审查 + 精加工审查协议（v1.12 新）| AI 进行审查时 |
| `references/二次加工-复用工作流.md` | 粗加工备份 + 新会话复用（v1.12 新）| 粗加工完成时 + 新会话检测时 |
| `references/电影感剪辑-变速倒放多机位.md` | 推镜头/慢动作/倒放 | 路由命中cinematic时 |
| `references/精剪-剪头剪尾保留段切中间.md` | pin-range/cut-middle多段 | 路由命中cut时 |
| `references/调色预设-18种预设LUT风格迁移.md` | 13种color preset | 路由命中color时 |
| `references/图片转视频-静态图KenBurns效果.md` | image_to_video+KenBurns | 路由命中photo时 |
| `references/字幕文字-Whisper烧字幕片头变声.md` | 字幕/文字叠加/opening-text | 路由命中text时 |
| `references/音频配乐-BGM循环淡入淡出节拍.md` | BGM混音 + 变声 + 节拍 + 提取音频 | 路由命中 audio-mix / audio-voice / audio-beat / audio-extract 时 |
| `references/ASR链路-声源分离说话人分离Whisper烧字幕.md` | 音频降噪 / 声源分离 / 说话人分离 / ASR / 烧字幕完整链路 | **路由命中 asr / audio-denoise / audio-separate / audio-diarize 时必读** |
| `references/视频底层-lib详解.md` | ffmpeg 视频底层 lib（字幕烧录 / 转场 41 种 / 调色 / 速度 / 缩放 / 黑边 / 水印）| 路由命中 视频滤镜/转场/调色/烧字幕/水印 时必读 |
| `references/rotation-metadata-处理.md` | ⭐ **rotation 3 层坑**(displaymatrix 残留 / user metadata 残留 / filter_complex 传播)+ 完整修复套路(v1.13 沉淀) | **AI 处理带 displaymatrix / rotation 视频源时必读** |
| `references/AI封面-生图叠字两步法.md` | 封面生成（ai/text/image） + **📍 路径契约唯一真理（草稿/终稿/成片 3 步）**| **路由命中 cover 时必读** |
| `references/AI智能剪辑-抠图金句去水词蒙版.md` | AI抠图/去水词/翻唱 | 路由命中AI features时 |
| `references/AI交互式采访触发条件.md` | 8条必问/建议问/不必问触发条件 | **阶段0.4 + 阶段1 + 阶段5必读** |
| `references/场景覆盖度自检.md` | 12条场景支持情况 | 阶段0.4决定是否要问用户时 |
| `references/批量处理-多视频统一操作.md` | 批量处理 | 路由命中批量时 |
| `references/美颜-四种人脸美化.md` | 美颜/磨皮/瘦脸/大眼 | 路由命中美颜时 |
| `references/改词翻唱-文案改写TTS替换音轨.md` | 改词/配音/换声 | 路由命中改写时 |
| `references/文字成片-mmx免key生成6秒片段.md` | 文字成片/AI生成视频 | 路由命中text-to-video时 |
| `references/数字人-AI主播头像说话.md` | 数字人/AI讲解 | 路由命中数字人时 |
| `references/原子操作-14种基础剪辑指令.md` | rotate/scale/crop/mute | 路由命中edit时 |
| `scripts/audio/*.py` | 音频链路 CLI（L1-L5：混音/变声/节拍/提取/降噪/分离/说话人）| AI 调音频脚本时 |
| `scripts/asr/*.py` | ASR 链路 CLI（L6：转录/烧字幕/说话人合并）| AI 调ASR脚本时 |
| `lib/ffmpeg/audio/*.py` | ffmpeg 音频底层 lib（10 文件，70+ 函数）| AI 调音频 lib 时 |
| `lib/ffmpeg/video/*.py` | ffmpeg 视频底层 lib（7 文件，21+ 函数：字幕/转场/调色/速度/缩放/黑边/水印）| AI 调视频 lib 时 |
| `lib/separate_demucs.py` | Demucs 声源分离底层（Python API + GPU）| AI 调 demucs 时 |
| `lib/asr/pyannote.py` | pyannote 说话人分离底层（需 HF token）| AI 调 pyannote 时 |
| `lib/asr/whisper.py` | faster-whisper ASR 底层 | AI 调 ASR 时 |
| `scripts/audio/*.py` | 音频链路脚本（11 个：mix/voice/beat/extract/denoise/separate/diarize/voice_extract/silence_split/loudness_norm）| AI 调音频脚本时 |
| `scripts/asr/*.py` | ASR 链路脚本（3 个：transcribe/burn_subtitle/speaker_srt）| AI 调 ASR 脚本时 |
| `scripts/video/*.py` | 视频操作脚本（21 个：color/fade/freeze/trim/xfade 等）| AI 调视频脚本时 |
| `scripts/ai/*.py` | AI 能力脚本（9 个：cover/beauty/rewrite 等）| AI 调 AI 脚本时 |
| `scripts/batch/*.py` | 批量处理脚本 | AI 调批量时 |
| `scripts/_internal/*.py` | 内部工具（一致性检查等）| **AI 不调，开发者用** |
| `lib/video_processing.py` | 视频滤镜 + 转场 + rotation（v1.7 改名，原 processing.py） | 阶段 2/3 |
| `lib/video/patch_mp4_rotation.py` | MP4 rotation 补丁 | v1.7 新增 |
| `lib/common.py` | ffmpeg 包装 + 错误 + 日志 + safe_run | 共享逻辑，**勿重写** |
| `lib/cli_args.py` | CLI 参数解析辅助 | 共享逻辑 |
| `lib/filename.py` | sanitize_filename + get_output_path | 阶段 5 命名 |
| `智剪工坊-意图编辑.html` | 唯一前端：填表 → intent.json | 阶段 0 项目初始化 |

> **不读**：`.archive/`（CHANGELOG / HANDOFF / README / 架构 / docs/ 历史沉淀），开发者面向，AI 不读。

---

## 🚀 一句话目标

**读 intent.json → 调原子 CLI → 出成片**。AI 自己编排，自己决定调什么、怎么调。

---

## 📞 调用范式

### 单技能调用

```bash
# 例: 加 BGM
python scripts/audio/mix.py --input v.mp4 --bgm bgm.mp3 --volume 0.18 --output out.mp4

# 例: 声源分离（提取人声）
python scripts/audio/separate.py --input audio.wav --output vocals.wav --stem vocals

# 例: 说话人分离
python scripts/audio/diarize.py --input vocals.wav --output diar.json

# 例: ASR 转录 + 带说话人的 SRT
python scripts/asr/transcribe.py --input vocals.wav --srt audio.srt
python scripts/asr/speaker_srt.py --diarize diar.json --srt audio.srt --output audio_speaker.srt
```

### AI 增强（agent-driven 流程）

AI 在 §阶段 2-5 按 SKILL.md 路由表自己编排。详见 `references/主流程-阶段编排.md`。

### 大流程（主体阶段 0-5）

```
阶段 0 项目初始化 → 阶段 1 意图对齐 → 阶段 2 粗加工 → 阶段 3 模板 → **阶段 4 产物审查** → 阶段 5 收尾
```

详细 AI 编排步骤见 `references/主流程-阶段编排.md`。

---

## 📁 工作区（<workspace>/）

**v1.3 工作区约定**（AI 必读）：

```
<workspace>/
├── video_*.mp4                ← 源视频（AI 不动）
├── intent.json                ← 唯一跟源混居的 AI 文件
├── intent_v1.json             ← 版本快照
└── 00_智剪/                   ← AI 自管区
    ├── 粗加工/
    │   ├── 单视频/            ← 每个视频处理后的标准片段
    │   ├── 组合/              ← sequence + 转场拼好的组
    │   ├── 文字稿/            ← ASR 结果
    │   ├── 中间产物/          ← log / profile / 自检报告
    │   ├── cover/             ← **📍 路径契约唯一真理见 references/AI封面-生图叠字两步法.md**
    │   └── 决策.md            ← 整体要求 + 用户新增
    └── 成片/
        ├── vlog_final.mp4     ← 模板工作流深度加工后（命名见 §阶段 5）
        └── cover.jpg          ← 最终封面（从粗加工/cover/cover_final.jpg 复制）
```

**AI 必读规则**：
- **不动源视频**：`video_*.mp4` 永远只读
- **唯一配置文件**：`intent.json` 跟源混居，其他 AI 文件全部进 `00_智剪/`
- **粗加工 5 类产物**：单视频/组合/文字稿/中间产物/cover/决策.md（v1.0 强制）
- **成片必须按 `project.title` 命名**：见 `references/AI路由表-意图JSON字段枚举.md` §B 项目级

---

## 🎬 阶段 0 ▸ 项目初始化（v1.3 强制）

```
0.0  AI 问用户工作目录路径（用户首问时必答，例：「素材放在哪？」）
0.1  AI 第 1 件事就调 shell 打开 智剪工坊-意图编辑.html（**禁止先用文字问答代填**）:
       - Windows:  Start-Process "<skill_root>/智剪工坊-意图编辑.html"
       - macOS:    open "<skill_root>/智剪工坊-意图编辑.html"
       - Linux:    xdg-open "<skill_root>/智剪工坊-意图编辑.html"
       - HTML 文件在哪都行:浏览器用 File System Access API,用户在表单
         顶部点"选择文件夹"按钮授权工作目录,保存时直接写到授权目录
         (Firefox / Safari 不支持 → 走 fallback 下载模式,这时 HTML 位置无关)
0.2  用户填表 → 生成 intent.json
0.3  用户把 intent.json 给 AI
0.4  [可选] 若 intent.json 缺失必填字段
       → AI 触发交互式采访补全
       → 不允许 AI 自己编默认值
```

**AI 必读规则（v1.9 强化）**：
- **0.1 是第 1 件事**：用户选「① 从零开始做一个完整的视频」→ 进阶段 0 → **第 1 个动作必须是 Start-Process 打开 智剪工坊-意图编辑.html**，**不是**先 dialog 文字问项目名/主题
- **禁止 dialog 代填**：AI 不允许用「聊天问答」代替 智剪工坊-意图编辑.html 填表（dialog 看不到字段全景、容易遗漏、用户没法一次看清所有可选项）
- **意图类型决定走法**：选项 ②「只做一个操作」→ 不开 智剪工坊-意图编辑.html，**直接** dialog 一句话解决；选项 ③/④/⑤ → 按各自章节走
- **0.1 主动用 shell 打开**：Mavis/AI 必须用 `Start-Process`（Windows）/ `xdg-open`（Linux）/ `open`（macOS）帮用户打开 智剪工坊-意图编辑.html，**不得仅告知路径让用户自己找**（v1.3 强制）
- **0.4 缺失必填字段时必须问**：AI 不得自编默认值（v1.0 强制）
- 详细必填字段清单见 `references/AI交互式采访触发条件.md`

**后续阶段详见 `references/主流程-阶段编排.md`**（阶段 1-5 详细契约：输入/输出/跳过/异常/强制）

---

## ⚙️ 通用参数（所有子技能共享）

| 参数 | 短选项 | 说明 |
|---|---|---|
| `--input` / `--video` | `-i` | 输入视频（部分脚本接受图片 / 音频）|
| `--output` | `-o` | 输出路径 |
| `--start` | — | 起始时间（秒）|
| `--duration` | — | 时长（秒，部分脚本支持）|

**所有原子 CLI 必须支持 `-h/--help`**，不确定时调 `--help` 看参数。

---

## 🤖 AI 协作协议（v1.2 强制，v1.3 修订）

> 本节是 AI 与智剪工坊交互的**核心约束**。详细条款（路由第一原则 / 文本解析 / 模糊项 / 速度范围 / 时间字段 / 序列 / intent diff / 修改同步 / 真实照片 / 新增 ops 等 10 项）见 **`references/AI协作协议-详细.md`**。

### 核心原则（4 条）

1. **零硬编码** — 不绑定具体项目（vlog 主题、平台、用户）。所有流程描述用通用 schema, 遇到项目特有需求必须从 intent.json 读取。
2. **零遗漏** — intent.json 每个字段必须有去处（明确操作 / 隐含意图 / 未覆盖说明）。无"AI 心里有数"这种模糊状态。
3. **零猜测** — 凡 AI 推断的、模糊的、未覆盖的, 必须主动交互式采访, 不允许闷头执行。详见 `references/AI交互式采访触发条件.md`。
4. **零自写（v1.3 新增）** — **禁止 AI 自己写 Python/ffmpeg 代码实现智剪工坊功能**。必须调已有 用户脚本 CLI; CLI 失败或缺漏时, **明确告诉用户哪里有故障/缺漏/需要补充 CLI**, 让用户决定如何补——而不是 AI 自己写新代码替代。

### 执行契约（5 条, 违反任意一条视为流程失败）

- 阶段 1 必须输出「操作清单」并经用户确认 → 才进入阶段 2
- 阶段 2 Step 2 每处理完一个视频 → 立即向用户汇报产物路径 + 摘要 + 异常
- 出现卡死 / 超时 → 立即向用户汇报, 不得静默
- 用户未明确指定的选项 → 用操作清单 D 象限（模糊项汇总）列出, 逐条问
- **CLI 失败 / 缺漏** → 立即向用户报告: 哪个 CLI 失败 + 错误信息 + 是否需要补 CLI 或换方案, **不许 AI 自己写代码**

### AI 自写代码的 3 种典型反模式（v1.3 禁止）

- **反模式 1：CLI 不存在就自己写** — `scripts/{audio,asr,video,ai,batch}/` 里没有的子技能，AI 不得用 `subprocess.run(['ffmpeg', ...])` 直接拼命令行。
- **反模式 2：CLI 失败就自己 hack** — CLI 返回非 0 exit code, AI 不得用 Python 重写 ffmpeg 命令。
- **反模式 3：CLI 缺功能就扩展** — CLI 不支持某参数, AI 不得自己 fork CLI 加功能。

### AI 是编排者, 不是 step 脚本的调用者（v1.3 关键变化）

- ❌ **不要**调 `pipeline_step*.py`（v1.3 已删 6 个 step 脚本）
- ✅ **要**直接调 用户脚本 CLI（`scripts/{audio,asr,video,ai,batch}/*.py` / `lib/video_processing.py`）

### 触发锚点：选①时必读 references/主流程-阶段编排.md

选①（从零开始做完整视频）→ **立即加载** `references/主流程-阶段编排.md`（主体流程骨架）

阶段 2-5 的具体步骤在 `references/主流程-阶段编排.md`，SKILL.md 只给总览。


## 🎬 阶段 2.5: 字幕生成（可选但推荐,v1.10 新增）

如果用户要 sequence 标题字幕(给观众"分段导航"):

1. 读 `intent.json sequences[*].title`(新字段) 或从 sequence 内 video 的 summary 推断
2. 用 `opening.py add` 给每个 sequence 开头加 2-3 秒标题

   ```bash
   python scripts/video/opening.py add \
     --input seg.mp4 --output seg_with_title.mp4 \
     --text "早上 - 体重 + 八段锦" \
     --region top-center \
     --font-size 80 --font-color yellow \
     --duration 3
   ```

3. 用 `trim.py concat` 把 sequence 标题 prepend 到原 sequence

**跳过条件**:用户明确说"不要字幕" 或 intent.json 无 sequence 标题意图。

**intent.json 新字段**:

```json
{
  "sequences": [
    {
      "title": "早上 - 体重 + 八段锦",  // v1.10 新增,可选
      "videos": [1, 2, 3, 4]
    }
  ]
}
```

**intent.html 表单新增字段**(在 sequences 区块):

```html
<div class="field">
  <label>Sequence 标题(可选,显示在画面上)</label>
  <input type="text" name="sequence_title"
         placeholder="例:早上 - 体重 + 八段锦">
  <small>留空则自动从该 sequence 包含的 video summary 推断</small>
</div>
```

### 2. **per-video 音频同步是必须, 不是可选**

`trim` / `pin-range` / `cut-middle` 后视频流 `setpts=PTS-STARTPTS` 归零了 PTS, **但音频流原始 PTS 范围未归零, 音画不同步**。必须同步 trim 音频并 `asetpts=PTS-STARTPTS`。

✅ **已在 `scripts/ai/fillers.py cut_video` 第 262 行实现**(`asetpts=PTS-STARTPTS`)。
   其他 trim 工具仍需注意 audio 同步。

### 3. **video_normalize 是自动, 不是手动**

`process_video` 末尾自动调 `video_normalize`, 输出统一 30fps / yuv420p / aac 44100 stereo。

### 4. **ending.type 路由**（v1.3 修订, v1.10 扩展）

| 值 | 路由 | 备注 |
|---|---|---|
| `fade` | `video_fade.py --fade-out N` | 视频结尾淡出 |
| `freeze` | `video_freeze.py --freeze N --padding-mode {clone\|black}` | 最后一帧定格 |
| `next-day` | `video_opening.py add` + 黑屏源 | 黑屏 + 文字 |
| `next-episode-promo` | `video_opening.py add` + 黑屏源 | 下期预告(黑屏 + 预告文字) |
| `next-week` | 同 `next-episode-promo` | 下周预告 |
| `text` | `asr/burn_subtitle.py` + srt | 烧结尾文字 |

### 5. **cover.type 路由**

| 值 | 路由 | 备注 |
|---|---|---|
| `ai`（推荐）| `ai_cover.py` | 按 cover.prompt AI 生图 |
| `text` | `ai_cover.py --text-only` | 纯文字封面 |
| `image` | （**当前不支持**）| 告诉用户"改用 ai 或 text" |

**强制规则（v1.4 新增）**: 封面上的所有文字叠加（数字/标题/标签/徽章等）**必须通过 `ai_cover.py` 的 `overlay_text()` 实现**，禁止自己 import PIL 写独立脚本。`ai_cover.py` 内置 `msyhbd.ttc`（微软雅黑粗体）支持完整中文字符。若 `ai_cover.py` 当前参数不够用，需先扩展该 CLI，不许绕路。|

### 6. **B. project-level 操作**（v1.3 新增）

`output.bgm_match_mode` 路由到 `audio/mix.py --match-mode <mode>`（4 种: loop/truncate/silence-end/ask）。

### 7. **C. sequence 约束**（v1.3 新增）

- 视频+图片混合 sequence: 图片必须先转视频（`image_to_video.py`）
- 转场 type 必须从 9 种 type 选
- `duration` 默认 0.5s, 建议 ≥ 0.5s

### 8. **D. 模糊项 / 待澄清**

详见上文"AI 协作协议"§3。

### 9. **E. AI 文本解析**

详见上文"AI 协作协议"§2。

### 10. **F. 未覆盖字段（out-of-scope）**

- 智剪工坊**不**做的事: 实时流剪辑 / 直播剪辑 / 复杂多轨音频混音
- 用户提这类需求 → 明确说"智剪工坊当前不支持, 推荐 XXX 工具"

---

## 📊 操作清单 schema（v1.0 强制, v1.3 修订）

**6 象限**（AI 阶段 1 必走, 作为阶段 2 执行契约）:

| 象限 | 内容 | 例子 |
|---|---|---|
| A. per-video 操作 | 每个视频单独处理 | trim-head / pin-range / cut-middle / color / fade-in / fade-out |
| B. project-level 操作 | 项目整体 | target-length / output.bgm / output.bgm_match_mode |
| C. sequence 约束 | 视频播放顺序 | sequences[].videos / sequences[].transitions |
| D. 模糊项 / 待澄清 | 必须问用户 | 动感是什么意思？滤镜哪个？ |
| E. AI 文本解析 | 自由文本 → 路由 | notes / overall_intent / ending.prompt |
| F. 未覆盖字段 | 明确说不支持 | 直播 / 多轨音频 / 实时 |

---

## 🎨 模板工作流

AI 阶段 3 按 yaml 模板编排（`模板/健身vlog.yaml` 等）。每模板含 4 stage:
1. **rhythm**（差异化节奏：开头慢、主体快、结尾慢）
2. **order**（时间线驱动：按 sequence 顺序拼）
3. **transitions**（统一转场策略：所有 segment 用同一种 type）
4. **data_overlay**（开头目标 + 结尾达成：基于 intent 字段）

**模板命名规则**: `<类别>vlog.yaml`（如 `健身vlog.yaml` / `教程vlog.yaml`）。

---

## 🔤 Jargon 大白话词典（→ references/Jargon-用户口语映射.md）

**详细路由表**见 `references/Jargon-用户口语映射.md`（从 v1.10 SKILL.md §Jargon 大白话词典 拆出，含 21 条用户口语映射）。SKILL.md 不再保留重复条目。


## 📜 License

MIT（智剪工坊 © 2024-2026 帅猎羽）

---

## 🗂 目录结构（v1.4）

```
智剪工坊/
├── SKILL.md                          # 本文件（含红线原则，优先级最高）
├── 智剪工坊-意图编辑.html                       # 唯一前端（项目初始化）
├── references/                       # 23 个子技能文档（v1.5/v1.6 新增 2 个）
│   ├── 剪切拼接-帧级剪切与多段合并.md
│   ├── AI路由表-意图JSON字段枚举.md
│   ├── 转场-9种转场类型.md
│   ├── 视觉特效-慢动作推镜头模糊.md
│   ├── 主流程-阶段编排.md                # 选①必读（主体流程骨架）
│   ├── 电影感剪辑-变速倒放多机位.md
│   ├── 精剪-剪头剪尾保留段切中间.md
│   ├── 调色预设-18种预设LUT风格迁移.md
│   ├── 图片转视频-静态图KenBurns效果.md
│   ├── 字幕文字-Whisper烧字幕片头变声.md
│   ├── 音频配乐-BGM循环淡入淡出节拍.md    # 含降噪/声源分离/说话人分离
│   ├── ASR链路-声源分离说话人分离Whisper烧字幕.md  # v1.4 新增
│   ├── AI封面-生图叠字两步法.md
│   ├── AI智能剪辑-抠图金句去水词蒙版.md
│   ├── 批量处理-多视频统一操作.md
│   ├── 美颜-四种人脸美化.md
│   ├── 改词翻唱-文案改写TTS替换音轨.md
│   ├── 文字成片-mmx免key生成6秒片段.md
│   ├── 数字人-AI主播头像说话.md
│   └── 原子操作-14种基础剪辑指令.md
├── scripts/                          # 原子 CLI（按红线原则分类）
│   ├── audio/                       # 音频链路 L1-L5（用户可见，v1.7 保留）
│   │   ├── mix.py                   # BGM 混音
│   │   ├── voice.py                 # 变声
│   │   ├── beat.py                  # 节拍
│   │   ├── extract.py               # 提取音频
│   │   ├── denoise.py               # 降噪（v1.4）
│   │   ├── separate.py              # 声源分离（v1.4）
│   │   ├── diarize.py               # 说话人分离（v1.4）
│   │   ├── voice_extract.py         # 人声提取（v1.5）
│   │   ├── silence_split.py         # 静音分段（v1.5）
│   │   └── loudness_norm.py         # 响度归一（v1.5）
│   ├── asr/                         # ASR 链路 L6（用户可见，v1.7 保留）
│   │   ├── transcribe.py            # Whisper 转录（v1.7 改调 lib.asr.whisper）
│   │   ├── burn_subtitle.py         # 烧字幕（v1.6 调 lib.ffmpeg.video.subtitle）
│   │   └── speaker_srt.py           # 说话人+ASR合并（v1.4，纯文本合成）
│   ├── video/                       # ⭐ 视频操作（v1.7 新建，21 个脚本）
│   │   ├── color.py fade.py freeze.py xfade.py trim.py
│   │   ├── speed.py reverse.py normalize.py scene.py
│   │   ├── mask.py overlay.py reframe.py multicam.py
│   │   ├── opening.py subtitle.py style.py keyframe.py
│   │   ├── fx.py hdr.py edit.py image_to_video.py
│   │   └── __init__.py
│   ├── ai/                          # ⭐ AI 能力（v1.7 新建，9 个脚本）
│   │   ├── cover.py beauty.py cutout.py digital_human.py
│   │   ├── fillers.py quotes.py rewrite.py
│   │   ├── text_to_video.py translate.py
│   │   └── __init__.py
│   ├── batch/                       # ⭐ 批量处理（v1.7 新建）
│   │   ├── batch.py
│   │   └── __init__.py
│   └── _internal/                   # 内部工具（AI 不调，开发者用，v1.7 新建）
│       └── stage1_checklist.py
├── lib/                              # 共享逻辑（勿重写）
│   ├── common.py                    # ffmpeg + 错误 + 日志 + safe_run
│   ├── cli_args.py                  # CLI 参数解析辅助
│   ├── filename.py                  # 命名
│   ├── video_processing.py          # ⭐ 视频处理（v1.7 改名，原 processing.py）
│   ├── separate_demucs.py           # Demucs 声源分离底层（Python API + GPU，v1.7 改名避免与 demucs 包冲突）
│   ├── asr/                         # ⭐ ASR 第三方底库（v1.7 新建子目录）
│   │   ├── pyannote.py              # pyannote 说话人分离
│   │   └── whisper.py               # faster-whisper ASR
│   ├── video/                       # ⭐ 视频第三方底库（v1.7 新建子目录）
│   │   └── patch_mp4_rotation.py
│   ├── ffmpeg/
│   │   ├── audio/                   # 音频 lib（10 文件，70+ 函数，v1.5）
│   │   │   └── denoise / enhance / detect / normalize / transform / channel / visualize / effect / utility / measure / extract
│   │   └── video/                   # 视频 lib（6 文件，21+ 函数，v1.6）
│   │       └── subtitle / transition / color / timing / transform / watermark
│   └── ...
├── references/                       # 子技能文档（按需读）
│   ├── ...（v1.4 全部已存在的 references）
│   └── 视频底层-lib详解.md              # 视频 lib 文档（v1.6 新增）
├── 模板/                             # AI 阶段 3 编排模板
│   └── 健身vlog.yaml
└── .archive/                        # 开发者面向（AI 不读）
    ├── CHANGELOG.md
    └── ...
```

---
