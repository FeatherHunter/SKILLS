---
name: 每日检查
description: 每天定时或手动触发，AI查询各技能数据后生成精美HTML页面，Playwright截图后发送给用户。纯视觉化展示，极简浅色Apple风格。
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

## 每日检查问题列表（共16个）

| # | 唤醒词 | CLI 命令 | 来源技能 | 查什么 |
|---|--------|----------|---------|--------|
| 1 | 查今天吃 | `python calorie_tracker.py list` | 卡路里 | 今日所有饮食记录 + 总热量 |
| 2 | 查今天 | `python record_bill.py summary` | 饼干记账 | 今日支出 + 月度结余 |
| 3 | 查询今日 | `python query.py --date <YYYYMMDD>` | 录音机 | 今日所有消息 + 关键事件 |
| 4 | 看提醒 | `python memo_cli.py reminders` | 备忘录 | 今日待触发提醒 + 状态 |
| 5 | 查已提醒备忘 | `python memo_cli.py completed` | 备忘录 | 今日已完成提醒 + 完成度 |
| 6 | 查作息计划 | `python schedule_cli.py query-plans <今日>` | 作息管家 | 当前时段在计划中的安排 |
| 7 | 查多日计划 | `python schedule_cli.py query-plans <今日,明日,后日>` | 作息管家 | 未来 N 天关键节点 |
| 8 | 查睡眠记录 | `python sleep_tracker.py list` | 卡路里 | 昨晚睡眠时长/质量 |
| 9 | 查运动记录 | `python exercise_tracker.py list` | 卡路里 | 今日运动项目 + 时长 |
| 10 | 查体重趋势 | `python calorie_tracker.py weight-history` | 卡路里 | 体重变化（今日/昨日/周均） |
| 11 | 查卡路里数据 | `python calorie_tracker.py summary` | 卡路里 | 今日热量摄入/消耗/缺口 |
| 12 | 查营养配比 | `python calorie_tracker.py list` (AI 解析宏量) | 卡路里 | 今日宏量营养素比例（碳水/蛋白/脂肪） |
| 13 | 查快递 | `python home_manager.py list --status 快递中` | 居家管家 | 在途/待取快递 |
| 14 | 查过期 | `python home_manager.py stats --type expiring` | 居家管家 | 即将/已过期物品 |
| 15 | 看总览 | `python record_bill.py overview` | 饼干记账 | 本月财务总览（收入/支出/结余） |
| 16 | 查作息报告 | `python schedule_cli.py report <今日>` | 作息管家 | 今日作息分析报告 |

> **设计说明**：
> - 表格新增「CLI 命令」列，每个子任务都对应一个可被脚本/AI 触发的命令
> - 16 条全部走 CLI，零歧义、零依赖 AI 二次解析（#12 通过 list 输出含宏量字段由 AI 聚合）
> - 删除原 #6（学习规划师无 CLI）、#16（居家管家无 health）、#17（卡路里无独立 dashboard CLI）、#19（勋章无 chain 聚合 CLI）

---

## 特殊交互要求

### 睡眠汇报
查询到睡眠时长后，必须对用户说："千里之行，始于足下"

### 运动关注
重点询问今日运动情况，用户之前反馈这是弱项，需要关注。

---

## 视觉风格规范（必须遵守）

### 页面尺寸
- HTML宽度：**1200px**（固定）
- 高度：**1600px**（3:4比例）
- 字体大小：主文字 28px，副文字 22-24px，标题 72px
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

### 图标样式
- 图标容器：72x72px，圆角16px
- 图标emoji：36px
- 已完成图标背景：#E8F5E9（浅绿）
- 待确认图标背景：#FFF3E0（浅橙）

---

## 工作流程

### Step 1：查询各技能数据

按顺序执行上面16个调度子任务（每条触发对应技能的 CLI）。

### Step 2：判断已完成 vs 待确认

根据查询结果判断每项状态：

**已完成** - 有明确数据：
- 体重：今早有记录
- 热量：今日有摄入记录
- 运动：今日有运动记录
- 快递：有快递状态记录
- 物品：有快过期物品记录
- 记账：今日有支出记录
- 备忘录：有今日待办
- 录音机：最近有汇报记录
- 作息：今日作息正常
- 睡眠：昨天有睡眠记录

**待确认** - 无数据：
- 查不到记录 → 抛一个问题

### Step 3：生成HTML

1. 读取同目录下的 `template.html` 模板
2. 用查到的数据替换模板中的占位符：
   - `{{date}}` → 今天的日期（如 "05月25日 · 周一"）
   - `{{done_cards}}` → 已完成项的卡片HTML，使用以下格式：
     ```html
     <div class="done-item">
       <div class="done-icon green|blue|orange|purple|teal">
         <svg viewBox="0 0 24 24" fill="none" stroke="#34C759" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
           <!-- 体重: scale, 热量: fire, 运动: activity, 快递: package, 记账: dollar-sign -->
         </svg>
       </div>
       <div>
         <div class="done-label">问题标题</div>
         <div class="done-value">结果 · 副说明</div>
       </div>
     </div>
     ```
     **SVG图标对照**：
     - 体重：`<path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"><circle cx="12" cy="12" r="3"></circle></svg>`（天平图标）
     - 热量：`<path d="M12 2c-1.1 3-4 5-4 9a4 4 0 0 0 8 0c0-4-2.9-6-4-9z"></path>`（火焰图标）
     - 运动：`<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>`（心电图图标）
     - 快递：`<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>`（包裹图标）
     - 记账：`<line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>`（美元图标）
     - 备忘录：`<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline>`（文档图标）
     - 汇报：`<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>`（麦克风图标）
     - 作息：`<circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline>`（时钟图标）
     - 睡眠：`<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>`（月亮图标）
   - `{{todo_cards}}` → 待确认项的卡片HTML（使用 `.todo-item` 格式，无需图标）
   - `{{done_count}}` → 已完成数量
   - `{{total_count}}` → 总数量（固定16）
   - `{{skill_tags}}` → 所有可用技能的标签HTML（如 `<span class="skill-tag">卡路里</span><span class="skill-tag">居家管家</span>...`）
   - 可用技能（健康类：卡路里/作息管家，生活类：居家管家/饼干记账/私家大厨，学习工作类：备忘录/勋章/学习系统/学习规划师/面试管家，其他：录音机）：卡路里、作息管家、居家管家、饼干记账、私家大厨、备忘录、勋章、学习系统、学习规划师、面试管家、录音机

3. **AI自由发挥**：
   - 保持简约浅色系 Apple 风格
   - 卡片圆角、阴影
   - 字体大小按规范（主文字 32px）
   - 装饰元素简洁

### Step 4：Playwright截图

1. 保存HTML到临时文件（/tmp/daily_check_{timestamp}.html）
2. 使用 `scripts/screenshot.py` 截图：
   ```bash
   python3 scripts/screenshot.py <html_path> <output_path> 1200 1
   ```
   - 参数1：HTML文件路径
   - 参数2：输出图片路径
   - 参数3：viewport_width = 1200
   - 参数4：scale = 1（1:1截图，不缩放）
3. 截图保存到：`~/.openclaw/media/qqbot/daily_check_{timestamp}.png`

### Step 5：发送图片

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

### Step 6：文字补充输出

发送图片后，用语言补充输出当次检查的完整汇报，按以下顺序：

1. **开场**：简要说明这是今日第X次检查
2. **已完成项**：逐一念出已完成的项目及其数据
3. **待确认项**：逐一念出待确认的项目
4. **总结**：本次检查X项已完成，X项待确认
5. **引导**：想了解更多技能用法？问「XX技能 支持哪些使用场景」

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
- 16个调度子任务顺序按上面列表执行
- 展示数据时用实际日期（如"05月25日 · 周一"）
- HTML中AI可以自由发挥视觉效果，但必须保持简约浅色系 Apple 风格
- 字体大小规范：主文字 32px，副文字 26-28px
- 截图必须 1:1（scale=1），不要缩放
- 查询睡眠后必须说"千里之行，始于足下"
- 重点关注今日运动情况
- 页面底部增加「探索更多技能」提示区，展示所有可用技能列表