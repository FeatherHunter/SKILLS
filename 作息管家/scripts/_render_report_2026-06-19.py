#!/usr/bin/env python3
"""
渲染 2026-06-19 作息报告 HTML
"""
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

with open('/tmp/report_data_2026-06-19.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']
hours = data['hours']
cat_minutes = data['cat_minutes']
total_minutes = data['total_minutes']
total_hours = total_minutes / 60
sleep_records = data['sleep_records']
main_sleep = data['main_sleep']
meal_records = data['meal_records']
health_records = data['health_records']
work_records = data['work_records']
commute_records = data['commute_records']

# 颜色 & emoji
color_map = {
    "睡眠": "#5E5CE6", "工作": "#007AFF", "学习": "#34C759", "运动": "#FF9500",
    "通勤": "#64D2FF", "餐饮": "#FF9F0A", "娱乐": "#AF52DE", "社交": "#FF2D55",
    "休闲": "#30D158", "健康": "#FF3B30", "洗漱": "#5AC8FA", "兴趣爱好": "#BF8F5F",
    "居家": "#BF8F5F", "家政家务": "#A2845E", "居家管理": "#A2845E",
    "家务": "#A2845E", "生活": "#8E8E93", "未知": "#8E8E93", "休息": "#8E8E93",
    "其他": "#8E8E93",
}
emoji_map = {
    "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
    "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
    "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿", "兴趣爱好": "🎨",
    "居家": "🏠", "家政家务": "🧹", "居家管理": "🧹",
    "家务": "🧹", "生活": "🌱", "未知": "❓", "休息": "🛋️",
    "其他": "📌",
}

# 排序分类（按时长倒序）
sorted_cats = sorted(cat_minutes.items(), key=lambda x: -x[1])

# ============ HTML 渲染 ============
def fmt_dur(mins):
    return f"{mins//60}小时{mins%60}分钟" if mins % 60 else f"{mins//60}小时"

def cat_emoji(c):
    return emoji_map.get(c, "📌")
def cat_color(c):
    return color_map.get(c, "#8E8E93")

# 渲染分类摘要
summary_html = []
for cat, mins in sorted_cats:
    emoji = cat_emoji(cat)
    color = cat_color(cat)
    pct = mins / total_minutes * 100
    summary_html.append(f'''    <div class="summary-item">
      <span class="emoji">{emoji}</span>
      <div class="info">
        <div class="cat">{cat}</div>
        <div class="dur">{fmt_dur(mins)}</div>
        <div class="bar"><div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div></div>
      </div>
    </div>''')
summary_html = '\n'.join(summary_html)

# 计算时间轴：使用每小时主导分类（按分钟数覆盖最多）
hour_cats = [None] * 24
hour_minutes = [defaultdict(int) for _ in range(24)]
for r in records:
    final_cat = r['category']
    try:
        h_start = int(r['time_start'].split(':')[0])
        s_min = int(r['time_start'].split(':')[1])
        if r['time_end'] == '23:59':
            e_min_total = 23 * 60 + 59
        elif r['time_end'] == '24:00':
            e_min_total = 24 * 60
        else:
            eh, em = map(int, r['time_end'].split(':'))
            e_min_total = eh * 60 + em
        s_min_total = h_start * 60 + s_min
        cur = s_min_total
        while cur < e_min_total:
            h = cur // 60
            if h < 24:
                next_hour = (h + 1) * 60
                covered = min(next_hour, e_min_total) - cur
                hour_minutes[h][final_cat] += covered
                cur = next_hour
            else:
                break
    except Exception as e:
        pass

# 取每小时主导分类
for h in range(24):
    if hour_minutes[h]:
        hour_cats[h] = max(hour_minutes[h].items(), key=lambda x: x[1])[0]
    else:
        hour_cats[h] = hours[h] or '休息'

# 渲染时间轴
timeline_html = []
for h in range(24):
    cat = hour_cats[h] or '休息'
    color = cat_color(cat)
    timeline_html.append(f'    <div class="timeline-block" style="background:{color}"><div class="tip">{h:02d}:00 {cat}</div></div>')
timeline_html = '\n'.join(timeline_html)

# 渲染时间轴图例（去重，基于新算法）
used_cats = []
for h in range(24):
    cat = hour_cats[h] or '休息'
    if cat not in used_cats:
        used_cats.append(cat)
legend_html = []
for cat in used_cats:
    color = cat_color(cat)
    legend_html.append(f'    <div class="legend-item"><div class="legend-dot" style="background:{color}"></div>{cat}</div>')
legend_html = '\n'.join(legend_html)

# 周几
weekday_map = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
dt = datetime.strptime(data['date'], '%Y-%m-%d')
weekday = weekday_map[dt.weekday()]
date_cn = f"{dt.year}年{dt.month}月{dt.day}日"

# ============ 当日亮点 ============
highlights_html = '''    <div class="highlight-row">
      <span class="h-emoji">😴</span>
      <div>
        <div class="h-text">睡眠爆棚 9h6m：凌晨主睡眠 02:08~08:05 长达 5h57m，加上 00:53~02:08 1h15m + 09:00~10:51 1h51m 的回笼觉 + 23:56~23:59 入睡。4 段睡眠总计 9h6m（占全天 37.9%），是近期最长的休息日。睡眠质量提升明显</div>
        <div class="h-time">02:08~08:05 主睡眠 / 09:00~10:51 回笼觉</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🍽️</span>
      <div>
        <div class="h-text">自助餐盛宴 2h42m：17:40~20:22 百家湖自助餐，包含星冰乐；卡路里记录估算 ≈2000 大卡。这是周末放纵日的典型节奏——大餐 + 完整休息 + 朋友相聚</div>
        <div class="h-time">17:40~20:22 百家湖自助餐</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎨</span>
      <div>
        <div class="h-text">居家管家深度使用 2h17m：7 段操作共 137min（占全天 9.5%）。上午集中录入新物品（复古撞色扣盖收纳盒 + 整理物品），晚上查询客厅健身箱物品、要HTML发微信、等待HTML（25min）。居家管家已成为日常管理工具，但 HTML 推送链路还有问题</div>
        <div class="h-time">12:03~14:10 / 21:04~21:43 两段集中操作</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">📚</span>
      <div>
        <div class="h-text">深度学习 AI 功能 1h50m：16:05~17:40 95min 连续咨询 AI 身份（你是谁）+ mmx query 网络查询能力。22:08~22:23 15min 查今日支出。学习驱动力强，对技术细节有钻研习惯。考虑整理成 AI 学习笔记归档</div>
        <div class="h-time">16:05~17:40 主学习段</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🏥</span>
      <div>
        <div class="h-text">卡路里管理活跃日 1h8m：5 段卡路里记录/咨询共 68min（占全天 4.7%）。14:25~15:02 37min 详细记录（3菜包+1肉包）；晚上 21:43~22:08 25min 算 207 单独吃 1200g 热量。健康数据记录很认真，但咨询多于最终决策，思考优化方向</div>
        <div class="h-time">14:25~15:02 主记录 / 21:43~22:08 计算</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">💕</span>
      <div>
        <div class="h-text">周五兄弟相聚：15:02~15:29 通勤去南京南站与王大为汇合（27min）；晚上 20:22~20:56 逛街 34min。友情时间虽不长但有质量，符合周五下班后的放松节奏</div>
        <div class="h-time">15:02~15:29 通勤 / 20:22~20:56 逛街</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎮</span>
      <div>
        <div class="h-text">娱乐+休闲占 5h32m（休闲 4h43m + 娱乐 49min）：全天无工作（0min），周五纯休息日。娱乐主要是 14:10~14:25 看照片备份（去年今年对比 15min），休闲主要是起床后自由活动 + 躺床休息等过渡时间</div>
        <div class="h-time">全天 0h 工作，纯休息日</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">📌</span>
      <div>
        <div class="h-text">饼干记账 37min：15:29~16:05 详细记账 36min（3元+瑞幸咖啡 9.9元/10.9元），22:23~22:24 快速记地铁 7元。日常收支管理稳健，单日合计记账 2 次，节奏合理</div>
        <div class="h-time">15:29~16:05 / 22:23~22:24</div>
      </div>
    </div>'''

# ============ 睡眠分析 ============
sleep_total_min = cat_minutes.get('睡眠', 0)
sleep_h = sleep_total_min // 60
sleep_m = sleep_total_min % 60

sleep_html = f'''    <div class="highlight-row">
      <span class="h-emoji">&#x1F319;</span>
      <div>
        <div class="h-text">凌晨主睡眠 02:08~08:05 5h57m：从 00:53 说"晚安哈"后真正入睡，到 08:05"醒咯"起床信号，中间持续 5h57m 无消息。这是核心睡眠段，质量应该不错</div>
        <div class="h-time">00:53 入睡 → 08:05 起床</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F634;</span>
      <div>
        <div class="h-text">回笼觉 1h51m：09:00~10:51 起床 1h 后又睡下，"九点继续睡，睡到了现在 10:50 哈哈"。典型的周末赖床节奏，补充睡眠让总量达到 9h6m。睡眠结构健康（非被迫睡眠，而是主动补充）</div>
        <div class="h-time">09:00~10:51 自愿回笼觉</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4A4;</span>
      <div>
        <div class="h-text">凌晨床上休息 53min（00:00~00:53）：接续 2026-06-18 23:28 躺床，是赖床阶段而非真正睡眠。说明用户从 23:28 就开始为入睡做准备，但到 00:53 才说晚安入睡，中间有 1h25m 清醒躺床。这是"拖延入睡"的信号——建议建立更明确的睡前流程</div>
        <div class="h-time">⚠️ 23:28 躺床 → 00:53 入睡，中间 1h25m 清醒</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4CA;</span>
      <div>
        <div class="h-text">总睡眠 {sleep_h}h{sleep_m}m，超过 7-9h 推荐范围上限（9h）。考虑到昨天出行（2026-06-18 端午双城出行 6h32m 通勤），今天长睡眠是合理的身体修复。但平时应该维持在 7-8h，过度睡眠反而可能带来惰性</div>
        <div class="h-time">总 {sleep_h}h{sleep_m}m（4 段）</div>
      </div>
    </div>'''

# ============ 改善建议 ============
suggest_html = '''    <div class="highlight-row">
      <span class="h-emoji">&#x1F634;</span>
      <div>
        <div class="h-text">入睡拖延问题 ⚠️：昨晚 23:28 躺床 → 00:53 才说晚安，中间 1h25m 是清醒躺床（赖床/刷手机）。这与入睡困难或睡眠仪式不清有关。建议：① 23:00 后关大灯只留小灯/夜灯 ② 躺床前 30min 不看手机（屏幕蓝光抑制褪黑素） ③ 建立固定睡前流程（洗漱→冥想 5min→躺床→闭眼）。今晚（2026-06-19 23:56 已入睡）看看是否改善</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F37D;&#xFE0F;</span>
      <div>
        <div class="h-text">自助餐日卡路里管理：今天 17:40~20:22 吃了 2h42m 自助餐，估算 ≈2000 大卡（包含星冰乐）。配上下午的卡路里记录（14:25~15:02 详细记录），说明用户对热量敏感。建议：① 自助餐前先喝 500ml 水 ② 按"蔬菜→蛋白→碳水"顺序取餐 ③ 每道菜只取 1 小份尝鲜。这样既能享受又能控制摄入</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4F1;</span>
      <div>
        <div class="h-text">居家管家 HTML 推送链路问题 ⚠️：晚上 21:15~21:43 共 28min 用户在等待 HTML 文件生成 + 抱怨没收到。这是推送链路不稳定导致。建议排查：① 模板渲染是否完整 ② 微信/QQ 媒体上传路径 ③ 异步通知机制。这影响居家管家的使用体验</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4DA;</span>
      <div>
        <div class="h-text">AI 学习笔记归档建议：今天 16:05~17:40 95min 深度咨询 AI 身份 + mmx query 网络查询能力，加上 22:08~22:23 查今日支出。学习内容有价值但未沉淀。建议：① 在「学习系统」技能中新建"AI 工具探索"主题 ② 把"我是谁""mmx query 是否支持网络查询"等关键问答整理成 Q&A 卡片 ③ 定期回顾（每周/月）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3E0;</span>
      <div>
        <div class="h-text">居家管家数据持续完善：今天 12:03~14:10 集中录入新物品（复古撞色扣盖收纳盒，位置客厅健身箱）+ 整理物品 + 查询快递 + 物品位置确认。这是把日常生活系统化的好习惯。建议继续：① 给每个物品加标签（材质/用途/使用频率）② 定期 review（季度盘点）③ 结合位置和照片做可视化</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F634;&#x200D;&#x1F4A8;</span>
      <div>
        <div class="h-text">回笼觉节奏观察：今天 09:00~10:51 起床 1h 后又睡了 1h51m，加上总睡眠 9h6m。这与昨天 2026-06-18 端午出行 + 背部疼痛睡眠分两段有关。身体在主动修复。明天（周六）如果没事，建议 10:30 之前起床，避免回笼觉形成惯性</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F465;</span>
      <div>
        <div class="h-text">社交维护：今天与王大为相聚（通勤 27min + 逛街 34min + 自助餐 2h42m 共 3h43m）。兄弟情谊 + 自助餐放松，是健康社交。继续保持每周至少 1 次深度社交（朋友/家人）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x2705;</span>
      <div>
        <div class="h-text">保留的好习惯：① 周五纯休息（0h 工作）身心充电 ② 长睡眠 9h6m 充分修复 ③ 自助餐 + 朋友相聚情绪价值高 ④ 卡路里管理细致 ⑤ 居家管家持续完善 ⑥ AI 学习驱动 ⑦ 饼干记账每日 2 次 ⑧ 睡前刷手机赖床也算"半休息"，整体状态放松</div>
      </div>
    </div>'''

# ============ 完整 HTML ============
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>作息报告 - {date_cn}（{weekday}）</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","SF Pro Display","PingFang SC","Microsoft YaHei",sans-serif;background:#f5f5f7;color:#1d1d1f;line-height:1.6;-webkit-font-smoothing:antialiased}}
.container{{max-width:720px;margin:0 auto;padding:24px 16px}}
.header{{text-align:center;padding:32px 0 24px}}
.header h1{{font-size:28px;font-weight:700;letter-spacing:-.5px}}
.header .date{{font-size:15px;color:#86868b;margin-top:4px}}
.header .weekday{{display:inline-block;font-size:12px;font-weight:500;color:#fff;background:#007AFF;border-radius:12px;padding:2px 10px;margin-top:8px}}
.card{{background:#fff;border-radius:14px;padding:24px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.card h2{{font-size:17px;font-weight:600;margin-bottom:16px;display:flex;align-items:center;gap:8px}}
.card h2 .icon{{font-size:20px}}
.summary-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
.summary-item{{display:flex;align-items:center;padding:12px 14px;background:#f5f5f7;border-radius:10px;gap:10px}}
.summary-item .emoji{{font-size:22px;width:32px;text-align:center;flex-shrink:0}}
.summary-item .info{{flex:1;min-width:0}}
.summary-item .cat{{font-size:13px;font-weight:500;color:#1d1d1f}}
.summary-item .dur{{font-size:12px;color:#86868b;margin-top:1px}}
.summary-item .bar{{height:4px;background:#e5e5e5;border-radius:2px;margin-top:6px;overflow:hidden}}
.summary-item .bar-fill{{height:100%;border-radius:2px;transition:width .6s ease}}
.total-row{{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;background:#f5f5f7;border-radius:10px;margin-top:12px}}
.total-row .label{{font-size:14px;font-weight:500;color:#1d1d1f}}
.total-row .value{{font-size:20px;font-weight:700;color:#007AFF}}
.total-row .check{{font-size:14px;color:#34c759;margin-left:6px}}
.timeline{{display:flex;gap:2px;height:40px;border-radius:8px;overflow:hidden;margin-bottom:8px}}
.timeline-block{{flex:1;position:relative;cursor:pointer;transition:opacity .15s}}
.timeline-block:hover{{opacity:.8}}
.timeline-block .tip{{display:none;position:absolute;bottom:calc(100% + 6px);left:50%;transform:translateX(-50%);background:#1d1d1f;color:#fff;font-size:11px;padding:4px 8px;border-radius:6px;white-space:nowrap;z-index:10;pointer-events:none}}
.timeline-block:hover .tip{{display:block}}
.timeline-labels{{display:flex;justify-content:space-between;font-size:10px;color:#86868b;padding:0 2px}}
.legend{{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}}
.legend-item{{display:flex;align-items:center;gap:4px;font-size:11px;color:#86868b}}
.legend-dot{{width:10px;height:10px;border-radius:3px;flex-shrink:0}}
.highlights{{display:flex;flex-direction:column;gap:10px}}
.highlight-row{{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;background:#f5f5f7;border-radius:10px}}
.highlight-row .h-emoji{{font-size:18px;flex-shrink:0;margin-top:1px}}
.highlight-row .h-text{{font-size:13px;color:#1d1d1f;line-height:1.5}}
.highlight-row .h-time{{font-size:12px;color:#86868b;margin-top:2px}}
.footer{{text-align:center;padding:20px 0;font-size:11px;color:#86868b}}
@media(max-width:480px){{.summary-grid{{grid-template-columns:1fr}}.container{{padding:16px 12px}}}}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>每日作息报告</h1>
  <div class="date">{date_cn}</div>
  <span class="weekday">{weekday}</span>
</div>

<div class="card">
  <h2><span class="icon">&#x1F4CA;</span> 时间分配</h2>
  <div class="summary-grid">
{summary_html}
  </div>
  <div class="total-row">
    <span class="label">总计</span>
    <span><span class="value">{fmt_dur(total_minutes)}</span><span class="check">&#x2713;</span></span>
  </div>
</div>

<div class="card">
  <h2><span class="icon">&#x1F550;</span> 24小时时间轴</h2>
  <div class="timeline">
{timeline_html}
  </div>
  <div class="timeline-labels">
    <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>23:59</span>
  </div>
  <div class="legend">
{legend_html}
  </div>
</div>

<div class="card">
  <h2><span class="icon">&#x2B50;</span> 当日亮点</h2>
  <div class="highlights">
{highlights_html}
  </div>
</div>

<div class="card">
  <h2><span class="icon">&#x1F634;</span> 睡眠分析</h2>
  <div class="highlights">
{sleep_html}
  </div>
</div>

<div class="card">
  <h2><span class="icon">&#x1F4A1;</span> 改善建议</h2>
  <div class="highlights">
{suggest_html}
  </div>
</div>

<div class="footer">
  作息管家 · 自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M")} · 共 {data['total_records']} 个记录块
</div>

</div>
</body>
</html>'''

REPORT_PATH = Path('/mnt/d/2Study/StudyNotes/SKILLS/作息管家/reports/2026-06-19.html')
REPORT_PATH.write_text(html, encoding='utf-8')
print(f"✓ HTML 报告已生成: {REPORT_PATH}")
print(f"  文件大小: {REPORT_PATH.stat().st_size} bytes")