# 智剪工坊 · 素材库索引

> **约定**: `音频命名规范` `{category}_{variant}_{style}_{bpm}{_modifier}.mp3`
> 所有 mp3 都是 matrix MCP 生成,可随时重新生成(用同目录的 `_meta*.json` 作为请求模板)。
> 修改 prompt 后请同步更新 `_meta*.json` 与本 README。

---

## 📂 目录结构(按用途分)

| 子目录 | 用途 | 主要调用场景 |
|---|---|---|
| `alarm_v1_electronic/` | 唤醒/闹钟铃声(2 个版本) | 视频开头唤醒、起床场景 |
| `bgm_demo_style/` | 3 种风格 demo (A/B/C) | 给用户挑风格的试听集 |
| `bgm_lofi_extended/` | Lo-Fi 长版变体(4 段) | 通勤/训练/工作场景 |
| `bgm_fitness/` | 健身主题 8 首(已标准化) | 健身 vlog 配乐 |
| `requests_4scenes/` | 4 场景 BGM **请求存档(未产 mp3)** | 如需可用 `_meta_prompts_unproduced.json` 重新生成 |

---

## 🎵 1. `alarm_v1_electronic/` — 唤醒/闹钟铃声

| 文件 | BPM | 风格 | 时长 | 用法 |
|---|---|---|---|---|
| `bgm_alarm_v1_electronic_120bpm.mp3` | 120 | 合成器 + 明亮铃声 | 完整版 | 唤醒主题、晨间视频 |
| `bgm_alarm_v1_electronic_120bpm_preview_5s.mp3` | 120 | 同上 | 5s 预览 | 不听完整先预览 |
| `bgm_alarm_v2_natural_110bpm.mp3` | 110 | 木吉他 + 鸟鸣 | 完整版 | 自然风格唤醒 |
| `bgm_alarm_v2_natural_110bpm_preview_5s.mp3` | 110 | 同上 | 5s 预览 | 同上 |
| `bgm_alarm_v2_natural_110bpm_loop_4s.mp3` | 110 | 同上 | 4s 循环 | 短循环素材 |
| `bgm_alarm_v2_natural_110bpm_loop_7s.mp3` | 110 | 同上 | 7s 循环 | 中循环素材 |

`_meta_v1_prompt.json` / `_meta_v2_prompt.json` — 完整 matrix 请求模板。

---

## 🎵 2. `bgm_demo_style/` — 3 种风格试听集

| 文件 | 风格 | BPM | 适合场景 |
|---|---|---|---|
| `bgm_demo_A_自然_acoustic_95bpm.mp3` | 🌿 自然治愈(木吉他 + 鸟声 + pad) | 95 | 晨间 / 安静 / 户外 |
| `bgm_demo_B_都市_lofi_85bpm.mp3` | 🏙 都市 Lo-Fi(钢琴 + vinyl + 鼓) | 85 | 通勤 / 都市日常 |
| `bgm_demo_C_电影_cinematic_80bpm.mp3` | 🎬 电影叙事(钢琴 + 弦乐 + ambient) | 80 | 叙事 / 收尾 / 情绪铺陈 |

`_meta_prompts.json` — 3 个完整 prompt 模板。

---

## 🎵 3. `bgm_lofi_extended/` — 长版 Lo-Fi

| 文件 | 风格 | BPM | 时长 |
|---|---|---|---|
| `bgm_lofi_extended_v1_long_90bpm.mp3` | 完整 Lo-Fi 曲目 | 90 | 长(主力) |
| `bgm_lofi_extended_v1_57s_90bpm.mp3` | 同 v1 截短版 | 90 | ~57s(轻量版) |
| `bgm_lofi_extended_v2_95bpm.mp3` | 街拍/健身感 | 95 | 中等 |
| `bgm_lofi_extended_v3_continuous_90bpm.mp3` | 连贯循环 Lo-Fi | 90 | 长(无缝 loop) |

`_meta_prompts.json` — 3 个 prompt 模板。

---

## 🎵 4. `bgm_fitness/` — 健身主题(已标准化)

8 首电子/嘻哈风,**按 BPM 排序**:

| 文件 | BPM | 风格标签 |
|---|---|---|
| `bgm_05_futurehouse_126.mp3` | 126 | Future House |
| `bgm_01_bigroom_128.mp3` | 128 | Bigroom |
| `bgm_07_trance_138.mp3` | 138 | Trance |
| `bgm_06_mdubstep_140.mp3` | 140 | Midtempo Dubstep |
| `bgm_02_phonk_140.mp3` | 140 | Phonk |
| `bgm_fitness_03_trapgym_140.mp3` | 140 | Trap Gym |
| `bgm_fitness_04_hardstyle_150.mp3` | 150 | Hardstyle |
| `bgm_fitness_08_epiccinematic_100.mp3` | 100 | Epic Cinematic |

> ⚠️ 历史命名不规范(部分还叫 `bgm_fitness_03_*`,部分叫 `bgm_01_*`),未来重命名时统一 `bgm_fitness_<序号>_<风格>_<bpm>.mp3`。

---

## ⚠️ 5. `requests_4scenes/` — **未产出存档**(纯历史)

`_meta_prompts_unproduced.json` 内有 4 个场景的完整 prompt:
1. 晨起场景 (acoustic 95 BPM)
2. 通勤场景 (acoustic 100 BPM)
3. 训练场景 (acoustic + synth 110 BPM)
4. 结尾总结 (acoustic + strings 95 BPM)

**这 4 个请求从未生成对应 mp3**(只有 prompt 留存)。如需使用:
```bash
# 直接重提请求(把 json 里的 content 喂给 matrix MCP)即可
mavis mcp call matrix matrix_synthesize_speech --file prompt.json
```

---

## 📐 命名规范(新增/修改素材时遵守)

```
{category}_{variant}_{style}_{bpm}[_{modifier}].mp3
```

| 段 | 含义 | 示例 |
|---|---|---|
| `category` | 用途大类 | `bgm_alarm` / `bgm_demo` / `bgm_lofi` / `bgm_fitness` |
| `variant` | 版本号(v1/v2/v3/A/B/C) | `v1` / `A` |
| `style` | 风格标签(英文短) | `electronic` / `natural` / `lofi` / `cinematic` |
| `bpm` | 数字 BPM | `120` / `95` |
| `modifier` | 变种修饰(可选) | `preview_5s` / `loop_4s` / `long` / `continuous` |

---

## 🔄 维护

- **生成新 BGM** → 用同目录 `_meta*.json` 作为请求模板 → 落地命名按上规范 → 在本 README 加一行
- **需要重新生成** → 跑对应 `_meta*.json` 提示词(matrix MCP)
- **复用约定** → `scripts/audio/mix.py --bgm` 直接引用绝对路径即可(如 `素材/bgm_demo_style/bgm_demo_A_自然_acoustic_95bpm.mp3`)
