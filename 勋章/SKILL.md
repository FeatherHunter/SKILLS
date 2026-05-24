# 勋章技能

> 用户完成指定任务后，颁发精美GIF奖励（勋章/证书/奖杯）

## 环境变量（必填）

**必须配置以下两个环境变量**：

| 环境变量 | 说明 |
|----------|------|
| `SKILLS_DB_PATH` | 勋章数据库存放目录 |
| `MEDAL_RESOURCE_PATH` | 勋章GIF资源存储目录 |

**配置方式**：通过交互引导用户提供路径，或由用户自行配置。

**注意**：AI执行任何操作前必须检查环境变量是否已设置，缺失则报错并提示用户配置。

---

## 奖励分类

### 勋章 (Badge)

**触发条件**：完成单项任务、习惯打卡

**用途**：最常用的认可方式，用户做完任何事都可以颁

**数据库记录**：medal_type = "badge"

---

### 证书 (Certificate)

**触发条件**：完成课程、达到里程碑、通过考试

**用途**：较大的成就认可，比勋章更正式

**数据库记录**：medal_type = "certificate"

---

### 奖杯 (Trophy)

**触发条件**：比赛获胜、超越他人、获得第一名

**用途**：竞争性场景，稀缺性高

**数据库记录**：medal_type = "trophy"

---

## GIF生成规范

### 核心原则

1. **每次必须全新设计**：不允许复用任何之前的HTML、动画、元素
2. **结合具体事件设计**：根据用户完成的具体事情设计对应的视觉风格
3. **充满创意**：每次都要有新鲜感和独特性，不能重复

### 技术方案（固定）

**技术栈**：Playwright + ffmpeg

**流程**：
```
AI根据具体事件自由设计 → 生成全新HTML（含CSS动画）
    ↓
scripts/generate_medal_gif.py --html "<HTML>" --output <文件名>
    ↓
Playwright渲染HTML → 逐帧截图（full_page=True，内容自适应）
    ↓
ffmpeg合成GIF
    ↓
保存到 MEDAL_RESOURCE_PATH
```

**脚本位置**：`scripts/generate_medal_gif.py`

**使用方法**：
```bash
# 方式1：直接传入HTML代码
python3 scripts/generate_medal_gif.py --html "<html>...</html>" --output badge.gif

# 方式2：读取HTML文件
python3 scripts/generate_medal_gif.py --html-file template.html --output badge.gif
```

**AI自行决定的参数**（不限制）：
- 动画时长
- 帧率
- 颜色质量
- 尺寸
- 背景样式
- 整体风格

**生成后**调用 `medal.py add` 写入数据库，然后发送GIF给用户。

---

## CLI 命令

### 颁发奖励
```bash
python3 scripts/medal.py add --type <badge|certificate|trophy> --name <名称> --gif <GIF路径> --remark <备注>
```

### 查询奖励记录
```bash
python3 scripts/medal.py list [--type <类型>] [--limit <数量>]
```

### 查看统计
```bash
python3 scripts/medal.py stats
```

### 初始化数据库
```bash
python3 scripts/medal.py init
```

---

## AI执行规范

1. **禁止直接操作数据库**：所有读写必须通过 `scripts/medal.py` CLI
2. **环境变量必检**：执行前检查 `SKILLS_DB_PATH` 和 `MEDAL_RESOURCE_PATH`
3. **生成前确认**：展示将颁发的奖励类型和名称，用户确认后再生成
4. **GIF必须发送**：生成后必须通过 qqbot 发送给用户
5. **每次全新设计**：不允许复用任何之前的HTML，必须完全重新设计
6. **结合具体事件**：设计必须与用户完成的具体事情紧密相关