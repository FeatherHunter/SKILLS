# requests_4scenes 状态

`_meta_prompts_unproduced.json` 内保存了 4 个场景 BGM 的原始 matrix 请求:

| # | 场景 | 风格 | BPM | 状态 |
|---|------|------|-----|------|
| 1 | 晨起唤醒 | acoustic + bird chirping | 95 | ❌ 未产出 mp3 |
| 2 | 城市通勤 | acoustic arpeggio + ambient | 100 | ❌ 未产出 mp3 |
| 3 | 健身房训练 | acoustic + synth + pulse | 110 | ❌ 未产出 mp3 |
| 4 | 结尾总结 | acoustic + strings + reverb | 95 | ❌ 未产出 mp3 |

## 重跑方法

```bash
# 把 _meta_prompts_unproduced.json 的 requests 数组拆成 4 个单请求文件,
# 分别喂给 matrix MCP:
mavis mcp call matrix matrix_synthesize_speech --file request_1_morning.json --output out_1.mp3
mavis mcp call matrix matrix_synthesize_speech --file request_2_commute.json --output out_2.mp3
...

# 生成的 mp3 放回本目录,用规范命名:
# bgm_4scene_morning_acoustic_95bpm.mp3
# bgm_4scene_commute_acoustic_100bpm.mp3
# bgm_4scene_gym_acoustic_110bpm.mp3
# bgm_4scene_ending_acoustic_95bpm.mp3
```
