# 封面合成 changelog

## v1.0 (2026-07-15)

### 初版

**来源**:从智剪工坊 DAY14 封面处理的 16 个真实踩坑提取

**踩坑史**(DAY14 封面处理):
1. 旋转图片的角是黑色实色(RGB rotate 填充黑色)
2. alpha 羽化后边缘有半透明黑
3. shadow 扩散造成画布上方半透明黑叠加
4. 画布 RGB 转 RGBA 时 alpha 默认 255 不透明
5. JPG 保存 RGBA 丢失 alpha
6. 旋转角刚好是黑色实色而非透明
7. PIL rotate 抗锯齿产生 alpha 中间值
8. shadow offset (12,12) 单边阴影视觉不对称
9. 不显式 z-order 导致谁覆盖谁不确定
10. 文字无黑色描边在亮色照片上读不清
11. 重复缩小主图导致主图消失
12. 4:3 安全区在 9:16 / 16:9 画布上不一致
13. RGB 转 RGBA 后 fill 非黑
14. 字号过大撑爆 4:3 安全区
15. JPG 不支持 alpha → 透明失效
16. 旋转后没 diagnose 半透明黑,用户反馈才发现

**实现的核心函数**:
- `rotate_hard(path, w, h, angle)` — 7 步硬旋转(临时大画布 → rotate → crop bbox → 二值化)
- `binarize_alpha(rgba)` — alpha 二值化(>128 → 255)
- `text_layer(canvas, content, position, ...)` — 文字 + 黑色描边
- `fit_text_to_area()` — 字号自动适配
- `symmetric-cascade` layout — 主图 + 左右副图,镜像对称
- `diagnose` 子命令 — 扫半透明黑 / 暗区 / 对称

**5 层架构落地**:
- ① 文档:SKILL.md + HTML + changelog + references/
- ② 契约:scripts/cli.py argparse,统一 JSON 输出
- ③ 业务:scripts/compose.py + layout.py + layers.py + text.py + diagnose.py + presets.py + validators.py
- ④ 数据:lib/canvas.py + lib/diagnostics.py + lib/presets_data.py
- ⑤ 集成:status/error 标准 JSON,供其它 Skill 调用

**4 个 layout**:
- symmetric-cascade(默认,镜像对称,适合主图+左右副图)
- cascade(主图 + 副图堆叠,右下偏移)
- polaroid(主图中央,副图四角散落)
- grid(网格平铺)

**3 个 CLI 子命令**:
- compose:合成封面
- diagnose:诊断图片问题(半透明黑/暗区/对称)
- presets:查询平台/比例预设