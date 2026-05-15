# 采购清单

> 触发词："生成采购清单"、"要买什么"、"准备食材"

---

## 功能说明

根据食谱生成**可交互的手机端采购清单 HTML**，供用户在菜市场/超市/网购使用。

---

## 完整工作流

```
用户请求
    ↓
AI 调用脚本获取 JSON
    ↓
AI 根据 JSON 和 HTML 生成规则 生成 HTML
    ↓
AI 发送 HTML 给用户
```

---

## 输入

| 参数 | 说明 |
|------|------|
| recipe_ids | 食谱ID数组，支持1个或多个 |
| exclude_optional | 可选，是否排除可选食材 |

---

## 命令参考

```bash
# 查询食材数据（返回JSON，支持多ID用逗号分隔）
python scripts/shopping_manager.py generate <recipe_id>[,<recipe_id2>,...]

# 排除可选食材
python scripts/shopping_manager.py generate <recipe_id> --exclude-optional
```

---

## 输出格式

```json
{
  "generated_at": "2026-05-16T01:13:00",
  "recipe_ids": ["f6a9bb9b-e2bc-477d-8178-b55c139e0506"],
  "exclude_optional": false,
  "recipes": [
    {
      "id": "f6a9bb9b-e2bc-477d-8178-b55c139e0506",
      "name": "红烧狮子头",
      "servings": 4,
      "ingredients": [
        {
          "id": "食材uuid",
          "name": "猪前腿肉",
          "quantity": 600,
          "unit": "g",
          "quantity_text": "约600g（七分瘦三分肥）",
          "category": "肉类",
          "is_optional": false,
          "substitute": null
        }
      ]
    }
  ]
}
```

---

## 字段说明

### 顶层字段

| 字段 | 说明 |
|------|------|
| generated_at | 生成时间（ISO格式） |
| recipe_ids | 请求的食谱ID数组 |
| exclude_optional | 是否排除了可选食材 |
| recipes | 食谱数组 |

### recipes[]

| 字段 | 说明 |
|------|------|
| id | 食谱ID |
| name | 食谱名称 |
| servings | 份数 |
| ingredients | 食材数组 |

### ingredients[]

| 字段 | 说明 |
|------|------|
| id | 食材ID |
| name | 食材名称 |
| quantity | 用量数值 |
| unit | 单位 |
| quantity_text | 文字描述 |
| category | 分类（肉类/蔬菜/调料/海鲜/蛋类/其他） |
| is_optional | 是否可选（false=必需，true=可选） |
| substitute | 替代食材（无可替代则为null） |

---

## 多食谱示例

**输入：**
```bash
python scripts/shopping_manager.py generate "id1","id2"
```

**输出：**
```json
{
  "generated_at": "2026-05-16T01:13:00",
  "recipe_ids": ["id1", "id2"],
  "exclude_optional": false,
  "recipes": [
    {
      "id": "id1",
      "name": "红烧狮子头",
      "servings": 4,
      "ingredients": [...]
    },
    {
      "id": "id2",
      "name": "宫保虾球",
      "servings": 2,
      "ingredients": [...]
    }
  ]
}
```

---

## HTML 生成要求

### 基础要求（12项全覆盖）

| # | 要求 | 说明 |
|---|------|------|
| 1 | 单手操作友好 | 按钮尺寸≥44px，间距足够 |
| 2 | 强光下可读 | 高对比度配色，避免浅色背景 |
| 3 | 快速扫描 | 分类清晰，食材信息一目了然 |
| 4 | 点击即标记 | 点一下复选框切换已买状态 |
| 5 | 已买/未买区分 | 已买项变灰+划线+复选框打勾 |
| 6 | 进度反馈 | 显示"已买X件/共Y件" |
| 7 | 分类折叠 | 支持折叠/展开分类，减少视觉负担 |
| 8 | 移动端适配 | 响应式设计，适配手机屏幕 |
| 9 | 来源可见性 | 多食谱时标注食材来自哪道菜 |
| 10 | 合并/拆分视图 | 支持"按分类看"和"按食谱看"两种模式 |
| 11 | 同名食材合并逻辑 | 多食谱同名食材合并显示总用量+来源 |
| 12 | 按食谱分组显示 | 支持切换"按食谱分组"视图 |

### 附加要求

| # | 要求 | 说明 |
|---|------|------|
| 13 | 可选食材特殊标识 | 可选食材加明显标记（如*或不同颜色） |
| 14 | 替代食材显示 | 替代食材信息可见 |

---

## HTML 文件存储

### 存储路径
```
/home/feather/.openclaw/media/qqbot/shopping/
```

### 文件名格式
```
采购清单_{菜名}_{时间戳}.html
```

| 部分 | 说明 |
|------|------|
| 前缀 | 采购清单（固定） |
| 菜名 | 单菜名；多菜用+连接（如宫保虾球+辣炒虾球） |
| 时间戳 | YYYYMMDD_HHMMSS |

### 示例
```
采购清单_宫保虾球_20260516_014200.html
采购清单_宫保虾球+辣炒虾球_20260516_014200.html
```

### 发送方式
1. 保存文件到上述路径
2. 通过QQBot发送给用户

---

## 参考

- 分类参考：references/categories.md
- 表结构：references/database_schema.md