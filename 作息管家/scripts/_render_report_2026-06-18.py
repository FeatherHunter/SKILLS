#!/usr/bin/env python3
"""
渲染 2026-06-18 作息报告 HTML
"""
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

with open('/tmp/report_data_2026-06-18.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']
hours = data['hours']
cat_minutes = data['cat_minutes']
total_minutes = data['total_minutes']
total_hours = total_minutes / 60
sleep_records = data['sleep_records']
main_sleep = data['main_sleep']

# 颜色 & emoji
color_map = {
    "睡眠": "#5E5CE6", "工作": "#007AFF", "学习": "#34C759", "运动": "#FF9500",
    "通勤": "#64D2FF", "餐饮": "#FF9F0A", "娱乐": "#AF52DE", "社交": "#FF2D55",
    "休闲": "#30D158", "健康": "#FF3B30", "洗漱": "#5AC8FA", "兴趣爱好": "#BF8F5F",
    "居家": "#BF8F5F", "家政家务": "#A2845E", "居家管理": "#A2845E",
    "家务": "#A2845E", "生活": "#8E8E93", "未知": "#8E8E93", "休息": "#8E8E93",
}
emoji_map = {
    "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
    "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
    "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿", "兴趣爱好": "🎨",
    "居家": "🏠", "家政家务": "🧹", "居家管理": "🧹",
    "家务": "🧹", "生活": "🌱", "未知": "❓", "休息": "🛋️",
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
      <span class="h-emoji">🚴</span>
      <div>
        <div class="h-text">双城出行日 通勤 6h32m 占全天 27.2%：①如皋→南京 高铁段 4h34m（12:22-16:56 含如皋等高铁72min + 高铁三段 28+80+25min + 到站聊天15min + 南京地铁+回家 54min）②接人来回 2h25m（19:58-20:16 出发 18min + 20:43-22:23 南京站等待+接人+回家 100min）。全天交通时间超 1/4，端午出行典型</div>
        <div class="h-time">12:22~16:56 / 19:58~22:23</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🏥</span>
      <div>
        <div class="h-text">凌晨背部健康事件 42min（04:06-04:48）：两年病史深度讨论，已排除强直性脊柱炎，定性为腰肌劳损+筋膜粘连。讨论了睡姿/床垫/枕头/久坐等6+项因素，输出就医清单与日常缓解方案。用户最终选择「今天不去医院，在如皋」延后就医</div>
        <div class="h-time">04:06~04:48 凌晨深度健康讨论</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎨</span>
      <div>
        <div class="h-text">端午文化体验 2h32m（08:11-10:43）：在龙游湖看赛龙舟 8:30 正式开始，152min 覆盖往返+观赛全程。传统文化参与 + 家庭团聚（人在如皋家），情绪价值高</div>
        <div class="h-time">08:11~10:43 龙游湖赛龙舟</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">📦</span>
      <div>
        <div class="h-text">居家管家录入 27min（20:16-20:43）5个批次：①3件防晒衣（文字+3张照）②清理 ③5件运动T恤（文字+前3张照）④剩余2张照片+确认 ⑤2件西装/衬衫。系统化衣物管理推进有条不紊，与接人事务并行处理</div>
        <div class="h-time">20:16~20:43 5批次录入</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🍽️</span>
      <div>
        <div class="h-text">餐饮 1h57m：①早餐 21min（07:50-08:11 如皋家盘水面+蛋饼 13元）②午餐+查账 1h36m（10:46-12:22 午餐图片+查2026支出收入）。早餐高效，午餐因查账延长但有意义</div>
        <div class="h-time">07:50~08:11 / 10:46~12:22</div>
      </div>
    </div>'''

# ============ 睡眠分析 ============
sleep_html = '''    <div class="highlight-row">
      <span class="h-emoji">&#x1F319;</span>
      <div>
        <div class="h-text">夜间主睡眠分两段：① 00:00-04:06 凌晨睡眠 4h6m（接续 2026-06-17 22:24 入睡）② 04:48-07:50 重新入睡 3h2m（讨论完背部病情后）。两段总计 7h8m，跨凌晨 + 背部疼醒分割</div>
        <div class="h-time">⚠️ 凌晨 4:06 因背部疼醒</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F634;</span>
      <div>
        <div class="h-text">总睡眠 7h8m：凌晨主睡眠 4h6m + 醒后躺床 + 重新入睡 3h2m。无午睡记录（出行日无固定午休场所），睡眠分两段是异常信号</div>
        <div class="h-time">⚠️ 睡眠被背部疼痛打断</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4A4;</span>
      <div>
        <div class="h-text">夜间入睡：23:28~23:59 休闲段（31min）后入睡。躺在床上赖着，未明确「晚安」信号；22:23~23:21 58min 在家躺床休息</div>
        <div class="h-time">22:23 后准备入睡</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4CA;</span>
      <div>
        <div class="h-text">睡眠质量待提升：7h8m 总量达标（接近 7-9h 推荐范围），但被背部疼痛分割成两段，质量打折扣。背部健康是 2 年多的慢性问题，需要尽快系统化就医</div>
        <div class="h-time">⚠️ 睡眠结构异常</div>
      </div>
    </div>'''

# ============ 改善建议 ============
suggest_html = '''    <div class="highlight-row">
      <span class="h-emoji">&#x1F3E5;</span>
      <div>
        <div class="h-text">背部健康优先处理 ⚠️：04:06-04:48 已与 AI 完整讨论过两年病史与就医方案，今天因在如皋未去医院。建议回南京后 ①尽快去三甲医院骨科/疼痛科就诊 ②带上今日整理的病史清单（腰肌劳损+筋膜粘连倾向） ③做腰椎 MRI 排除椎间盘问题。凌晨疼醒 2 年多不是小事</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F6B4;</span>
      <div>
        <div class="h-text">久坐+姿势与背部健康直接相关：作为 Android 工程师长期伏案工作，是腰部问题的高危因素。建议 ①每 1 小时起身活动 5-10 分钟 ②工位配置腰靠 ③显示器调高到视线平行 ④考虑站立办公桌。这些改变比按摩/膏药更治本</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3DF;&#xFE0F;</span>
      <div>
        <div class="h-text">床垫/枕头排查：用户已用过硬床且软床也不适，可能是床垫支撑力问题。建议 ①回顾最近一次换床垫的时间（5年+未换建议换） ②测试仰卧时腰椎是否能保持平直 ③枕头高度是否合适（仰卧时颈椎与胸椎应在同一平面）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F684;</span>
      <div>
        <div class="h-text">端午双城出行效率观察：6h32m 通勤占 27.2%，其中如皋高铁段就占 4h34m。短期无法压缩，但可在高铁上做轻量任务：①看练舞视频（兴趣爱好）②佛学/修行（悟了大师）③算账/记账（饼干记账）。今日已部分做到（聊天+算账）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4BC;</span>
      <div>
        <div class="h-text">工作 0h 正常：端午假期出行日无工作记录符合预期。但 5 月工资 6.20 发放的话题已和 AI 讨论过（13:41 消息），今天出行中也有 14:02 重算 2026 收支，说明收入管理意识强。继续保持月度收支复盘</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4F1;</span>
      <div>
        <div class="h-text">居家管家 27min 录入高密度：5 个批次含文字+图片同步推进，证明居家管家技能实用性得到验证。端午回家可继续录入剩余衣物，把如皋家+南京住处两个衣橱都系统化</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x2705;</span>
      <div>
        <div class="h-text">保留的好习惯：①端午陪伴家人 + 参与龙舟赛 ②凌晨健康讨论不拖延 ③如皋家饮食记录（盘水面+蛋饼 13元）④出行前查 2026 收支 ⑤居家管家衣物系统化 ⑥高铁上碎片化算账 ⑦晚上接人事务有条不紊</div>
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

REPORT_PATH = Path('/mnt/d/2Study/StudyNotes/SKILLS/作息管家/reports/2026-06-18.html')
REPORT_PATH.write_text(html, encoding='utf-8')
print(f"✓ HTML 报告已生成: {REPORT_PATH}")
print(f"  文件大小: {REPORT_PATH.stat().st_size} bytes")
