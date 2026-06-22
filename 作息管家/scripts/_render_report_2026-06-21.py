#!/usr/bin/env python3
"""
渲染 2026-06-21 作息报告 HTML
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

with open('/tmp/report_data_2026-06-21.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']
hours = data['hours']
cat_minutes = data['cat_minutes']
total_minutes = data['total_minutes']
total_hours = total_minutes / 60
sleep_records = data['sleep_records']
main_sleep = data['main_sleep']
meal_records = data['meal_records']
work_records = data['work_records']
commute_records = data['commute_records']
study_records = data['study_records']
leisure_records = data['leisure_records']
entertainment_records = data['entertainment_records']

# 颜色 & emoji
color_map = {
    "睡眠": "#5E5CE6", "工作": "#007AFF", "学习": "#34C759", "运动": "#FF9500",
    "通勤": "#64D2FF", "餐饮": "#FF9F0A", "娱乐": "#AF52DE", "社交": "#FF2D55",
    "休闲": "#30D158", "健康": "#FF3B30", "洗漱": "#5AC8FA", "兴趣爱好": "#BF8F5F",
    "居家": "#BF8F5F", "家政家务": "#A2845E", "居家管理": "#A2845E",
    "家务": "#A2845E", "生活": "#8E8E93", "未知": "#8E8E93", "休息": "#8E8E93",
    "其他": "#8E8E93", "烹饪": "#FF9F0A", "生活管理": "#A2845E",
    "卡路里": "#FF3B30", "记账": "#64D2FF",
}
emoji_map = {
    "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
    "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
    "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿", "兴趣爱好": "🎨",
    "居家": "🏠", "家政家务": "🧹", "居家管理": "🧹",
    "家务": "🧹", "生活": "🌱", "未知": "❓", "休息": "🛋️",
    "其他": "📌", "烹饪": "🍳", "生活管理": "📌",
    "卡路里": "🏥", "记账": "📌",
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
# 睡眠总时长
sleep_total = cat_minutes.get('睡眠', 0)
sleep_h = sleep_total // 60
sleep_m = sleep_total % 60

highlights_html = f'''    <div class="highlight-row">
      <span class="h-emoji">😴</span>
      <div>
        <div class="h-text">睡眠爆表 {sleep_h}h{sleep_m}m（占全天 53.6%）：4 段睡眠总计 12h52m，远超 7-9h 推荐上限。① 00:00~02:10 凌晨前段 2h10m ② 02:10~07:00 凌晨后段 4h50m ③ 08:46~11:42 上午回笼觉 2h56m ④ 13:49~16:45 下午午睡 2h56m。这是典型的"周日补觉"模式，但睡眠过多（&gt;11h）会引发惰性、头痛、加重疲劳感，反而越睡越累</div>
        <div class="h-time">4 段睡眠：00:00~02:10 / 02:10~07:00 / 08:46~11:42 / 13:49~16:45</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">📚</span>
      <div>
        <div class="h-text">卡路里技能深度研究 3h6m：晚上 20:14~23:20 集中研究卡路里技能缺陷，包括：① 20:14~21:59 卡路里技能缺陷报告（105min）② 21:59~22:06 5个问题讨论（7min）③ 22:06~22:08 问题四最终版本（2min）④ 22:08~23:15 加载卡路里技能审查5个问题（67min）⑤ 23:15~23:20 修改方案+openclaw技能工坊（5min）。这是"用技能工坊优化技能"的高阶用法，是开发者思维</div>
        <div class="h-time">20:14~23:20 晚上集中研究</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🍽️</span>
      <div>
        <div class="h-text">餐饮时间偏长 3h31m（占 14.7%）：7 段餐饮操作 211min。包括 11:51~12:40 做饭 49min、12:40~12:54 热饭 14min、12:54~13:48 吃午饭 54min、16:45~18:03 做晚饭+吃饭 78min、18:03~18:05 吃完饭+记录 2min、20:00~20:14 吃桃子+记录 14min。其中"做饭 49min+吃 54min"午饭较慢，晚饭"焖饭+吃"78min 是因为焖饭要等</div>
        <div class="h-time">11:51~13:48 午饭 / 16:45~18:05 晚饭</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">💼</span>
      <div>
        <div class="h-text">周日零工作：今天 1 段"工作"（22:06~22:06 0min）是 claude settings.json 模型配置，仅 1 分钟的技术调整，不算真正工作。本周日彻底休息（参考昨天 2026-06-20 也是 0h 工作日），建议把周日作为「完全无工作日」固定下来</div>
        <div class="h-time">22:06 仅 1min 模型配置</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">📌</span>
      <div>
        <div class="h-text">记账+卡路里 1h56m：记账 58min（13:48 父亲节红包 + 18:05 翻墙软件 + 18:52 讨论）+ 卡路里 58min（19:02~20:00 卡路里估算 1h）。父亲节红包是节日关怀（虽然晚了几天），翻墙软件是持续支出。卡路里估算用了 1h，比前两天 6h5m 大幅减少，是进步</div>
        <div class="h-time">18:05~19:02 记账 / 19:02~20:00 卡路里</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🛋️</span>
      <div>
        <div class="h-text">休闲 1h56m：5 段。① 07:00~07:01 醒来后报告睡眠时长 1min ② 07:01~08:33 躺在床上看手机 1h32m（这是补觉的代价）③ 08:33~08:46 决定再睡 13min ④ 11:42~11:51 起床准备 9min ⑤ 23:20~23:21 躺床 1min。休闲时间主要集中在上午看手机，符合周日懒散节奏</div>
        <div class="h-time">5 段休闲：07:00~07:01 / 07:01~08:33 / 08:33~08:46 / 11:42~11:51 / 23:20~23:21</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎮</span>
      <div>
        <div class="h-text">娱乐 38min：2 段。① 23:21~23:21 看视频（安东尼2001 体验分享）0min —— 用户在 23:21 分享了观看安东尼2001 视频的体验 ② 23:21~23:59 躺床看视频+技能修改讨论 38min —— 这是按 SKILL.md「过去日期补到 23:59」规则补齐的时段（23:31 后无消息），推断为继续躺床看视频+讨论技能。安东尼2001 是经典老视频，分享视频体验是好习惯</div>
        <div class="h-time">2 段娱乐：23:21~23:21（0min）/ 23:21~23:59（38min，按规则补齐）</div>
      </div>
    </div>'''

# ============ 睡眠分析 ============
sleep_html = f'''    <div class="highlight-row">
      <span class="h-emoji">&#x1F319;</span>
      <div>
        <div class="h-text">凌晨主睡眠 00:00~07:00 共 7h00m：从 00:00 持续到 07:00，中间无中断。整段都是睡眠状态，是周日的长睡眠基础。其中 00:00~02:10 是前夜延续，02:10~07:00 是后半夜</div>
        <div class="h-time">00:00~07:00 持续 7h00m 无中断</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F634;</span>
      <div>
        <div class="h-text">回笼觉 2h56m（08:46~11:42）：醒来后看手机 1h33m，又决定继续睡 2h56m。这是"醒了又睡"的典型模式，但问题是 08:33 才醒，11:42 才真正起床——起床后的 3 小时里有 2h56m 又在睡觉，说明白天的"清醒-睡眠"边界模糊了</div>
        <div class="h-time">08:46~11:42 上午回笼觉 2h56m</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4A4;</span>
      <div>
        <div class="h-text">午睡 2h56m（13:49~16:45）：吃完午饭后 1 分钟就进入午睡，持续近 3 小时。这是"过度午睡"——超过 90min 会进入深度睡眠，醒来后比不睡还累。建议午睡控制在 20~30min</div>
        <div class="h-time">⚠️ 13:49~16:45 午睡 2h56m（超过 90min）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4CA;</span>
      <div>
        <div class="h-text">总睡眠 {sleep_h}h{sleep_m}m（4 段），占全天 53.6%。远超 7-9h 推荐范围上限（9h），是补觉日 + 周末惰性的双重作用。睡眠过多（&gt;11h）会增加：① 心血管疾病风险 ② 抑郁风险 ③ 白天嗜睡 ④ 越睡越累的恶性循环。明天（周一）建议：① 早起 1h（如 06:00 而不是 07:00）② 控制总睡眠 7-8h ③ 取消回笼觉决定——醒了就起床</div>
        <div class="h-time">总 {sleep_h}h{sleep_m}m（4 段）⚠️ 过多</div>
      </div>
    </div>'''

# ============ 改善建议 ============
suggest_html = '''    <div class="highlight-row">
      <span class="h-emoji">&#x1F489;</span>
      <div>
        <div class="h-text">睡眠过多问题 ⚠️：今天 12h52m 睡眠（占 53.6%），是过去几天的最高值。这是"周末补觉"的过度反应——平时缺觉，周末报复性补觉，反而打乱节律。建议：① 周一到周五保持 7-8h 稳定睡眠（参考 2026-06-19 周五 9h1m 已偏多）② 周六周日不要超过 9h ③ 起床后不再回笼——醒了就起，看手机不躺床上 ④ 午睡控制在 20-30min（小睡不过 90min）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4A4;</span>
      <div>
        <div class="h-text">午睡过久问题 ⚠️：13:49~16:45 午睡 2h56m，深度睡眠 2h+。醒来后应该非常累。午睡过久的原因：① 吃完饭太困 ② 手机/床太近 ③ 缺乏时间约束。建议：① 午饭后站立 10min（洗碗/收拾）② 午睡设置闹钟 25min ③ 午睡不躺床上（坐着打盹）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4F1;</span>
      <div>
        <div class="h-text">上午看手机 1h33m：07:00~08:33 醒来后第一件事就是看手机 1h33m。手机是回笼觉的导火索——看了 90min 后决定"再睡会儿"。建议：① 起床后第一件事喝水/洗漱 ② 手机放到客厅充电 ③ 如果必须看手机，限定 15min 内</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F37D;&#xFE0F;</span>
      <div>
        <div class="h-text">餐饮时间优化：今天餐饮 3h31m（占 14.7%），其中"做饭 49min+吃 54min"午饭 1h43m，"焖饭 78min"晚饭 1h18m。餐饮时间偏长的原因：① 一个人做饭无帮手 ② 焖饭需要等待 ③ 边吃边看手机。建议：① 周日用简单的饭菜（如面条+炒菜 30min 完成）② 焖饭时同步做菜 ③ 餐饮总时间控制在 2h 以内</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4DA;</span>
      <div>
        <div class="h-text">卡路里技能优化已推进：晚上 3h6m 集中研究卡路里技能缺陷（5个问题），这表明：① 你正在用「技能工坊」优化技能——这是高阶用法 ② 卡路里技能确实有改进空间（之前 2026-06-20 用了 6h5m 查卡路里）③ 优化完成后，卡路里查询时间应该会大幅下降。建议：① 继续完善 5 个问题的修复方案 ② 优化后实测 1~2 天看效果</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3E0;</span>
      <div>
        <div class="h-text">周日零工作是好习惯：今天工作 0min（仅 1min 模型配置不算）。这与昨天 2026-06-20（周六）的 54min 工作形成对比。建议：① 把周日固定为「完全无工作日」② 周末每天工作不超过 30min（紧急事务）③ 周末优先休息/家庭/兴趣</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3C3;</span>
      <div>
        <div class="h-text">运动量继续为 0：今天依然没有任何运动。周日是休息日，但即使是休息日也可以：① 散步 30min（户外）② 拉伸 10min ③ 站立做事。建议：每天至少散步 20-30min，明天周一开始加入</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4F1;</span>
      <div>
        <div class="h-text">晚间多任务问题：23:21~23:59 边看视频（安东尼2001）边讨论技能修改。38min 内既要看视频又要写技术问题，注意力切换频繁。建议：① 22:00 后只做一件事 ② 要么纯看视频（放松），要么纯写代码（专注）③ 睡前 30min 减少屏幕</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x2705;</span>
      <div>
        <div class="h-text">周日做得好的地方：① 完全无工作（休息日）② 集中时间研究卡路里技能（3h6m）③ 卡路里查询大幅减少（从 6h5m 到 1h）④ 父亲节红包表达关怀 ⑤ 晚上技能修改讨论 ⑥ 简单晚饭（焖饭）⑦ 23:21 前已躺床（不算熬夜）⑧ 8 个分类覆盖完整生活</div>
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

REPORT_PATH = Path('/mnt/d/2Study/StudyNotes/SKILLS/作息管家/reports/2026-06-21.html')
REPORT_PATH.write_text(html, encoding='utf-8')
print(f"✓ HTML 报告已生成: {REPORT_PATH}")
print(f"  文件大小: {REPORT_PATH.stat().st_size} bytes")
