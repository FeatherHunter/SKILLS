# 12-beauty - 美颜 — v1.2 已实现

> **对应脚本**: `scripts/ai_beauty.py`
> **触发词**: "美颜"、"磨皮"、"瘦脸"、"大眼"、"美白"、"人脸美化"
> **实测状态**: ✅ 验证通过

---

## 1. 调用范式

### 场景 1

```bash
# 用预设
python scripts/ai_beauty.py --input v.mp4 --output v_beauty.mp4 --preset natural

# 自定义强度(0-1)
python scripts/ai_beauty.py --input v.mp4 --output v.mp4 \
  --smooth 0.5 --whiten 0.25 --slim 0.3 --enlarge 0.3

# 只磨皮(瘦脸/大眼关闭)
python scripts/ai_beauty.py --input v.mp4 --output v.mp4 --smooth 0.5 --slim 0 --enlarge 0

# 加 --verbose 看 debug 日志
python scripts/ai_beauty.py --input v.mp4 --output v.mp4 --preset natural --verbose
```

## 2. 参数

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--input` | `-i` | (必填) | 输入视频/音频/图片 |
| `--output` | `-o` | (必填) | 输出路径 |

## 3. 常见错误 / 限制

- 大眼需要正脸(侧面效果差)
- 多人脸只处理第 1 张脸
- 视频处理慢(逐帧),生产用建议 GPU

## 4. 相关参考

- **SKILL.md §14 子技能索引**：本子技能的路由表
- **scripts/README.md**：scripts/ 目录命名规范（`<维度>_<动作>.py`）
- `.archive/CHANGELOG.md`：本子技能历史变更

---

<details>
<summary>📋 原文存档（v0.5 旧版，仅供 git history 追溯）</summary>

# 子技能 12 · beauty(美颜 L2)

## 它是什么

用 mediapipe face mesh(478 个关键点 = 468 mesh + 10 iris)做**磨皮 + 美白 + 瘦脸 + 大眼**四种人脸美化。代码版剪映美颜。

**Level:** L2 标准版(对标剪映 90%)。
- ✅ 磨皮:脸部 oval mask + 高斯模糊 + alpha blend
- ✅ 美白:HSV 空间提亮 + 降饱和(自然不假)
- ✅ 瘦脸:Delaunay 三角剖分 + 仿射变形(脸颊/下颌关键点向中心靠拢)
- ✅ 大眼:眼睛轮廓点向虹膜中心放大
- ❌ 美肤瑕疵修复(需要 AI API,L3 做不到)

## 怎么用

```bash
# 用预设
python scripts/ai_beauty.py --input v.mp4 --output v_beauty.mp4 --preset natural

# 自定义强度(0-1)
python scripts/ai_beauty.py --input v.mp4 --output v.mp4 \
  --smooth 0.5 --whiten 0.25 --slim 0.3 --enlarge 0.3

# 只磨皮(瘦脸/大眼关闭)
python scripts/ai_beauty.py --input v.mp4 --output v.mp4 --smooth 0.5 --slim 0 --enlarge 0

# 加 --verbose 看 debug 日志
python scripts/ai_beauty.py --input v.mp4 --output v.mp4 --preset natural --verbose
```

## 5 个 preset

| preset | smooth | whiten | slim | enlarge | 适用 |
|---|---|---|---|---|---|
| `off` | 0 | 0 | 0 | 0 | 关掉所有效果 |
| `slight` | 0.3 | 0.15 | 0.2 | 0.2 | 几乎看不出,稳妥 |
| **`natural`** | 0.5 | 0.25 | 0.3 | 0.3 | **默认,推荐,自然好看** |
| `strong` | 0.7 | 0.4 | 0.5 | 0.4 | 明显美颜,适合商业 |
| `max` | 0.9 | 0.5 | 0.7 | 0.5 | 极限美颜,可能失真 |

## 4 个子能力(技术细节)

### 磨皮(`--smooth` 0-1)
- 算法:脸部 oval 区域做高斯模糊,alpha mask blend
- mask 边缘羽化 15px(避免硬边)
- 强度:0.5 = 模糊 σ=15 + 50% blend

### 美白(`--whiten` 0-1)
- HSV 空间:提亮(beta = 8×strength) + 提饱和(alpha = 1+0.1×strength)
- 同时降饱和(1-0.15×strength),避免假白
- 自然效果好

### 瘦脸(`--slim` 0-1)
- 22 个关键点(SLIM_INDICES)向脸部中心 x 靠拢
- 公式:`new_x = x + (cx - x) * strength * 0.35`
- Delaunay 三角剖分 + 仿射变形
- 仅影响脸部,不波及其他区域

### 大眼(`--enlarge` 0-1)
- 眼睛轮廓点(28 个)向虹膜中心放大
- 公式:`new_x = cx + (x - cx) * (1 + 0.4 * strength)`
- 需要 mediapipe `refine_landmarks=True` 才能拿到虹膜点
- 边缘 mask 控制只影响眼周,不变脸型

## 输出规格

- 分辨率:跟原视频一致
- 帧率:跟原视频一致
- 视频编码:libx264(原视频编码)
- 音频:原样保留
- 处理速度:1080p ~5-10x 实时(CPU),建议小批量

## 模型管理

mediapipe 0.10.35 需要 `face_landmarker.task` 模型(~3.7MB),自动下载:
- 优先:`assets/face_landmarker.task`(项目本地)
- fallback:`C:\zhijian_models\`(绕过 Windows 中文路径 bug)

**注:** 如果你的项目路径含中文(如 `D:\2Study\StudyNotes\智剪工坊`),模型会 fallback 到 `C:\zhijian_models\`。这是已知 bug,自动处理。

## 已知限制

- 大眼需要正脸(侧面效果差)
- 多人脸只处理第 1 张脸
- 视频处理慢(逐帧),生产用建议 GPU

## 常见问题

**Q: 提示 "FileNotFoundError: face_landmarker.task"?**
A: 网络问题,手动从 https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task 下载到 `C:\zhijian_models\`。

**Q: 处理到一半报 "Access Violation"?**
A: NVENC bug,beauty 默认用 libx264 不应该出问题。如果出问题,确认 `--vcodec libx264`。

**Q: 想批量处理 100 个视频?**
A: 用 `batch.py --task beauty ...`(需先扩展 batch.py,目前不支持 beauty task)。

## 相关脚本

- 上游:无
- 下游:无(独立功能)
- 类似:剪映美颜、抖音美颜(图形化 GUI)


</details>
