#!/usr/bin/env python3
"""
渲染 2026-06-17 作息报告 HTML
"""
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

with open('/tmp/report_data_2026-06-17.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']

# 智能分类映射 (与 gen 脚本一致)
def refine_category(rec):
    """根据 activity 内容细化分类"""
    orig_cat = rec['category']
    activity = rec['activity']
    if orig_cat == '休息':
        if rec['duration_minutes'] >= 60:
            return '睡眠'
        if any(kw in activity for kw in ['睡眠', '睡觉', '午睡', '躺床休息']):
            return '睡眠'
        if rec['duration_minutes'] <= 2:
            return '休闲'
        return '休闲'
    return orig_cat

# 应用 refine 到 records
records = [
    {**r, 'category': refine_category(r)} for r in records
]
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
    "居家": "#BF8F5F", "家务": "#A2845E", "生活": "#8E8E93", "未知": "#8E8E93", "休息": "#8E8E93",
}
emoji_map = {
    "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
    "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
    "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿", "兴趣爱好": "🎨",
    "居家": "🏠", "家务": "🧹", "生活": "🌱", "未知": "❓", "休息": "🛋️",
}

# 排序分类（按时长倒序）
sorted_cats = sorted(cat_minutes.items(), key=lambda x: -x[1])

# ============ HTML 渲染 ============
def fmt_dur(mins):
    return f"{mins//60}小时{mins%60}分钟" if mins % 60 else f"{mins//60}小时"

# 计算总占比
max_pct = max(cat_minutes.values()) / total_minutes * 100 if total_minutes else 0

# 找占主导的活动
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

# 重新计算时间轴：使用每小时**主导**分类（按分钟数覆盖最多）
hour_cats = [None] * 24
hour_minutes = [defaultdict(int) for _ in range(24)]
for r in records:
    final_cat = r['category']  # 已应用 refine
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
        # 计算每个小时覆盖的分钟数
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
    label = cat[:2]
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
# 通勤拆分: 早通勤07:29-08:19 + 中午高铁+接送11:20-11:26 + 下午14:43-19:34 = 6h4m
# 计算通勤总时间
commute_min = cat_minutes.get('通勤', 0)
# 睡眠拆分: 00:00-06:15 (375min) + 06:15-06:38 (23min) + 14:39-16:05 (86min) + 22:24-23:59 (95min) = 579min

highlights_html = '''    <div class="highlight-row">
      <span class="h-emoji">🚄</span>
      <div>
        <div class="h-text">如皋往返出行日：通勤 6h4m 占全天 25.3%。早通勤 47min（07:29-08:19 骑车+地铁，含小黄车摔跤）→ 候车 52min（08:19-09:11 进站+排队）→ 高铁 52min（09:11-10:03 C424南京→如皋）→ 中午接送 + 返家 2h2m（11:20-11:26 + 12:43-14:39）→ 晚回家 1h31m（18:03-19:34 文峰大世界→家）</div>
        <div class="h-time">07:29~08:19 / 09:11~10:03 / 11:20~14:39 / 18:03~19:34</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎨</span>
      <div>
        <div class="h-text">兴趣爱好 3h12m 是核心：①修行思考 37min（10:03-10:40 元母意程）②看练舞 1h53m（16:10-18:03 文峰大世界看小孩练舞 + 元母意程）③AI 交互 42min（19:54-20:36 查车票/佛学/悟了大师对话）。修行 + 文化关怀 + AI 探索三线并行</div>
        <div class="h-time">10:03~10:40 / 16:10~18:03 / 19:54~20:36</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🛋️</span>
      <div>
        <div class="h-text">休闲 + 居家 2h30m：①记账 51min（06:46-06:59 联通话费 + 20:36-21:14 支出记录）②蛋糕零食记录 40min（10:40-11:20）③家务 30min（06:59-07:29 换猫水猫砂/倒垃圾/收拾）④躺床休息 29min（21:14-21:43）。碎片时间安排得当，记账习惯延续</div>
        <div class="h-time">06:46~07:29 / 10:40~11:20 / 20:36~21:43</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🍽️</span>
      <div>
        <div class="h-text">餐饮 1h37m：①午餐 1h17m（11:26-12:43 吾悦广场餐厅点餐吃饭 含步行 + 等位 + 用餐）②晚餐 20min（19:34-19:54 在家与AI交互创作歌曲时吃）。午餐用餐环境正常，晚餐高效</div>
        <div class="h-time">11:26~12:43 / 19:34~19:54</div>
      </div>
    </div>'''

# ============ 睡眠分析 ============
sleep_html = '''    <div class="highlight-row">
      <span class="h-emoji">&#x1F319;</span>
      <div>
        <div class="h-text">夜间主睡眠：6小时15分钟（00:00 ~ 06:15），跨夜接续 2026-06-16 22:56 入睡，实际睡眠时长 7h19m。起床时间 06:15 偏早（昨天 22:56 入睡时间正常）</div>
        <div class="h-time">⚠️ 起床偏早，主睡眠时长偏短</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F634;</span>
      <div>
        <div class="h-text">午睡：1小时26分钟（14:39 ~ 16:05），在如皋家中。出行日午睡有助于恢复精力</div>
        <div class="h-time">✓ 午睡时长合理</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4A4;</span>
      <div>
        <div class="h-text">夜间入睡：22:24~23:59（1h35m），收到俯卧撑提醒后准备睡觉。2026-06-18 整天无消息，推断 22:24 后即入睡</div>
        <div class="h-time">✓ 入睡时段正常</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4CA;</span>
      <div>
        <div class="h-text">总睡眠 9小时39分钟（凌晨主睡眠 6h15m + 醒后躺床 23min + 午睡 1h26m + 22:24 后入睡 1h35m），占全天 40.2%，略超 9h 推荐上限但出行日合理（含长途交通恢复需求）</div>
        <div class="h-time">✓ 出行日睡眠合理</div>
      </div>
    </div>'''

# ============ 改善建议 ============
suggest_html = '''    <div class="highlight-row">
      <span class="h-emoji">🚴</span>
      <div>
        <div class="h-text">小黄车摔跤事故关注：07:30 通勤时骑小黄车摔了一跤。需检查膝盖/手肘是否有擦伤、淤青。如果有不适，洗澡和俯卧撑时注意护伤。可考虑通勤改用更稳的共享单车或地铁短驳</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🚄</span>
      <div>
        <div class="h-text">出行效率优化：6h4m 通勤占全天 25.3%，是典型「双城出行日」。如果类似出行频繁，可考虑：①提前买好往返票 + 早班车次 ②出发前做好行程清单 ③在高铁上做一些轻量任务（修行/看书/AI 交互），不浪费通勤时间</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">💼</span>
      <div>
        <div class="h-text">工作 0h 是出行日正常状态：今天无工作记录，与出行计划相符。但全天 24h 仅有 3h12m 兴趣爱好 + 2h30m 休闲 + 1h37m 餐饮，剩余 6h41m 主要被通勤（6h4m）+ 睡眠（9h39m 包含 4h 多段睡眠）+ 洗漱占据。出行日的「时间颗粒度」可被进一步利用</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🧘</span>
      <div>
        <div class="h-text">修行思考 1h53m（10:03-10:40 + 16:10-18:03 期间）是核心亮点：在文峰大世界看练舞时同步练习元母意程，是修行 + 家庭关怀的巧妙结合。建议把这种「并行修行」模式常态化，例如日常陪伴家人时同步练功</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">📱</span>
      <div>
        <div class="h-text">AI 交互 42min：与悟了大师讨论佛学/查车票是有价值的探索（19:54-20:36）。可在出行日利用碎片时间增加与悟了大师的对话密度，深化心结梳理</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">✅</span>
      <div>
        <div class="h-text">保留的好习惯：①出行的车票/检票口提前查询；②午睡恢复精力；③睡前有准备动作（洗漱+收到俯卧撑提醒）；④修行 + 家庭关怀双线并行；⑤记账习惯延续（联通话费/蛋糕零食/支出）</div>
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

REPORT_PATH = Path('/mnt/d/2Study/StudyNotes/SKILLS/作息管家/reports/2026-06-17.html')
REPORT_PATH.write_text(html, encoding='utf-8')
print(f"✓ HTML 报告已生成: {REPORT_PATH}")
print(f"  文件大小: {REPORT_PATH.stat().st_size} bytes")
