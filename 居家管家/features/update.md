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

#### 覆盖式（删除原 tag + 写入新 tag）

```bash
# 覆盖式更新标签
python home_manager.py update --id 1 --tags "新标签1,新标签2"
```

#### 追加 tag（保留现有 tag + 新增）

```bash
# 追加单个 tag
python home_manager.py update --id 1 --add-tag "红色"

# 追加多个 tag（逗号分隔）
python home_manager.py update --id 1 --add-tag "红色,短袖,优衣库"
```

#### 删除 tag（按值删除，不覆盖）

```bash
# 删除单个 tag
python home_manager.py update --id 1 --remove-tag "白色"

# 删除多个 tag（逗号分隔）
python home_manager.py update --id 1 --remove-tag "白色,旧款"
```

#### 追加 + 删除组合（推荐用于纠错：白 → 白色 + 去重复）

```bash
# 同时追加和删除（执行顺序：先追加，后删除）
python home_manager.py update --id 1 --remove-tag "白" --add-tag "白色"
```

**注意**：
- `--tags` 是覆盖式（删除原 tag），与 `--add-tag` / `--remove-tag` 不能同时用同一类目
- tag 字符串自动 `strip()`，空字符串 / 纯空格跳过
- 删除不存在的 tag 不会报错（静默成功）
- update 不强制 tag 数量 ≥ 10（与 add 不同，允许纠错/合并）

### 追加新位置（心愿 ID: 84）

**与"位置移动"的区别**：
- 位置移动（`--new-location`）：**替换**现有位置，原位置记录被改写
- 追加位置（`--add-location`）：**新增**一条位置记录，原位置保留 → 一物多位置

**适用场景**：
- 同款 2 罐可乐：1 罐在客厅/桌上、1 罐在厨房/冰箱
- 应季衣物：夏季在阳台/壁柜，冬季回主卧/衣柜（两个位置都在）
- 重要文件：本地 + U 盘双备份
- 食品库存：冰箱 1 袋 + 储物柜 1 袋备用

**基本用法**：

```bash
# 最简：追加一个位置，数量 1，状态"在家"
python home_manager.py update --id 1 --add-location "办公室/抽屉"

# 追加 2 件，状态"备用"
python home_manager.py update --id 1 --add-location "储物柜" --add-quantity 2 --add-location-status "备用"

# 追加位置时同时设购买/过期日期
python home_manager.py update --id 1 --add-location "零食柜" \
  --add-purchase-date "2026-06-01" \
  --add-expiration-date "2027-06-01"

# 追加时附带原因备注
python home_manager.py update --id 1 --add-location "健身房" --add-reason "健身带去的"
```

**完整参数**：

| 参数 | 说明 |
|------|------|
| --add-location | 必填，要追加的位置路径 |
| --add-quantity | 该位置数量（默认1） |
| --add-location-status | 该位置状态（默认"在家"） |
| --add-purchase-date | 该位置购买日期 |
| --add-expiration-date | 该位置过期日期 |
| --add-reason | 备注原因 |

**限制**：
- 同一物品同一路径不能重复追加（会报错）。如需增加该位置数量，请用 `--plus --location "位置"`。


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