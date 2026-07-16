# diagnose 子命令

> 详见 SKILL.md §② 子命令 2。

## 3 个检查项

| 项 | 阈值 | 含义 |
|---|---|---|
| transparency | pct > 1% | alpha ∈ [10, 245] 的像素占比,通常是旋转/羽化残留 |
| darkness | pct > 60% | RGB < 30 像素占比,可能全黑底或半透明黑叠加 |
| symmetry | diff > 8% | 左右翻转对比差异,对称布局是否镜像 |

## 用法

```bash
# 跑全部(默认)
封面合成 diagnose cover.jpg

# 只跑某几项
封面合成 diagnose cover.jpg --check transparency
封面合成 diagnose cover.jpg --check transparency,darkness

# 多个 check 用逗号
封面合成 diagnose cover.jpg --check transparency,darkness,symmetry
```

## 输出解读

```json
{
  "status": "warn",
  "data": {
    "image": "cover.jpg",
    "size": [1920, 1080],
    "semi_transparent": {"count": 5230, "pct": 0.25, "warning": false},
    "dark_areas": {"count": 1200000, "pct": 55.7, "warning": false},
    "symmetry": {"diff_pct": 5.2, "warning": false}
  },
  "message": "诊断完成:无问题",
  "warnings": []
}
```

每项 `warning: bool` 字段就是"有没有问题"的判断。`warnings` 数组是给 AI 的修复建议。

## 各警告对应修复方案

| 警告 | 修复 |
|---|---|
| semi_transparent high | 重新跑 compose,确保 layers.py 用的是 `rotate_hard` 而不是 `im.rotate(expand=True)` |
| too_dark | 检查画布色 + 减小主图占画布比例 |
| asymmetric | 对称布局时 left_x 和 right_x 应镜像于画布中心 |
