# text 子命令(策划中)

> 文字水印目前集成在 `compose` 子命令里,通过 `--text` JSON 配置。
> 未来如果需要"独立 draw_text 工具"再拆出来。

## 当前用法

文字作为 compose 流程的一部分:

```bash
封面合成 compose \
  --text '{"main":"14 天","sub":"-7 斤","tags":"腰突"}' \
  ...
```

详见 SKILL.md §② `--text` 两种格式。

## 文字 9 宫格位置

`top-left` / `top-center` / `top-right`
`middle-left` / `middle-center` / `middle-right`
`bottom-left` / `bottom-center` / `bottom-right`

## 字号经验值(1920×1080 16:9 画布)

- 主标(钩子):200-300
- 副标:80-150
- 标签:40-70

## 防 #10 必加描边

每条文字都自带黑色描边(stroke_fill=(0,0,0), stroke_width=字号×5%),否则在亮色照片背景上读不清。

如果想自定义颜色,完整格式的 JSON:
```json
{
  "lines": [
    {
      "text": "14 天",
      "position": "middle-center",
      "size": 200,
      "font_color": [255, 215, 0],
      "outline_color": [0, 0, 0],
      "outline_width": 8
    }
  ]
}
```