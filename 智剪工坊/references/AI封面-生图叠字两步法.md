# AI封面 - 生图叠字两步法

> **对应脚本**: `scripts/ai/cover.py`
> **触发词**: "封面"、"做封面"、"AI 封面"、"AI 生图"、"设计封面"、"缩略图"、"thumbnail"
> **实测状态**: ✅ 验证通过

---

## 📍 路径契约（**本文件是路径的唯一真理**，v1.3 强制）

**AI 看到 cover 任务必读本段**。其他文件不再定义封面路径，只引用本段。

### 3 步路径

```
00_智剪/粗加工/cover/cover_draft_N.jpg   ← Step 1 草稿（AI 生成，可多个候选 N=1,2,3...）
00_智剪/粗加工/cover/cover_final.jpg     ← Step 2 终稿（用户从草稿中选定 1 个）
00_智剪/成片/cover.jpg                    ← Step 3 拼成片时复制过来
```

### AI 执行流程（v1.3 强制）

1. **生成草稿**：
   - 调 `ai_cover.py` 或 `matrix_generate_image`
   - 输出 `00_智剪/粗加工/cover/cover_draft_1.jpg`、`cover_draft_2.jpg`...（按用户要求数量）
2. **用户选定终稿**：
   - AI **必须**等用户从草稿中选 1 个
   - 不允许 AI 自己挑
   - 复制到 `00_智剪/粗加工/cover/cover_final.jpg`
3. **拼成片时复制**：
   - 阶段 4 收尾时，AI 自动 `cp cover/cover_final.jpg ../成片/cover.jpg`
   - 这是为向后兼容：`00_智剪/成片/` 下必须有 `cover.jpg` 才能算"完整成片"

### 关键规则

- **草稿必须 ≥1 个**：AI 至少生成 1 张让用户选（推荐 3-4 张给用户挑）
- **用户没选 = 流程未完成**：AI 不得跳过用户选择直接生成 `cover_final.jpg`
- **终稿文件名固定**：`cover_final.jpg`（不带后缀编号）
- **成片封面与草稿分离**：成片目录只放终稿副本，不放草稿

---

## 1. 调用范式

### 场景 1：单图生成

```bash
python scripts/ai/cover.py \
  --prompt "A man on a fitness journey, cinematic dramatic lighting, NO TEXT" \
  --title-main "DAY 1" \
  --subtitle "减脂日记" \
  --output 00_智剪/粗加工/cover/cover_draft_1.jpg
```

### 场景 2：批量生成（推荐 3-4 张让用户选）

```bash
for i in 1 2 3 4; do
  python scripts/ai/cover.py \
    --prompt "vlog cover, $i" \
    --output "00_智剪/粗加工/cover/cover_draft_$i.jpg"
done
```

### 场景 3：matrix MCP 直接调用

```bash
mavis mcp call matrix matrix_generate_image --file req.json
# 输出 → 复制到 00_智剪/粗加工/cover/cover_draft_N.jpg
```

## 2. 参数

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--prompt` | — | (必填) | AI 生图 prompt（英文效果更好） |
| `--title-main` | — | `""` | 主标题文字（叠在图上） |
| `--subtitle` | — | `""` | 副标题文字 |
| `--theme` | — | `fitness` | 配色方案（fitness / lifestyle / professional，详见配色段） |
| `--output` | `-o` | (必填) | 输出路径（**默认写到 `00_智剪/粗加工/cover/`**） |
| `--input` | `-i` | — | 可选：真实照片（图生图用） |

## 3. 配色方案（v1.3 三类主题）

| 主题 | 主色 | 副色 | 适用 |
|---|---|---|---|
| `fitness` | 警示红 `#FF3838` | 目标金 `#FFD700` | 健身/挑战/热血 |
| `lifestyle` | 主色暖橙 `#FF922B` | 副色深蓝 `#4DABF7` | 旅行/美食/治愈 |
| `professional` | 主色深蓝 `#4D6BF7` | 副色亮金 `#FFD700` | 教程/财经/专业 |

**`theme` 参数必填**——AI 必须问用户或从 `intent.json.cover.theme` 读取。

## 4. 字号参考（1920x1080 画布）

| 元素 | 字号 | 位置 |
|---|---|---|
| 主标题数字 | 130-180 px | 居中 / 右上 |
| 副标题 | 50-70 px | 主标题下方 |
| 系列名 | 40-60 px | 角落 / 底部 |
| 标签 | 30-40 px | 角落 |

## 5. 字体选择

```python
# Windows 自带字体
"C:/Windows/Fonts/msyh.ttc"        # 微软雅黑(默认)
"C:/Windows/Fonts/msyhbd.ttc"      # 微软雅黑 Bold(主标题)
"C:/Windows/Fonts/simhei.ttf"      # 黑体(更现代)
"C:/Windows/Fonts/simsun.ttc"      # 宋体(传统)
```

## 6. 完整脚本

封装到 `scripts/ai/cover.py`,支持:
- 自动调用 matrix 生图
- 自动叠中文（PIL）
- 自动配色（按 theme）
- 输出 JPG（95% 质量）

## 7. 调用示例

```
用户: "给我做个减肥挑战的封面,184 到 139.9 斤"
→ AI:
  1. 问 theme (fitness/lifestyle/professional)
  2. 批量生成 3-4 张草稿到 00_智剪/粗加工/cover/cover_draft_*.jpg
  3. 把草稿列表展示给用户
  4. 等用户选定 → 复制为 cover_final.jpg
  5. 阶段 4 拼成片时复制到 00_智剪/成片/cover.jpg
```

## 8. 输出规格

- **比例:** 16:9（B 站标准，实际 1146x717 也可）
- **分辨率:** 2K（2752x1536）
- **格式:** JPG（95% 质量）
- **大小:** < 2 MB（B 站上传限制）
- **文件名约定**: `cover_draft_N.jpg`（草稿）/ `cover_final.jpg`（终稿）/ `cover.jpg`（成片）

## 9. 常见错误

- **AI 自己选终稿**：违反 v1.3 契约，必须等用户选
- **草稿数量为 0**：AI 至少生成 1 张
- **文件写到工作区根目录**：必须写到 `00_智剪/粗加工/cover/`
- **文件名带版本号 `cover_final_v2.jpg`**：违反契约，必须 `cover_final.jpg`（不带后缀）

## 10. 相关参考

- **SKILL.md §⚠️ AI 必读 #5**: cover.type 路由
- **references/主流程-阶段编排.md §阶段 4 收尾**: 拼成片时复制 cover 的具体时机
- **scripts/ai/cover.py**: 实际脚本
