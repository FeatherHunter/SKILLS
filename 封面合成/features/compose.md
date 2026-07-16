# compose 子命令

> 详见 SKILL.md §② 契约层,这里只放实战 cheatsheet。

## 最常用 3 个配方

### 1. 抖音 vlog 封面(DAY14 真实场景)

```bash
封面合成 compose \
  --photos ~/DAY14/汉堡特写.jpg ~/DAY14/吃包.jpg ~/DAY14/健身房.jpg \
  --layout symmetric-cascade \
  --aspect 9:16 \
  --text '{"main":"14 天","sub":"-7 斤","tags":"腰突 大基数"}' \
  -o ~/DAY14/cover.jpg
```

### 2. B 站横屏封面

```bash
封面合成 compose \
  --photos main.jpg left.jpg right.jpg \
  --layout symmetric-cascade \
  --aspect 16:9 \
  --text '{"main":"减脂日记","sub":"DAY 14"}' \
  -o cover_bilibili.jpg
```

### 3. 小红书方形多图

```bash
封面合成 compose \
  --photos a.jpg b.jpg c.jpg d.jpg e.jpg f.jpg \
  --layout grid \
  --aspect 1:1 \
  -o cover_xhs.jpg
```

## `--text` 格式选择

| 场景 | 用 |
|---|---|
| 3 行固定布局(main + sub + tags)| 简单 JSON |
| 自定义位置/字号/颜色 | 完整 JSON(lines 数组)|

详见 SKILL.md §② `--text` JSON 两种格式。

## 常见错

- ❌ `--photos` 只有 1 张 → 报错,至少 2 张
- ❌ `--output` 缺后缀 → 报错
- ❌ `--aspect` 不在白名单 → 报错(白名单:16:9, 9:16, 4:3, 3:4, 1:1, 4:5, 5:4)
- ❌ 某张照片路径不存在 → 报错(哪个文件错,会明确告诉你)

## 跑完看结果

`status: "warn"` 是**正常**(布局不同会产生不同的暗像素区,不影响结果)。

`status: "ok"` 表示所有诊断项都过。

`status: "error"` 看 `data` 里的 `errors` 列表,每个错误都包含字段名 + 当前值 + 期望值 + 怎么修。