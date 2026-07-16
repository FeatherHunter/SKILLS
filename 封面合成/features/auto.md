# auto 子命令(智能挡)

> 详见 SKILL.md §双层 API 设计。

## 核心概念

`auto` 是 `compose` 的**智能挡**:用户只传 `--photos`,AI 自动分析图片决定 layout/aspect/bg/text,然后调基础 API `compose()` 执行。

```
用户传 --photos
    ↓
[auto_compose.analyze]  读每张图(尺寸/方向/主色/亮度)
    ↓
[auto_compose.decide]   决策:layout/aspect/bg/text
    ↓
[core.compose]           1 个基础 API 落地
    ↓
输出 cover.jpg
```

## 用法

```bash
# 最简单:只传照片
封面合成 auto --photos a.jpg b.jpg c.jpg -o cover.jpg

# 加 hint(字符串当主标题)
封面合成 auto --photos a.jpg b.jpg c.jpg --hint "14 天" -o cover.jpg

# 加 hint(JSON 完整文字)
封面合成 auto --photos a.jpg b.jpg c.jpg \
  --hint '{"main":"14 天","sub":"-7 斤","tags":"腰突"}' \
  -o cover.jpg
```

## 决策逻辑

| 项 | 规则 |
|---|---|
| layout | 1 张 → cascade<br>2-3 张 → symmetric-cascade<br>4+ 张 → polaroid(除非全 square 改 grid) |
| aspect | 全 portrait → 9:16<br>全 landscape → 16:9<br>混合 → 16:9 |
| bg | 主图 brightness > 128 → 用主图主色<br>否则 → 纯黑 #000000 |
| text | hint=str → hint 当主标题<br>hint=dict → 用 hint 完整文字<br>hint=None → 从主图文件名提取 |

## 输出会多一个 decisions 字段(自动挡特供)

```json
{
  "status": "warn",
  "data": { "path": "cover.jpg", "size": [1080, 1920], ... },
  "decisions": {
    "layout": "symmetric-cascade",
    "aspect": "9:16",
    "bg": "#000000",
    "text": {"main": "IMG", "sub": "", "tags": ""},
    "reasons": {
      "layout": "根据 3 张图自动选 symmetric-cascade",
      "aspect": "主图 portrait → 9:16",
      "bg": "主图 brightness=112, contrast=60"
    }
  },
  "warnings": [...],
  "message": "合成完成:共 3 个图层"
}
```

`decisions` 字段告诉 AI "我为啥选这些",便于诊断和后续调整。

## 与 compose 的区别

| | compose(手动挡) | auto(自动挡) |
|---|---|---|
| 用户输入 | layout + aspect + text + bg | 只 photos |
| 决策权 | 用户 | AI(用图片特征自动决策) |
| 输出 | 同样 status/data/warnings | 多 decisions 字段 |
| 精确度 | 100% 控制 | "80% 智能" 足够好,特殊场景可手动调 |

## 跟基础 API 的关系

`auto` 是 `compose` 的**包装**,不直接调 layers/text/layout。  
依赖方向:`operations → core → infra`(只能向下)。  
所以 `auto` 改 layout 算法不会影响基础 API 行为,反之亦然。