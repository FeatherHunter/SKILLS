# 智剪工坊 · Session Handoff 文档

> **目的:** 用户(帅猎羽)要清空当前 session,这是给下一个 session AI 的完整上下文。
> **写于:** 2026-07-03 13:32 (Asia/Shanghai)
> **重要:** 必须读完整个文档再开始动手,尤其是"未完成需求"和"关键 bug"两节。

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

## 1. 当前状态(2026-07-03 15:00,新 session 进度)

### 1.1 已完成

| 维度 | 进度 | 备注 |
|---|---|---|
| 架构设计 | ✅ 100% | 11 子技能 + 1 大流程 |
| SKILL.md | ✅ 100% | YAML frontmatter, Mavis 已识别 |
| References | ✅ 100% | 11 个 .md,详细接口 + 命令 |
| 代码框架 | ✅ 100% | 27 个 .py 脚本(新增 beauty.py) |
| 公共库 | ✅ 100% | lib/common.py(读 config.json + 友好错误 + 跨平台) |
| 产品 README | ✅ 100% | 3 分钟快速开始 + 27 脚本速查 + 5 工作流 |
| 安装脚本 | ✅ 100% | setup.bat(Windows)+ setup.sh(Mac/Linux) |
| 验证脚本 | ✅ 100% | verify.py(5 秒快检 / 2 分钟全检) |
| 文档 | ✅ 100% | README + docs/ + CHANGELOG |
| 依赖 | ✅ 100% | requirements.txt 全实,清华源安装 |
| 验证(实测) | ✅ 100% | 27/27 import + 6/6 冒烟测试真正通过 |
| **可发布** | ✅ 90% | A 路线完成,任何人 5 分钟能装上用 |
| **美颜 L2** | ✅ 100% | beauty.py 完整(磨皮+美白+瘦脸+大眼)|
| 跨平台 | ⚠️ 50% | setup.sh 写好但只测了 Windows |
| 错误处理 | ⚠️ 50% | common.py 升级,12 个脚本没 try/except |
| 单元测试 | ❌ 0% | 待补 |
| CI/打包 | ❌ 0% | 待补 |
| 日志系统 | ❌ 0% | 待补(用 print 凑合) |
| AI 去水词 | ❌ 0% | B 路线下一站 |
| AI 改词翻唱 | ❌ 0% | B 路线再下一站 |

### 1.2 v0.3 进度(本 session)

**B 路线首项(美颜 L2)✅ 完成:**
- beauty.py 完整实现(磨皮+美白+瘦脸+大眼)
- mediapipe 0.10 task API 适配
- 5 个 preset 真实人脸测试通过

**重大 bug 修复(27 脚本):**
- 全部 27 个脚本入口 `safe_run(main)` → `safe_run(main)()`(之前 main() 根本没跑!)
- 现在 verify.py "6/6 冒烟通过" 是真的在跑

---

## 3. 关键 Bug 教训(必看)

### Bug 6: 全局 `safe_run(main)` 缺 `()`

**现象:** 全部 27 个脚本的入口 `safe_run(main)` 实际只创建了 wrapper 没调用
**影响:** 任何 `python scripts/xxx.py` 都静默退出(0),啥也没跑
**修法:** 批量 `safe_run(main)` → `safe_run(main)()`
**教训:** 装饰器工厂的 entry point 一定要带 `()` 才能调起来

### Bug 7: mediapipe 0.10.35 Windows 中文路径

**现象:** 模型路径含中文/日文 → `FileNotFoundError: Unable to open file`
**修法:** `lib/common.py` 已自动 fallback 到 `C:\zhijian_models\`
**应用:** beauty.py 的模型管理已用

### Bug 8: mediapipe 0.10 移除 `solutions` API

**现象:** `mp.solutions.face_mesh` 不存在
**修法:** 改用 `mp.tasks.vision.FaceLandmarker`
**应用:** beauty.py 已用新 API

### Bug 9: ffmpeg 7.1 不支持 `curves=preset=X`

**现象:** `curves=preset=warm` 报错 "Invalid argument"
**修法:** 批量移除 `curves=preset=X` 段
**影响:** color_style / fx 已修

### Bug 10: fx.py 的 intensity blend 语法错

**现象:** `split[orig];[orig][orig]blend=...` 写错,ffmpeg 报 input/output 数量错
**修法:** 简化为静态效果,intensity 改成提示信息

### 1.2 26 个脚本清单

```
[核心 5]   cut · xfade · bgm_loop · cover_ai · pipeline_vlog
[P0 基础 7]  reverse · speed · overlay · mask · voice_change · color_style · beat_sync
[P1 基础 3]  auto_subtitle · scene_detect · fx
[P1 进阶 5]  hdr_io · reframe · keyframe · multicam · style_transfer
[P2 已有 3]  batch · quotes · cutout
[P2 战略 3]  text_to_video · digital_human · translate
```

**严格审查结果**(全 ✅ 完整代码,无占位):

| 脚本 | 行数 | 错误处理 |
|---|---|---|
| auto_subtitle.py | 120 | ✅ |
| batch.py | 174 | ✅ |
| beat_sync.py | 127 | ✅ |
| bgm_loop.py | 74 | ❌ |
| color_style.py | 115 | ❌ |
| cover_ai.py | 166 | ❌ |
| cut.py | 92 | ✅ |
| cutout.py | 160 | ✅ |
| digital_human.py | 143 | ✅ |
| fx.py | 139 | ❌ |
| hdr_io.py | 114 | ❌ |
| keyframe.py | 137 | ✅ |
| mask.py | 124 | ✅ |
| multicam.py | 199 | ✅ |
| overlay.py | 110 | ❌ |
| pipeline_vlog.py | 256 | ✅ |
| quotes.py | 184 | ✅ |
| reframe.py | 134 | ✅ |
| reverse.py | 51 | ❌ |
| scene_detect.py | 160 | ✅ |
| speed.py | 129 | ❌ |
| style_transfer.py | 184 | ✅ |
| text_to_video.py | 150 | ❌ |
| translate.py | 216 | ✅ |
| voice_change.py | 90 | ❌ |
| xfade.py | 89 | ✅ |

**已真实跑通的 5 个:** cut / reverse / color_style / fx / reframe
**未跑过的 21 个:** 需装依赖后才能验证

### 1.3 路径信息(必读)

```
主位置:  D:\2Study\StudyNotes\SKILLS\智剪工坊\
Mavis 入口: C:\Users\辰辰洋洋\.mavis\skills\智剪工坊\  (junction)

ffmpeg 路径: D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe
ffprobe:  没有(用 ffmpeg -i 验证)

Python:   3.13 (D:\0Tools\Python313\python.exe)
工作脚本目录: D:\0Tools\FunASR\workspace\  (历史工作区,Day 1 跑过)

用户的 B 站 vlog 目录:
  D:\2Study\StudyNotes\2026\自媒体\DAY1\  (已发,11 段原始视频)
  D:\2Study\StudyNotes\2026\自媒体\DAY2\  (待拍)
```

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
**教训:** ffmpeg 跑完必须用 `ffmpeg -i output.mp4 | grep Duration` 验证,不能光信脚本输出

### Bug 3:AI 生图中文乱码

**现象:** matrix 生图对中文/数字支持差(90% 渲染错)
**解决:** 拆成两步 —— 先生成视觉(无文字),后用 PIL 叠中文
**代码位置:** `scripts/cover_ai.py` 已用两步法

### Bug 4:reframe.py 的 f-string 冲突

**现象:** `f"crop={new_w}:{new_h}:({iw-{new_w})/2"` 中 f-string 把 `iw` 当 Python 变量
**解决:** 改成 `(iw-{new_w})/2`(去掉外层 `{}` 让 ffmpeg 解析)
**已修**

### Bug 5:PowerShell 调 Python 行为怪

**现象:** `python scripts\xxx.py --help` 经常没输出(直接调 `main()` 才行)
**解决:** 跨平台用 `python -c "import sys; sys.path.insert(0, 'lib'); sys.path.insert(0, 'scripts'); sys.argv = [...]; import xxx; safe_run(xxx.main)()"` 这种方式

---

## 3. 未完成需求(用户最新要求,2026-07-03 13:32)

### 3.1 核心目标

> 用户原话:"全面落地吧,先是可以发布版本。骨架完善到 90%,功能也完善到 90%(对标剪映)"

**3 件事:**
1. **可发布版本**(让别人能直接用)
2. **骨架完善到 90%**
3. **功能完善到 90%(对标剪映)**

### 3.2 "可发布" Checklist(4 大块)

**1. 安装脚本(setup.bat + setup.sh)**
- 自动装 Python 依赖
- 自动检测 ffmpeg(没有就提示下载)
- 自动创建目录结构
- 自动写 assets/config.json 模板
- 跨平台(Win/Mac/Linux)

**2. 验证脚本(verify.py)**
- 检查 ffmpeg 可用
- 检查所有 Python 包装了
- 跑一个 5 秒测试视频,确认每个子技能能跑
- 输出"通过/失败"清单

**3. 友好的错误提示**
- 现在:出错了 print stderr
- 目标:"X 缺失,请运行 `pip install X`" + 自动给命令
- 改 `lib/common.py` 的 `safe_run` 装饰器

**4. 产品级 README**
- 3 分钟快速开始
- 完整功能列表
- 常见问题(对方没装 ffmpeg 怎么办 / API key 怎么申请)
- 截图 / demo 视频

### 3.3 "对标剪映" Gap(功能补到 90%)

**剪映 2025 全部功能 vs 智剪工坊现状:**

| 剪映功能 | 智剪工坊 | 状态 |
|---|---|---|
| 切割 | cut.py | ✅ |
| 倒放(0.2-100x 变速) | reverse.py / speed.py | ✅ |
| 画布 | cut.py 内置 | ✅ |
| 转场(~30 种) | xfade.py(60+ 种) | ✅ 超过 |
| 滤镜(18 预设 + 美颜) | color_style.py(13 种) | ⚠️ 无美颜 |
| 美颜 | — | ❌ 缺 |
| 智能字幕(27 语) | auto_subtitle.py | ✅ |
| 变声(12 种) | voice_change.py(7 种) | ✅ |
| 智能抠像(3 种) | cutout.py(rembg, 1 种) | ⚠️ 简化 |
| 画中画 | overlay.py | ✅ |
| 蒙版 | mask.py | ✅ |
| 关键帧 + 曲线 | keyframe.py | ✅ |
| HDR 导入导出 | hdr_io.py | ⚠️ 简化 |
| AI 文字成片 | text_to_video.py | ⚠️ 框架,需 API key |
| AI 一键成片 | — | ❌ 缺 |
| 多轨道(10 层) | multicam.py(4 路) | ⚠️ 简化 |
| 智能卡点 | beat_sync.py | ⚠️ 简化 |
| 立体 3D 字幕 | — | ❌ 决定不做(ffmpeg 不擅长) |
| AI 视频翻译 | translate.py | ⚠️ 框架,需 edge-tts + 翻译 API |
| AI 转场 | — | ❌ 缺 |
| AI 智能去水词 | — | ❌ 缺 |
| AI 改词翻唱 | — | ❌ 缺 |
| 风格迁移 | style_transfer.py | ✅ |
| AI 数字人 | digital_human.py | ⚠️ 框架,需 API key |
| 模板市场 | — | ❌ 决定不做 |
| 素材库 | — | ❌ 决定不做 |

**目标:** 补到 90% ≈ 还需要:
- ❌ 美颜(1 天)
- ❌ AI 智能去水词(2 天)
- ❌ AI 改词翻唱(2 天)
- ❌ AI 一键成片(3 天)
- ❌ AI 转场(1 天)
- ⚠️ 抠像补全(1 天)
- ⚠️ HDR 完善(1 天)
- ⚠️ AI 翻译 API 完整实现(2 天)
- ⚠️ 数字人 API 完整实现(2 天)
- ⚠️ 文字成片 API 完整实现(2 天)

**总计:** ~15-20 天

### 3.4 "骨架 90%"缺口

骨架层还有些没补:
- **错误处理 12 个脚本没 try/except** —— 加 1 天
- **单元测试** —— 加 2-3 天
- **CI/打包** —— 加 1-2 天
- **日志系统**(现在的 print 太简陋) —— 加 1 天

**总计:** 5-7 天

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

(普通用户用 `mklink /J` 不需要管理员,但 `mklink /D` 符号链接需要)

### 5.2 Mavis 验证

```bash
mavis skill list 2>&1 | Select-String "智剪工坊"
mavis skill show 智剪工坊
```

应该看到:
- `name: 智剪工坊`
- 触发词包含"剪辑/转场/调色/智剪工坊"
- location 在 junction 路径

---

## 6. 立即可做(下个 session 第一件事)

### 6.1 工作流

新 session 看到这条消息后的工作流:
1. 读 `智剪工坊/HANDOFF.md`(本文件)
2. 读 `智剪工坊/SKILL.md`
3. 读 `智剪工坊/CHANGELOG.md`
4. 读 `智剪工坊/docs/FEATURE_COMPARISON.md`
5. 读 `智剪工坊/docs/GETTING_STARTED.md`
6. 跑 `verify.py`(待写)确认环境
7. 询问用户先做哪个:`setup 脚本 / verify 脚本 / 美颜 / AI 去水词 / 文字成片 API ...`

### 6.2 第一句问候(参考)

新 session 可以这样问候用户:

> "帅猎羽,看到 HANDO 了。智剪工坊骨架 100% 写完,但要"可发布+90% 对标剪映"还差 ~20 天的工作。我建议这么排优先级:
> 1. setup 脚本 + verify 脚本(让任何人都能装上用)
> 2. 美颜 + AI 去水词 + AI 改词翻唱(剪映特色,补齐对标)
> 3. API 集成(文字成片/数字人/翻译,要用户填 key)
> 4. 错误处理 + 单元测试
>
> 你想先做哪块?"

---

## 7. 已有文件(下个 session 不要重新写)

```
D:\2Study\StudyNotes\SKILLS\智剪工坊\
├── SKILL.md                          ← 主入口(已识别)
├── README.md                         ← 架构说明
├── requirements.txt                  ← 依赖清单
├── CHANGELOG.md                      ← v0.1 版本日志
├── HANDOFF.md                        ← 本文件
├── lib/
│   └── common.py                     ← 公共库(ffmpeg + 错误处理)
├── scripts/                          ← 26 个 Python 脚本
│   ├── cut.py / xfade.py / bgm_loop.py / cover_ai.py / pipeline_vlog.py
│   ├── reverse.py / speed.py / overlay.py / mask.py
│   ├── voice_change.py / color_style.py / beat_sync.py
│   ├── auto_subtitle.py / scene_detect.py / fx.py
│   ├── hdr_io.py / reframe.py / keyframe.py / multicam.py / style_transfer.py
│   ├── batch.py / quotes.py / cutout.py
│   ├── text_to_video.py / digital_human.py / translate.py
│   └── README.md
├── references/                       ← 11 个子技能文档
│   └── 01-cutting.md ... 11-pipelines.md
├── docs/
│   ├── GETTING_STARTED.md
│   ├── VS_JIANYING.md
│   ├── FAQ.md
│   └── FEATURE_COMPARISON.md         ← vs 剪映/Pr/Resolve/FCP 对比
└── assets/
    ├── fonts/  luts/  templates/  test_videos/  README.md
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

如果下个 session 出现关键 bug(比如 8 小时视频、NVENC 崩溃、AI 中文乱码),回看:
- §2 关键 Bug 教训
- §1.3 路径信息
- §4.3 关键命令模板

不要瞎试,先看历史方案。

---

**祝下个 session 顺利。** —— 2026-07-03 13:32 当前 session 留
