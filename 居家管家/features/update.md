# 改物品

## 流程概述

1. 搜索目标物品
2. 推断变更内容
3. 展示变更内容
4. 确认并执行

---

## Step 1: 搜索目标物品

AI 先搜索目标物品，确认是哪一个（多物品时让用户选）。

---

## Step 2: 推断变更内容

### 位置状态变更

| 用户说 | 命令 |
|--------|------|
| "借给朋友" | `--location-status "借用中"` |
| "坏了" | `--location-status "维修中"` |
| "扔了/不要了" | `--location-status "已废弃"` |
| "用完了" | `--location-status "已用完"` |

如果物品有多个位置，需要用 `--location` 指定要修改的位置：

```bash
# 修改特定位置的状态
python home_manager.py update --id 1 --location-status "备用" --location "客厅/冰箱"
```

### 数量变更

| 用户说 | 命令 |
|--------|------|
| "喝了1瓶" | `--minus 1` |
| "买了3瓶" | `--plus 3` |

同样可以用 `--location` 指定要修改的位置：

```bash
# 冰箱里的那瓶喝了
python home_manager.py update --id 1 --minus 1 --location "客厅/冰箱"

# 再买2瓶放冰箱
python home_manager.py update --id 1 --plus 2 --location "客厅/冰箱"
```

**注意**：当数量减到 0 时，该位置记录会自动删除。

### 位置移动

| 用户说 | 命令 |
|--------|------|
| "移到厨房" | `--new-location "厨房/餐桌" --location "原位置"` |

```bash
# 把客厅的东西移到厨房
python home_manager.py update --id 1 --new-location "厨房/餐桌" --location "客厅/茶几"
```

### 日期更新

| 用户说 | 命令 |
|--------|------|
| "更新购买日期" | `--purchase-date "2025-05-01" --location "位置"` |
| "更新过期日期" | `--expiration-date "2025-06-01" --location "位置"` |

```bash
# 更新位置的购买日期
python home_manager.py update --id 1 --purchase-date "2025-05-10" --location "客厅/冰箱"

# 更新位置的过期日期
python home_manager.py update --id 1 --expiration-date "2025-06-01" --location "客厅/冰箱"
```

### 基本信息更新

```bash
# 更新名称、分类、备注等
python home_manager.py update --id 1 --name "新名称" --remark "新备注"
python home_manager.py update --id 1 --category "新分类"
python home_manager.py update --id 1 --owner "其他人"
```

### 标签更新

```bash
# 覆盖式更新标签
python home_manager.py update --id 1 --tags "新标签1,新标签2"
```

---

## Step 3: 展示变更内容

AI 列出将要改动的字段和值，请用户确认。

---

## Step 4: 确认并执行

用户说"对" → 执行命令，AI 展示脚本输出的更新结果。

---

## 多位置物品处理

当物品有多个位置时，update 命令需要用 `--location` 指定要操作的位置：

```bash
# 物品有多个位置时，必须指定
python home_manager.py update --id 1 --location-status "备用" --location "客厅/冰箱"

# 如果不指定 --location，且物品有多个位置，脚本会报错并列出所有位置让用户选择
```

**数量增加时的特殊处理**：
- 当通过 `--plus` 增加数量时
- 如果该物品原状态为"已用完"或"已废弃"
- AI 必须询问用户新状态是什么（在家/备用/快递中/其他）
- 不得自动修改状态，必须用户明确表态