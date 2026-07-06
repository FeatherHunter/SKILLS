# 04-cut - 时间裁剪（v1.3 multi-range 已实现）

> **对应脚本**: `lib/processing.py build_video_filter` / `build_cut_middle_filter` / `_build_pin_range_multi_filter`
> **触发词**: "剪头"、"剪尾"、"保留某段"、"切掉中间"、"trim"、"cut"、"pin"、"clip"、"去掉广告片段"
> **实测状态**: ✅ 验证通过（v1.3 10 场景严格测试 0 偏差）

---

## 1. 4 个 op 速查

| op 名 | 含义 | 路由 | 简单示例 |
|---|---|---|---|
| `trim-head` | 剪头 N 秒 | `processing.py build_video_filter` | `{on: true, sec: 3}` |
| `trim-tail` | 剪尾 N 秒 | `processing.py build_video_filter` | `{on: true, sec: 2}` |
| `pin-range` | 强制保留某段时间 | `processing.py build_video_filter` | `{on: true, from: "00:00:05", to: "00:00:10"}` |
| `cut-middle` | 切掉中间某段 | `processing.py build_cut_middle_filter` | `{on: true, from: "00:00:05", to: "00:00:10"}` |

## 2. pin-range / cut-middle multi-range（v1.3 新增）

### 单段（向后兼容 v1.2）

```json
{"on": true, "from": "00:00:05", "to": "00:00:10"}
```

### 多段（v1.3 新增）

```json
{
  "on": true,
  "ranges": [
    {"from": "00:00:05", "to": "00:00:10"},
    {"from": "00:00:20", "to": "00:00:25"}
  ]
}
```

### 行为差异

- **`pin-range` multi-range**：保留所有列出的段，concat 起来
- **`cut-middle` multi-range**：切掉所有列出的段，剩余的 concat 起来

### 自动优化

- 段列表自动按 `from` 排序（无需用户排好序）
- 相邻 / 重叠的段自动合并：
  - `[5,10]+[10,15]` → `[5,15]`（相邻）
  - `[5,15]+[10,20]` → `[5,20]`（重叠）

## 3. 严格测试已通过（10 场景 0 偏差 0.00s）

| 场景 | cut-middle 输出 | pin-range 输出 |
|---|---|---|
| 单段 [5,10] | 25.0s | 5.0s |
| 多段 [5,10]+[15,20] | 20.0s | 10.0s |
| 交叉 [5,15]+[10,20] | 15.0s（合并） | 15.0s（合并）|
| 相邻 [5,10]+[10,15] | 20.0s（合并） | — |
| 无序 [15,20]+[5,10] | 20.0s（自动排序）| — |
| 三段 [3,5]+[10,12]+[20,25] | 21.0s | 10.0s |

测试方法: 用 30s 测试视频,严格隔离测试每种场景的输出时长。

## 4. 时间格式

`from` / `to` 接受多种格式（`parse_time` 自动识别）:

- `HH:MM:SS` — `"00:00:05"` / `"1:30:00"`
- `MM:SS` — `"05:10"` / `"1:30"`
- `"5分30秒"` / `"5分"` — 中文
- `"1.5分钟"` / `"1.5 min"` — 浮点分钟
- 纯数字 — 视为秒

## 5. AI 编排要点

- **AI 必读**: 看到 `pin-range` / `cut-middle` 时,先看 `ranges` 字段,有则 multi-range,无则 fallback `from/to`
- **多段拼接需要 concat**: 用了 multi-range 后,filter 必须用 concat 输出,不再是单 trim
- **时间合法性**: `end > start`（pin-range 失败时 fallback `end=start+1`）
- **cut-middle 不允许 cut 全部**: 若 cuts 覆盖整段视频,会返回 None（ffmpeg 不会跑）

## 6. 实际测试命令

```python
# cut-middle 多段
from processing import build_cut_middle_filter
fc, mappings = build_cut_middle_filter({
    'on': True,
    'ranges': [
        {'from': '00:00:05', 'to': '00:00:10'},
        {'from': '00:00:15', 'to': '00:00:20'},
    ]
}, 640, 360, aspect_handling='aspect-fit')

# pin-range 多段
from processing import build_video_filter
fc, mappings = build_video_filter({
    'pin-range': {
        'on': True,
        'ranges': [
            {'from': '00:00:05', 'to': '00:00:10'},
            {'from': '00:00:20', 'to': '00:00:25'},
        ]
    }
}, 'keep', input_duration=30, target_aspect='16:9', aspect_handling='aspect-fit')
```

## 7. 相关参考

- **SKILL.md §G.1**: video 级 ops 速查表
- **SKILL.md 路由表**: pin-range / cut-middle 字段定义
- **references/03-stages.md**: 阶段 2 视频处理流程
