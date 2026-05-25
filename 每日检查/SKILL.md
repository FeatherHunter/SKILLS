---
name: 每日检查
description: 每天定时或手动触发，AI查询各技能数据后生成精美HTML页面，Playwright截图后发送给用户。纯视觉化展示，极简浅色风格。
---

# 每日检查

## 核心设计

**不再使用数据库，不再使用issues表，不再使用脚本**。

视觉化流程：
1. AI查询各技能数据
2. 生成精美HTML页面（AI自由发挥视觉设计）
3. Playwright截图
4. 发送图片给用户

---

## 视觉风格规范（必须遵守）

### 页面尺寸
- HTML宽度：**800px**（固定）
- 字体大小：主文字 32px，副文字 26-28px，标题 64px
- 1:1 截图（不缩放）

### 配色方案（简约浅色系 Apple风）
- 背景：#FAFAFA（浅灰白）
- 卡片背景：#FFFFFF（纯白）
- 主文字：#1C1C1E（近黑）
- 次文字：#8E8E93（灰色）
- 成功色：#34C759（绿色）
- 警告色：#FF9500（橙色）
- 强调色：#007AFF（Apple蓝）

### 字体
- 标题：700 weight，64px
- 日期：500 weight，28px
- 主文字：500 weight，32px
- 副文字：400 weight，26-28px

### 布局
- 页面宽度：800px（固定）
- 卡片圆角：28px
- 内边距：36px
- 卡片间距：20px

### 卡片样式
- 白色背景
- 圆角28px
- 轻微阴影
- 左侧无色条（简洁风格）

### 图标样式
- 图标容器：72x72px，圆角16px
- 图标emoji：36px
- 已完成图标背景：#E8F5E9（浅绿）
- 待确认图标背景：#FFF3E0（浅橙）

---

## 工作流程

### Step 1：查询各技能数据

按顺序查询以下技能和对应数据：

| 顺序 | 问题 | 技能 | 查什么 |
|------|------|------|--------|
| 1 | 备忘录待办 | 备忘录 | 所有待提醒事项 |
| 2 | 体重 | 卡路里 | 最近体重记录 + 7天趋势 |
| 3 | 热量 | 卡路里 | 昨日摄入/消耗数据 |
| 4 | 睡眠 | 作息管家 | 昨日睡眠时长 |
| 5 | 运动 | 卡路里 | 昨日运动记录 |
| 6 | 作息 | 作息管家 | 昨日作息执行情况 |

### Step 2：判断已完成 vs 待确认

根据查询结果判断每项状态：

**已完成** - 有明确数据：
- 今早有体重记录
- 昨日有热量记录
- 昨日有睡眠记录
- 昨日有运动记录
- 有待办事项记录

**待确认** - 无数据：
- 查不到记录 → 抛一个问题

### Step 3：生成HTML

1. 读取同目录下的 `template.html` 模板
2. 用查到的数据替换模板中的占位符：
   - `{{date}}` → 今天的日期（如 "05月25日 · 周一"）
   - `{{done_cards}}` → 已完成项的卡片HTML
   - `{{todo_cards}}` → 待确认项的卡片HTML
   - `{{done_count}}` → 已完成数量
   - `{{total_count}}` → 总数量（固定6）

3. **AI自由发挥**：
   - 保持简约浅色系 Apple 风格
   - 卡片圆角、阴影
   - 字体大小按规范（主文字 32px）
   - 装饰元素简洁

**模板占位符说明**：

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{{date}}` | 当天日期 | 05月25日 · 周一 |
| `{{done_cards}}` | 已完成卡片HTML | 包含图标的item列表 |
| `{{todo_cards}}` | 待确认卡片HTML | todo-item列表 |
| `{{done_count}}` | 已完成数量 | 4 |
| `{{total_count}}` | 总数量 | 6 |

**HTML结构规范**：
```html
<!-- 标题区 -->
<div class="header">
  <div class="date">{{date}}</div>
  <div class="title">每日检查</div>
</div>

<!-- 分隔线 -->
<div class="divider"></div>

<!-- 已完成区 -->
<div class="section">
  <div class="section-header">
    <span class="section-icon">✓</span>
    <span class="section-title">已完成</span>
  </div>
  <div class="card">
    <div class="item">
      <div class="item-left">
        <div class="item-icon icon-green">📝</div>
        <span class="item-label">备忘录</span>
      </div>
      <div class="item-right">
        <div class="item-value">暂无待办</div>
      </div>
    </div>
    <!-- 更多item -->
  </div>
</div>

<!-- 待确认区 -->
<div class="section">
  <div class="section-header">
    <span class="section-icon">?</span>
    <span class="section-title">待确认</span>
  </div>
  <div class="card">
    <div class="todo-item">
      <div class="todo-label">今天睡了多久？</div>
      <div class="todo-hint">昨晚几点睡，几点起的</div>
    </div>
    <!-- 更多todo-item -->
  </div>
</div>

<!-- 底部统计 -->
<div class="footer">
  <div class="stat-badge">
    <span class="stat-num">3</span>
    <span class="stat-sep">/</span>
    <span class="stat-num">6</span>
    <span class="stat-text">项已完成</span>
  </div>
</div>
```

### Step 4：Playwright截图

1. 保存HTML到临时文件（/tmp/daily_check_{timestamp}.html）
2. 使用 `scripts/screenshot.py` 截图：
   ```bash
   python3 scripts/screenshot.py <html_path> <output_path> 800 1
   ```
   - 参数1：HTML文件路径
   - 参数2：输出图片路径
   - 参数3：viewport_width = 800
   - 参数4：scale = 1（1:1截图，不缩放）
3. 截图保存到：`~/.openclaw/media/qqbot/daily_check_{timestamp}.png`

### Step 5：发送图片（关键！）

使用 message 工具发送图片到 QQ：

```python
message(
  action="send",
  attachments=[{"path": "/home/feather/.openclaw/media/qqbot/daily_check_{timestamp}.png", "type": "image"}],
  message="每日检查 · {日期}",
  target="qqbot:c2c:18CD32F5999F760615E9862E343E59FC"
)
```

**重要**：
- `attachments` 参数必须用数组，元素是 `{"path": ..., "type": "image"}`
- `image` 参数已废弃，不要用
- 截图路径必须在 `~/.openclaw/media/qqbot/` 下才能发送
- 必须有 `message` 参数（可以是简单文字如"每日检查"）

---

## 触发方式

### 手动触发

用户说以下任意一句即触发：
- "每日检查"
- "健康检查"
- "检查一下"
- "lint"

### 定时触发

Cron：每天 22:00

---

## 注意事项

- 查询各技能时，如果某技能没有数据，返回"暂无数据"而不是报错
- 如果某技能查询出错，跳过该技能，不影响其他
- 不存任何数据到数据库，每次检查都是独立对话
- 六个问题顺序固定为：备忘录 → 体重 → 热量 → 睡眠 → 运动 → 作息
- 展示数据时用实际日期（如"05月25日 · 周一"）
- HTML中AI可以自由发挥视觉效果，但必须保持简约浅色系 Apple 风格
- 字体大小规范：主文字 32px，副文字 26-28px
- 截图必须 1:1（scale=1），不要缩放