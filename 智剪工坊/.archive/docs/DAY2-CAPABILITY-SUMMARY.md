# DAY2 实战能力总结 — 从 vlog 制作提炼可复用工具

> **来源**：DAY2 vlog 制作实战（2026-07-04 ~ 07-05）
> **目的**：把今天用到的所有"AI 辅助音频处理"能力沉淀为通用 CLI 工具设计 + 经验教训
> **范围**：闹钟铃声 / BGM 生成与混合到视频的完整链路

---

## 0. 今日时间线速览

| 时段 | 任务 | 产物 |
|---|---|---|
| 18:56 起 | 视频拼接、Stage 4 ending、vlog_final.mp4 落盘 | v1 完整版（4:21 / 无 BGM / 无闹钟） |
| 23:53 | 用户提需求：在素材目录生成闹钟铃声 | 目录创建 + v1 电子 chime |
| 23:58 | 改方向 C：原声吉他 + 鸟鸣 | v2 自然治愈（126.6s） |
| 00:04 | 用户确认 V2 音色 OK + 闹钟作为"假闹铃" | alarm_bell_v2_loop4s.mp3 |
| 00:08 | 用户选定 2:34-3:31 用 demo B 都市 LoFi | demo B 37s 太短，重生成 |
| 00:11 | 用户指出"音乐有些短了" | 重生成 3 个延长版，v1 64.94s OK |
| 00:17 | 用户感觉闹钟 3 秒太短 | 截 v2 完整版 7s 段，重新 mix |
| 00:20 | 完工 + 沉淀本文 | vlog_final_v2.mp4（4:21 / 闹钟 7s + LoFi BGM 57s） |

---

## 1. 今日用到的能力清单（按操作分类）

### A. AI 音乐生成（mmx matrix MCP）

**调用方式**：
```bash
mavis mcp call matrix matrix_batch_text_to_music \
  --file _bgm_request.json
```

**关键参数**：
- `requests[]`：每次最多 5 个
- `prompt`：10-300 字符，必填
- `lyrics`：可选（纯音乐时省略）
- `sample_rate`：16000/24000/32000/**44100**
- `bitrate`：32000/64000/128000/**256000**
- `format`：**mp3** / wav / pcm

**返回**：
- `success_items[].output_url`：CDN URL（早期是本地路径，最近是 https URL）
- **行为变化**：早期版本自动下载到 workspace，最近版本只返回 CDN URL

### B. 音频探测（ffmpeg astats）

**调用方式**：
```bash
ffmpeg -i video.mp4 -af \
  'astats=metadata=1:reset=N,ametadata=print:key=lavfi.astats.Overall.RMS_level' \
  -f null -
```

**用途**：
- 每 N 秒测一次 RMS（dB）
- 找静音段（< -40dB）、小声段、中声段、大声段
- 验证混合后的音量分布

### C. 音频截取（ffmpeg atrim + afade）

**调用方式**：
```bash
ffmpeg -y -i src.mp3 -t 7 \
  -af 'afade=t=out:st=6:d=1' \
  -c:a libmp3lame -q:a 2 dst.mp3
```

**用途**：
- 从长音频取特定时长
- 加淡入淡出（`afade=t=in:st=A:d=B` / `afade=t=out:st=A:d=B`）
- `-q:a 2` 是 VBR 编码，质量≈190kbps

### D. 音频混合到视频（ffmpeg filter_complex）

**调用方式**（核心模板）：
```bash
ffmpeg -y \
  -i video.mp4 \
  -i alarm.mp3 \
  -i bgm.mp3 \
  -filter_complex "
    [0:a]volume=1.0[a0];
    [1:a]volume=1.0[alarm];
    [2:a]volume=0.35,adelay=154000|154000[bgm];
    [a0][alarm][bgm]amix=inputs=3:duration=first:normalize=0[mixed];
    [mixed]alimiter=limit=0.95[out]
  " \
  -map 0:v -map '[out]' \
  -c:v copy -c:a aac -b:a 192k \
  output.mp4
```

**关键参数**：
- `duration=first`：输出长度对齐第一个输入（视频）
- `normalize=0`：禁止 amix 自动归一化（必须！）
- `adelay=N|N`：双声道延迟（N 毫秒）
- `alimiter=limit=0.95`：防削顶

### E. 素材目录管理

**核心规范**（今天确立的）：
- 命名：`{type}_{variant}_{purpose}.mp3`
- 请求参数追溯：`_*.json`
- 归档在 `素材/` 目录

---

## 2. 应该封装成哪些 CLI 工具

### 工具总览

| # | 工具名 | 作用 | 替换当前手动操作 |
|---|---|---|---|
| 1 | `gen_audio.py` | AI 生成音频（mmx）+ 自动归档 | 手动写 JSON + 调 MCP + 移动文件 |
| 2 | `probe_audio.py` | 音频探测（RMS/静音段/音量分布）| 手动写 astats 命令 + 解析输出 |
| 3 | `slice_audio.py` | 截取音频段 + 淡入淡出 | 手动写 atrim + afade |
| 4 | `mix_audio.py` | 多轨音频混合到视频 | 手动写复杂 filter_complex |
| 5 | `asset.py` | 素材目录管理 + 命名规范 | 手动 mv/重命名 |

每个工具的设计：

---

### 2.1 `gen_audio.py` — AI 音频生成 CLI

**接口设计**：
```bash
python scripts/gen_audio.py \
  --prompt "Natural wake-up alarm, acoustic guitar..." \
  --style wake_alarm \
  --tag "v1_electronic" \
  --duration-target 4 \
  --sample-rate 44100 \
  --out 素材/
```

**返回**：
- 归档后的 .mp3 路径
- `_request.json`（追溯参数）
- 时长信息

**核心逻辑**：
1. 读 prompt + 风格
2. 调用 mmx `matrix_batch_text_to_music`
3. 处理返回（本地路径 vs CDN URL）
4. 下载（如果是 CDN）
5. 归档 + 重命名
6. 写 _request.json

**可选增强**：
- `--batch`：一次 N 个变体（用于对比试听）
- `--auto-trim`：自动截取前 N 秒（针对"开场闹钟"场景）
- `--genre wake_alarm | bgm_natural | bgm_lofi | bgm_cinematic`：预设 prompt 模板

---

### 2.2 `probe_audio.py` — 音频探测 CLI

**接口设计**：
```bash
# 默认每 2 秒一次
python scripts/probe_audio.py --input video.mp4

# 自定义采样间隔
python scripts/probe_audio.py --input video.mp4 --reset 5

# 只找静音段
python scripts/probe_audio.py --input video.mp4 --find-silence --threshold -40

# 关键时段验证
python scripts/probe_audio.py --input video.mp4 --check-points 0,4,154,211
```

**返回**：
- 时间线表（time, dB, 等级）
- 静音段时间戳列表
- 关键时段音量快照

**核心逻辑**：
1. 调 ffmpeg astats
2. 解析 stderr（pts_time + RMS_level）
3. 按等级分类（静音/小声/中声/大声）
4. 打印表 / 输出 JSON

---

### 2.3 `slice_audio.py` — 音频截取 CLI

**接口设计**：
```bash
python scripts/slice_audio.py \
  --input alarm_full.mp3 \
  --start 0 --duration 7 \
  --fade-in 0:0.5 \
  --fade-out 6:1 \
  --out alarm_loop7s.mp3
```

**返回**：
- 截取的 .mp3 路径
- 实际时长

**核心逻辑**：
1. atrim 起止时间
2. afade 淡入淡出
3. 编码 libmp3lame q:a=2
4. 验证时长

---

### 2.4 `mix_audio.py` — 多轨音频混合 CLI

**接口设计**：
```bash
python scripts/mix_audio.py \
  --video vlog_final.mp4 \
  --layer "alarm:alarm_7s.mp3:0:7:1.0" \
  --layer "bgm:bgm_57s.mp3:154:57:0.35" \
  --limit 0.95 \
  --output vlog_final_v2.mp4
```

**layer 语法**：`name:file:start_sec:duration_sec:volume`

**返回**：
- 混合后的视频路径
- 各层音量统计

**核心逻辑**：
1. 输入：视频 + 多个 layer
2. 对每 layer：volume + atrim + adelay
3. amix duration=first normalize=0
4. alimiter 防削顶
5. -c:v copy（不重编视频）

---

### 2.5 `asset.py` — 素材目录管理 CLI

**接口设计**：
```bash
# 列出某类素材
python scripts/asset.py list --category alarm
python scripts/asset.py list --category bgm

# 归档新文件（按命名规范）
python scripts/asset.py archive src.mp3 \
  --type alarm_bell --variant v3 --purpose full

# 清理过期/低质量
python scripts/asset.py clean --keep-latest 3

# 追溯
python scripts/asset.py trace alarm_bell_v2
```

---

## 3. 今日踩过的关键坑（必读）

### 3.1 mmx AI 音乐前 0.7s 静音

**现象**：
所有 mmx 生成的音频（无论是 alarm 还是 BGM），开头 0.5-1.0s 都是 -50dB 左右的静音。

**根因**：
模型的"自然淡入"特性，不是 bug。

**影响**：
- 闹钟实际"听感长度"比文件长度短约 0.7s
- 4s 闹钟文件实际听感 ≈ 3.3s
- 7s 闹钟文件实际听感 ≈ 6.3s

**对策**：
- 截取时按"目标听感长度 + 0.7s"预留
- 用户说"3 秒闹钟"时，按 3.7-4.0s 截
- 用户说"7 秒闹钟"时，按 7.5-8.0s 截

**验证命令**：
```bash
ffmpeg -i alarm.mp3 -af 'astats=metadata=1:reset=1,...'
```

---

### 3.2 PowerShell 引号转义陷阱

**现象**：
```powershell
python -c "print(f'{\"时间(s)\":<10}')"
# 报错: The term 's' is not recognized
```

**根因**：
PowerShell 把 `f'{\"时间\"'` 中的 `\"` 解析成了字面字符 `s` + 引号。

**对策**：
**复杂命令一律写到 .py 文件**，然后 `python file.py`：
```bash
# ❌ 错的（PowerShell 里会被拆引号）
python -c "import subprocess; print('{\"key\": 1}')"

# ✅ 对的（写到 _probe.py）
echo 'import subprocess; ...' > _probe.py
python _probe.py
```

**适用范围**：
- 多层嵌套引号
- 长 ffmpeg 命令
- 任何含 JSON 字符串的 Python 调用

---

### 3.3 ffmpeg normalize 默认行为

**现象**：
`amix` 默认 `normalize=1`，会把所有输入按权重归一化，导致单层音量被压低。

**对策**：
**永远显式设置 `normalize=0`**，然后用 `volume=N` 手动控制每层：
```bash
amix=inputs=3:duration=first:normalize=0
```

**配合**：
- `volume=1.0`：原声保持
- `volume=1.0`：闹钟（要盖过原静音段）
- `volume=0.35`：BGM 铺底

---

### 3.4 amix duration=first 关键作用

**现象**：
如果不指定 duration，amix 输出长度 = 最长输入，可能超出视频长度。

**对策**：
**永远用 `duration=first`**，第一个输入放视频：
```bash
[video_audio][alarm][bgm]amix=inputs=3:duration=first:...
```

---

### 3.5 alimiter 防削顶

**现象**：
多轨直接相加（amix normalize=0）可能超过 0dB，导致硬削顶，听感失真。

**对策**：
```bash
[mixed]alimiter=limit=0.95[out]
```

`limit=0.95` 把峰值控制在 -0.45dB 以下，留余量。

---

### 3.6 ffmpeg 路径不在 PATH

**现象**：
```bash
ffprobe -i video.mp4
# 'ffprobe' is not recognized
```

**对策**：
用 `imageio_ffmpeg` 提供的 ffmpeg（Python 包自带二进制）：
```python
FF = r'D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.EXE'
```

或者 `shutil.which('ffmpeg')` 兜底。

---

### 3.7 mmx 返回路径风格变化

**现象**：
- 早期：output_url 直接是本地路径（自动下载到 workspace）
- 最近：output_url 是 https://cdn.hailuoai.com/... CDN URL

**对策**：
工具里写"两种都支持"的下载逻辑：
```python
url = item['output_url']
if url.startswith('http'):
    # CDN 下载
    ...
elif os.path.exists(url):
    # 本地已下载
    ...
```

---

## 4. 素材命名规范（v1 试行）

### 文件命名

```
{type}_{variant}_{purpose}.{ext}
```

| 字段 | 取值 | 示例 |
|---|---|---|
| type | alarm_bell / bgm_demo / bgm_ext / bgm_loop / sfx_* | alarm_bell |
| variant | v1/v2/v3 / A/B/C / 风格名 | v2, 都市LoFi, 自然治愈系 |
| purpose | full / preview_5s / loop7s / 57s / extended | loop7s |
| ext | mp3 / wav | mp3 |

**示例**：
```
alarm_bell_v1_full.mp3              ← v1 完整版
alarm_bell_v1_preview_5s.mp3        ← v1 前 5s 预览
alarm_bell_v2_loop7s.mp3            ← v2 截取 7s 循环段 ← 实际用
bgm_demo_B_都市LoFi.mp3             ← 风格 demo B
bgm_ext_v1_long_lofi_57s.mp3        ← 延长版截 57s ← 实际用
```

### 请求参数追溯

每个生成批次对应一个 `_*.json`：
```
_alarm_v2_request.json               ← alarm v2 的 prompt + 参数
_bgm_style_demos_request.json        ← 3 个风格 demo 的批量参数
_bgm_extended_request.json           ← 延长版的批量参数
```

**JSON 内容**：原始调用 mmx 的 `requests` 数组（含 prompt/lyrics/sample_rate/bitrate/format），可直接重放。

---

## 5. 完整工作流模板（DAY2 实例）

### Phase 0：需求评估

1. 听现有音轨（probe_audio）
2. 找静音段 / 弱声段
3. 评估"需要加什么"

### Phase 1：生成候选

```bash
# 3 个候选风格
python scripts/gen_audio.py \
  --prompt "Lo-fi chill hip-hop..." \
  --style bgm_lofi --variant A --purpose demo
```

### Phase 2：用户试听 + 选定

```bash
python scripts/slice_audio.py \
  --input bgm_demo_A_*.mp3 \
  --duration 30 \
  --out bgm_demo_A_preview.mp3
```

### Phase 3：延长（如果不够长）

不要用 loop —— **直接重生成延长版**：
```bash
python scripts/gen_audio.py \
  --prompt "Long extended lo-fi chill..." \
  --style bgm_lofi --variant B_ext --purpose full
```

筛选（按时长 >= 目标）：
```python
dur = probe_audio(src)
if dur >= target: keep
else: drop
```

### Phase 4：截取 + 淡入淡出

```bash
python scripts/slice_audio.py \
  --input bgm_ext_v1_long_lofi.mp3 \
  --start 0 --duration 57 \
  --fade-in 0:1.5 \
  --fade-out 55.5:1.5 \
  --out bgm_ext_v1_long_lofi_57s.mp3
```

### Phase 5：多轨混合

```bash
python scripts/mix_audio.py \
  --video vlog_final.mp4 \
  --layer "alarm:alarm_bell_v2_loop7s.mp3:0:7:1.0" \
  --layer "bgm:bgm_ext_v1_long_lofi_57s.mp3:154:57:0.35" \
  --output vlog_final_v2.mp4
```

### Phase 6：关键段验证

```bash
# 闹钟段
python scripts/slice_audio.py --input vlog_final_v2.mp4 --start 0 --duration 12 --out verify_alarm_12s.mp3

# BGM 段
python scripts/slice_audio.py --input vlog_final_v2.mp4 --start 150 --duration 65 --out verify_bgm_65s.mp3

# 关键时段音量快照
python scripts/probe_audio.py --input vlog_final_v2.mp4 --check-points 0,4,154,211
```

### Phase 7：交付

- 完整版 mp4 在 `00_智剪/成片/vlog_final_v2.mp4`
- 关键验证段在 `_fix/verify_*.mp3`
- 所有素材归档在 `SKILLS/智剪工坊/素材/`

---

## 6. 与现有 scripts/ 的整合

现有 `scripts/` 已有 38 个工具，本次新增的 5 个工具与它们的关系：

| 新工具 | 现有相关 | 关系 |
|---|---|---|
| `gen_audio.py` | （无） | 新增能力（AI 生成） |
| `probe_audio.py` | `scene_detect.py` | 互补：probe 测音量，scene_detect 测场景切换 |
| `slice_audio.py` | `cut.py` / `xfade.py` | 互补：cut 切视频，slice 切音频 |
| `mix_audio.py` | `bgm_loop.py` / `step3_assemble.py` | 互补：bgm_loop 管 BGM 循环，mix_audio 管多轨混合 |
| `asset.py` | （无） | 新增能力（素材治理） |

**集成建议**：
- `mix_audio.py` 可作为 `step3_assemble.py` 的 audio-only 模式调用
- `bgm_loop.py` 可改用 `gen_audio.py` 生成的素材
- `asset.py` 可作为所有 scripts 的前置依赖（统一命名）

---

## 7. 优先级建议

按"复用价值 × 实现成本"排序：

| 优先级 | 工具 | 理由 |
|---|---|---|
| 🔴 P0 | `gen_audio.py` | 用 mmx 必封装；下次 vlog 必用 |
| 🔴 P0 | `mix_audio.py` | vlog 完结必用；filter_complex 太复杂 |
| 🟡 P1 | `probe_audio.py` | 验证必备；现在每次都要手写 astats |
| 🟡 P1 | `slice_audio.py` | 闹钟/BGM 截取必用 |
| 🟢 P2 | `asset.py` | 长期价值；现在素材还少，手动也能管 |

---

## 8. 跨项目注意

这套工具本质是"音频处理"通用能力，不限于 vlog：
- 任何 AI 生成音乐场景都可用（podcast 配乐、解说视频、ASMR）
- 任何"原视频 + 多音轨混合"场景都可用
- 命名规范可复用到其他 SKILL（卡片记账有类似命名规范问题）

如果其他 SKILL（卡路里 / 居家管家 / 学习规划师）有"AI 生成音频"需求，可直接复用 `gen_audio.py` + `slice_audio.py`。

---

## 9. 待办

- [ ] 实现 `gen_audio.py` + `mix_audio.py`（P0）
- [ ] 实现 `probe_audio.py` + `slice_audio.py`（P1）
- [ ] 在 README.md 中标注本文档
- [ ] 在 CHANGELOG.md 记录本次新增 references
- [ ] 下一部 vlog (DAY3) 实战验证

---

**作者**：DAY2 实战沉淀
**对应代码版本**：vlog_final_v2.mp4
**文档位置**：`D:\2Study\StudyNotes\SKILLS\智剪工坊\docs\DAY2-CAPABILITY-SUMMARY.md`