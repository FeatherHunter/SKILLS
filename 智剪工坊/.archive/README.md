# 智剪工坊

> **代码视频剪辑工作台,对标剪映(图形化)+ 扩展(AI 能力)**
>
> 🎬 一行命令做剪切/转场/调色/字幕/AI 封面,任何视频自动化流水线

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)]()
[![ffmpeg](https://img.shields.io/badge/ffmpeg-required-green)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

---

## 3 分钟跑通你的第一个视频

### 1. 装(Windows / Mac / Linux)

```bash
# Windows
setup.bat

# Mac / Linux
bash setup.sh
```

脚本会自动:
- 装 Python 依赖(清华源,国内快)
- 装 ffmpeg(`imageio-ffmpeg` 自带,免手动下)
- 创建目录结构
- 写 `config.json`(记录 ffmpeg 路径)
- 跑 `verify.py` 确认环境

### 2. 验证

```bash
python verify.py
```

应该看到 `26/26 脚本导入通过` 和 `6/6 冒烟测试通过`。第一次装会下一些模型,稍等。

### 3. 跑一个剪切

```bash
# Windows
python scripts\cut.py trim --input your_video.mp4 --ss 30 --t 60 --output out.mp4

# Mac/Linux
python3 scripts/cut.py trim --input your_video.mp4 --ss 30 --t 60 --output out.mp4
```

🎉 完事。

---

## 26 个子技能速查

| 类别 | 脚本 | 一句话 |
|---|---|---|
| **核心 5** | `cut.py` | 剪切 + 拼接,统一 1080x1920 + 30fps |
|  | `xfade.py` | 60+ 种转场(超过剪映 30 种) |
|  | `bgm_loop.py` | BGM 循环混音(自动 loop + 音量) |
|  | `cover_ai.py` | AI 生图封面 + 中文叠字(两步法) |
|  | `pipeline_vlog.py` | 7 步完整 vlog 流水线 |
| **基础效果** | `reverse.py` | 倒放(视频+音频) |
|  | `speed.py` | 0.2-100x 变速 |
|  | `overlay.py` | 画中画(多图层) |
|  | `mask.py` | 蒙版(矩形/圆形/自定义) |
|  | `voice_change.py` | 7 种变声(男女/童声/机器人) |
|  | `color_style.py` | 13 种风格调色(warm/cool/cinematic) |
|  | `beat_sync.py` | 节拍卡点(自动切到 beat) |
| **进阶** | `auto_subtitle.py` | Whisper 自动字幕(27 语) |
|  | `scene_detect.py` | 智能场景检测(帧差) |
|  | `fx.py` | 视觉特效(blur/glow/glitch/...) |
|  | `hdr_io.py` | HDR 导入/导出 |
|  | `reframe.py` | 自动重新构图(人脸优先) |
|  | `keyframe.py` | 关键帧动画 + 曲线 |
|  | `multicam.py` | 多机位剪辑(4 路 sync) |
|  | `style_transfer.py` | 风格迁移(油画/动漫/...)| |
| **批量** | `batch.py` | 批量处理(100 视频并发) |
|  | `quotes.py` | 金句检测(Whisper + NLP) |
|  | `cutout.py` | AI 抠图(rembg) |
| **战略** | `text_to_video.py` | AI 文字成片(可灵/Vidu) |
|  | `digital_human.py` | AI 数字人 |
|  | `translate.py` | 视频翻译(转录→翻译→TTS) |

每个脚本都支持 `--help` 看具体参数。

---

## 常用工作流

### A. 完整 vlog 一条龙(7 步)

```bash
python scripts/pipeline_vlog.py run \
  --input videos/ --output day1/ \
  --theme "Day 1" --bgm bgm.mp3
```

自动跑:降分辨率 → Whisper 转录 → 抽关键帧 → AI 建议 → 拼接 → 烧字幕 → AI 封面

### B. 视频加 BGM

```bash
python scripts/bgm_loop.py --video vlog.mp4 --bgm bgm.mp3 --volume 0.18 --out vlog_bgm.mp4
```

### C. 批量加转场(20 个视频一次过)

```bash
python scripts/batch.py xfade --input videos/ --output joined/ --type fade --duration 1
```

### D. AI 改字幕风格

```bash
python scripts/auto_subtitle.py --input vlog.mp4 --style cinematic --output subtitled.mp4
```

### E. 视频翻译(中→英)

```bash
python scripts/translate.py --input chinese.mp4 --target-lang en --output english.mp4
```

---

## 架构

```
智剪工坊/
├── SKILL.md                 # Mavis 入口(主技能)
├── README.md                # 本文件
├── HANDOFF.md               # Session 交接文档
├── CHANGELOG.md             # 版本日志
├── requirements.txt         # 依赖清单
├── setup.bat / setup.sh     # 一键安装(Win/Mac/Linux)
├── verify.py                # 环境验证(5 秒快检 / 2 分钟全检)
├── config.json              # 自动生成的 ffmpeg 路径配置
│
├── lib/
│   └── common.py            # 公共库(ffmpeg 包装 + 友好错误)
│
├── scripts/                 # 26 个原子子技能
│   ├── cut.py / xfade.py / ...
│
├── references/              # 11 个子技能详细文档
│   ├── 01-cutting.md
│   ├── 02-transitions.md
│   ├── ...
│
├── docs/                    # 产品文档
│   ├── GETTING_STARTED.md   # 新手引导
│   ├── FEATURE_COMPARISON.md # vs 剪映/Pr/Resolve 对比
│   ├── FAQ.md               # 常见问题
│   └── VS_JIANYING.md       # 剪映 vs 智剪工坊
│
└── assets/                  # 资源
    ├── fonts/               # 字体
    ├── luts/                # 调色预设
    ├── templates/           # 模板
    ├── test_videos/         # 测试视频
    ├── output/              # 默认输出
    └── cache/               # 缓存(rembg 模型等)
```

---

## 输出规格(默认)

| 项 | 值 | 备注 |
|---|---|---|
| 分辨率 | 1080x1920 | 竖屏 vlog,加黑边保持比例 |
| 帧率 | 30 fps | 强制统一(避免 8 小时视频 bug) |
| 视频编码 | libx264 | CPU 编码,稳定 |
| 质量 | crf=20 | 视觉无损,文件 1-2MB/分钟 |
| 音频 | aac 128k | 通用兼容 |
| 容器 | MP4 + faststart | 网络播放优化 |

要改:传 `--resolution 1920x1080 --fps 60 --crf 18`

---

## 关键技术决策(为啥这样设计)

| 决策 | 理由 |
|---|---|
| **libx264 而不是 NVENC** | NVENC 在某些场景随机崩(Access Violation),libx264 稳 |
| **强制 30fps** | 不同 fps 拼接会算出 8 小时视频(血的教训) |
| **AI 生图两步法** | matrix 生图对中文/数字支持差(90% 渲染错),先生成视觉再 PIL 叠字 |
| **imageio_ffmpeg** | 自动装 ffmpeg,免用户手动下(尤其 Windows) |
| **清华 pip 源** | 国内 10x 快 |
| **subprocess + importlib** | 不用 ffmpeg-python / moviepy,依赖少,稳 |

---

## FAQ(常见问题)

### Q1: 报错"找不到 ffmpeg"?

跑 `setup.bat` / `setup.sh` 装 `imageio-ffmpeg`(自带 ffmpeg)。或手动下载放 PATH:https://ffmpeg.org/download.html

### Q2: 报错"Access Violation 0xC0000005"?

NVENC 崩溃。所有脚本默认用 `libx264`,确认参数里没自己加 `-c:v h264_nvenc`。

### Q3: 视频时长变 8 小时?

帧率不一致 bug!确认用了 `unified_vf("1080:1920", 30)`,强制 30fps。

### Q4: 字幕显示方框/乱码?

字体问题。
- Windows:确认 `C:\Windows\Fonts\msyh.ttc` 存在
- Mac:PingFang SC 自带
- Linux:`sudo apt install fonts-noto-cjk`

### Q5: AI 生图中文奇怪?

训练数据里中文/数字少,直接生成 90% 错。改用两步法(先生成视觉,后用 PIL 叠字)——`cover_ai.py` 已用此方案。

### Q6: 处理太慢?

- 改 `crf=23`(质量略低,快 30%)
- 用 `libx264 -preset ultrafast`
- 降分辨率到 720p

### Q7: 怎么接 matrix AI?

matrix MCP 已在 Mavis daemon 里,直接 `mavis mcp call matrix matrix_generate_image` 即可。

### Q8: 怎么加新功能?

子技能粒度:每个原子能力 = 一个脚本。参考 `references/01-cutting.md` 写一个新脚本,import `lib/common` 复用 ffmpeg 包装 + 错误处理。

更多问题见 [docs/FAQ.md](docs/FAQ.md)。

---

## 性能参考(1080x1920 30fps)

| 操作 | 时长 | CPU 占用 |
|---|---|---|
| 剪切(cut) | 3s 视频 → 0.5s | 30% |
| 转场(xfade) | 5s + 5s → 0.8s | 40% |
| 调色(color_style) | 3s → 0.6s | 35% |
| 倒放(reverse) | 3s → 0.3s | 30% |
| AI 抠图(cutout) | 3s → 4-6s | 60%(下模型) |
| Whisper 转录 | 1 分钟音频 → 5-15s | GPU 加速 5x |

GPU 用 `h264_nvenc` 可提速 5x,但不稳定。日常推荐 libx264 + `-preset medium`。

---

## License

MIT

---

## 路线图

- [x] v0.1 骨架完成(26 脚本)
- [x] v0.2 可发布版本(setup/verify/友好错误/README) ← 你在这
- [ ] v0.3 美颜 / AI 去水词 / AI 改词翻唱
- [ ] v0.4 AI 一键成片 / AI 转场
- [ ] v0.5 单元测试 + CI + 打包
- [ ] v1.0 90% 对标剪映 + 战略差异(批量 + AI)

---

**🎬 让视频剪辑像写 Python 一样自然。**
