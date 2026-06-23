#!/usr/bin/env python3
"""
渲染 2026-06-22 作息报告 HTML
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

with open('/tmp/report_data_2026-06-22.json', 'r', encoding='utf-8') as f:
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
sleep_pct = sleep_total / total_minutes * 100

# 餐饮总时长
meal_total = cat_minutes.get('餐饮', 0)
meal_h = meal_total // 60
meal_m = meal_total % 60

# 工作总时长
work_total = cat_minutes.get('工作', 0)
work_h = work_total // 60
work_m = work_total % 60

# 娱乐总时长
entertainment_total = cat_minutes.get('娱乐', 0)
entertainment_h = entertainment_total // 60
entertainment_m = entertainment_total % 60

# 通勤总时长
commute_total = cat_minutes.get('通勤', 0)

# 休闲总时长
leisure_total = cat_minutes.get('休闲', 0)
leisure_h = leisure_total // 60
leisure_m = leisure_total % 60

highlights_html = f'''    <div class="highlight-row">
      <span class="h-emoji">😴</span>
      <div>
        <div class="h-text">睡眠正常 9h15m（占 38.6%）：5 段睡眠总计 {sleep_h}h{sleep_m}m，符合 7-9h 推荐范围。① 00:30~03:49 前夜延续 3h19m（用户 03:49 报告"凌晨十二点半睡的"）② 03:49~04:14 凌晨醒来 25min（短醒后很快回睡）③ 04:15~07:35 回笼觉 3h20m（用户 04:14 主动说"继续睡觉 不需要闹钟"，08:24 报告"7.35醒了"）④ 14:08~15:20 午睡 1h12m（略长但可接受）⑤ 23:00~23:59 入睡 59min（按规则补齐）。夜间总睡眠约 6h40m + 午睡 1h12m = 7h52m 真实睡眠。睡眠结构合理，无过度</div>
        <div class="h-time">5 段睡眠：00:30~03:49 / 03:49~04:14 / 04:15~07:35 / 14:08~15:20 / 23:00~23:59</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">💼</span>
      <div>
        <div class="h-text">工作 4h3m（占 16.9%）：14 段工作 {work_h}h{work_m}m，这是高强度技术工作日。上午 08:24~08:50 清理饼干记账测试数据（26min），下午 13:08~17:36 集中处理 feathersdata 仓库事故（4h多），含分支问题排查 / 历史 commit 恢复 / 安全删除 master / .db 异常修复 / 47 条污染 commit 清理 / GitHub 推送修复等。晚上 18:14~19:03 边看电影边讨论 gc 失败原因（49min）。这是典型的"事故恢复日"——多线程问题并行处理</div>
        <div class="h-time">14 段工作：00:00~00:30 / 04:14~04:15 / 08:24~08:50 / 13:08~13:56 / 14:00~14:04 / 16:41~18:06 / 18:14~19:03</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🍽️</span>
      <div>
        <div class="h-text">餐饮时间偏长 4h30m（占 18.8%）：8 段餐饮 {meal_h}h{meal_m}m，远超正常 1.5~2h。① 08:58~10:46 吃早餐 280g 焖饭（48min）② 11:51~13:08 吃午饭 焖饭+卡路里（77min，3段）③ 21:05~22:30 晚餐+喝水+查看每日检查（85min，3段）。三餐全是焖饭，单调且吃饭时间长。焖饭习惯是 2026-06-20 开始的，问题是焖饭耗时 + 边吃边看手机/操作</div>
        <div class="h-time">8 段餐饮：08:58~10:46 / 11:51~12:21 / 12:21~12:21 / 12:21~13:08 / 21:05~21:25 / 21:25~22:08 / 22:08~22:30</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎮</span>
      <div>
        <div class="h-text">看电影 {entertainment_h}h{entertainment_m}m：19:03~20:38 共 95min，女朋友请客看新电影《抓特务》。这是周一晚上难得的放松时间，且是社交（女朋友陪伴）+ 娱乐（看电影）的结合。19:03~20:38 完整无中断，是高质量的 1.5h 专注放松</div>
        <div class="h-time">19:03~20:38 看电影《抓特务》</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🚴</span>
      <div>
        <div class="h-text">通勤+餐饮混合 27min：20:38~21:05 回家开始煮包子 + 卡路里记录（焖饭+水蜜桃）。这是电影结束后的回家过程，27min 内做了三件事：① 回家 ② 煮包子 ③ 卡路里记录。说明用户已经把"做饭+卡路里"整合到通勤后流程中，效率不错</div>
        <div class="h-time">20:38~21:05 回家+煮包子+卡路里</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">📚</span>
      <div>
        <div class="h-text">学习 45min：10:46~11:31 学习/思考"解除劳动合同协议和离职证明"——这是一个有现实意义的学习主题（用户在考虑离职相关事项），属于"人生规划"类学习。45min 集中思考后，11:31~11:51 是 20min 刷手机+准备午饭的过渡，符合"学习后放松"节奏</div>
        <div class="h-time">10:46~11:31 解除劳动合同+离职证明</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🛋️</span>
      <div>
        <div class="h-text">休闲 2h37m（占 10.9%）：8 段。① 07:35~08:24 醒后床上 49min（用户 7.35 醒但 8.24 才报）② 11:31~11:51 刷手机+准备午饭 20min ③ 13:56~13:59 烦躁情绪发泄 3min ④ 14:04~14:08 记账查询 4min ⑤ 15:20~16:01 起床+小憩+撒娇 41min ⑥ 16:31~16:41 询问健身活动 10min ⑦ 22:30~23:00 准备睡觉+躺床 30min。休闲结构合理，有"醒后过渡""睡后恢复""睡前准备"等多种用途</div>
        <div class="h-time">8 段休闲：07:35~08:24 / 11:31~11:51 / 13:56~13:59 / 14:04~14:08 / 15:20~15:41 / 15:41~16:01 / 16:31~16:41 / 22:30~23:00</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">💕</span>
      <div>
        <div class="h-text">社交 17min：3 段。① 08:50~08:58 送走女朋友 8min ② 13:59~14:00 模型切换讨论 1min ③ 18:06~18:14 外出+女朋友请看新电影 8min。社交时间虽短但有质量：早上送女朋友+晚上请看电影，是伴侣关系的健康互动</div>
        <div class="h-time">3 段社交：08:50~08:58 / 13:59~14:00 / 18:06~18:14</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">🎨</span>
      <div>
        <div class="h-text">兴趣爱好 19min：16:01~16:20 元母意程修炼+备忘录打卡。这是用户持续打卡的修炼项目，配合洗漱（16:20~16:31 11min）形成"修炼+洗漱"的固定流程。19min 完整无中断，是专注的修炼时间</div>
        <div class="h-time">16:01~16:20 元母意程+备忘录打卡</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">⚠️</span>
      <div>
        <div class="h-text">运动/健康 0min：今天 0 段运动或健康相关活动。每日检查报告也标记"今日运动 · 0 项（最近 6-15）⚠️ 这是弱项"。运动连续 6-15 天为 0 是大红旗——身体是革命的本钱，1 万小时的编程/技术技能也需要健康支撑。建议明天（周二）加入至少 20min 散步</div>
        <div class="h-time">⚠️ 0 段运动，连续 6-15 天未运动</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">📌</span>
      <div>
        <div class="h-text">无独立"卡路里"或"记账"分类：今天的卡路里操作都归入"餐饮"分类（如 11:51~12:21 吃午饭+卡路里记录，21:05~21:25 焖饭 130g+喝水 2000ml），记账操作归入"休闲"（14:04~14:08）。这与前几天（2026-06-20 有 6h5m 卡路里）相比，卡路里查询大幅减少——是因为昨天（2026-06-21）3h6m 集中优化了卡路里技能，让今日查询更快更准</div>
        <div class="h-time">卡路里操作合并到餐饮 / 记账合并到休闲</div>
      </div>
    </div>'''

# ============ 睡眠分析 ============
sleep_html = f'''    <div class="highlight-row">
      <span class="h-emoji">&#x1F319;</span>
      <div>
        <div class="h-text">凌晨主睡眠 00:30~07:35 共 7h05m：从 00:30 持续到 07:35，中间 03:49~04:14 短暂醒来 25min（回笼准备）。实际睡眠 6h40m。整段是"前夜入睡 → 凌晨短暂醒 → 续睡"的模式，3 个睡眠段（00:30~03:49 / 03:49~04:14 / 04:15~07:35）</div>
        <div class="h-time">00:30~07:35 持续 7h05m（中间 25min 短醒）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F634;</span>
      <div>
        <div class="h-text">午睡 1h12m（14:08~15:20）：在完成上午清理测试数据 + 解除劳动合同思考 + 午饭 + 工作讨论后，14:08 午睡。1h12m 比理想的 20-30min 长（超 90min 会进入深度睡眠），但比昨天的 2h56m 短很多，是改善</div>
        <div class="h-time">14:08~15:20 午睡 1h12m</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4CA;</span>
      <div>
        <div class="h-text">总睡眠 {sleep_h}h{sleep_m}m（5 段），占全天 38.6%。在 7-9h 推荐范围之内（略偏高但合理）。真实睡眠时间：前夜 6h40m + 午睡 1h12m + 入睡 59min = 8h51m（接近 9h）。睡眠结构合理：前夜长睡 + 短午睡 + 短醒，是健康的睡眠模式</div>
        <div class="h-time">总 {sleep_h}h{sleep_m}m（5 段）✓ 正常</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F552;</span>
      <div>
        <div class="h-text">凌晨 03:49 短醒：用户 03:49 醒来主动报告"凌晨十二点半睡的"（说明 00:30 入睡），然后 04:14 主动说"继续睡觉 不需要闹钟"，4h15 续睡到 07:35。这是健康的"短醒后回睡"模式——主动入睡而不是辗转难眠。建议：① 继续保持"凌晨短醒后自然回睡"的能力 ② 23:00 前入睡可以避免凌晨短醒</div>
        <div class="h-time">03:49 短醒 25min → 04:15 续睡 3h20m</div>
      </div>
    </div>'''

# ============ 改善建议 ============
suggest_html = f'''    <div class="highlight-row">
      <span class="h-emoji">&#x1F3C3;</span>
      <div>
        <div class="h-text">运动 0 问题 ⚠️：今天 0min 运动，连续 6-15 天未运动（每日检查报告标注）。运动缺失会累积健康风险：① 颈椎/腰椎问题（程序员高发）② 免疫力下降 ③ 精神状态变差 ④ 长期可能影响心血管。建议：① 明天（周二）开始加入 20min 散步 ② 上午/下午各 10min 站起来活动 ③ 周末户外活动 1h+。从"轻量"开始，关键是"每天都做"</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F37D;&#xFE0F;</span>
      <div>
        <div class="h-text">餐饮时间过长 ⚠️：今天 4h30m 餐饮（占 18.8%），是严重偏高的指标。问题点：① 三餐全是焖饭（280g+130g），单调且耗时 ② 吃饭时操作手机/卡路里记录 ③ 焖饭需要等待。建议：① 早餐用快速餐（牛奶+面包 15min）② 午餐外卖或简单炒菜（30min）③ 焖饭改为电压力锅（25min 出锅）④ 吃饭时不操作手机 ⑤ 餐饮总时间控制在 1.5~2h</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4A4;</span>
      <div>
        <div class="h-text">午睡 1h12m 略长：14:08~15:20 午睡 72min。比昨天 2h56m 好很多，但超过推荐的 20-30min。建议：① 午饭后洗碗 10min 再睡 ② 闹钟 25min ③ 午睡不躺床上（坐着打盹）④ 超过 90min 会进入深度睡眠，醒来后比不睡还累</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F62E;</span>
      <div>
        <div class="h-text">凌晨短醒问题：03:49~04:14 短醒 25min。虽然能快速回睡是好事，但凌晨 3-4 点是深睡期，短醒会影响睡眠质量。建议：① 23:00 前入睡（今天 23:00 才入睡，可能略晚）② 晚餐不要过饱（晚餐 21:05~22:30 太晚）③ 凌晨 3 点避免喝太多水（21:25~22:30 喝 2000ml 水会增加起夜）④ 卧室温度 18-22°C 最佳</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4F1;</span>
      <div>
        <div class="h-text">边工作边娱乐问题：18:14~19:03（49min）边看电影边讨论 gc 失败原因。表面是"高效利用时间"，实际是"注意力频繁切换"——电影情节 + 技术问题同时处理，效率和质量都会打折扣。建议：① 19:00~20:30 完整看电影 ② 19:00 前完成技术讨论 ③ 不要把工作"塞进"娱乐时间</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4DA;</span>
      <div>
        <div class="h-text">学习主题转变：10:46~11:31 学习"解除劳动合同协议和离职证明"。这与之前学习主题（卡路里技能缺陷 5 个问题）不同，是"人生/法律"类内容。可能用户在考虑职业转型或离职相关事项。建议：① 如果真在考虑离职，可进一步了解劳动法、社保、个税等 ② 与"现在工作"做对比分析 ③ 列出"离职利弊清单" ④ 这个主题值得深入学习</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F389;</span>
      <div>
        <div class="h-text">事故处理能力强：下午 13:08~17:36（4h28m）连续处理 feathersdata 仓库事故——分支问题排查 / 历史 commit 恢复 / 安全删除 master / .db 异常 / 47 条污染 commit 清理 / GitHub 推送修复 / gc 问题。这是"开发者能力"的综合体现。建议：① 总结本次事故处理经验（避免下次重复）② 完善 .gitignore ③ 建立"事故处理 SOP" ④ 提前备份（不要等到出事）</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F3E0;</span>
      <div>
        <div class="h-text">情侣关系良好：早上 08:50~08:58 送走女朋友 + 晚上 18:06~18:14 女朋友请看新电影《抓特务》+ 19:03~20:38 一起看电影 95min。这是健康的伴侣互动模式——"出门道别 + 一起看电影 + 一起回家"。建议：① 保持每周至少 1 次"约会"（电影/吃饭/散步）② 周末可加 1 次户外活动</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4F1;</span>
      <div>
        <div class="h-text">晚上喝水过多：21:25~22:30 共 65min 喝水 2000ml+，且 23:00 才入睡。这会增加起夜次数，影响凌晨睡眠质量。建议：① 21:00 后减少喝水（≤500ml）② 白天补水为主 ③ 2000ml/天的水应分散在 7:00~21:00 之间</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x1F4A1;</span>
      <div>
        <div class="h-text">洗漱顺序合理：16:01~16:20 元母意程修炼+备忘录打卡 → 16:20~16:31 洗澡+吹头发 → 16:31~16:41 询问健身活动。这是"修炼→清洁→计划下一步"的健康流程。建议：① 保持这个顺序 ② 健身活动可以真正执行（结合运动 0 的问题）③ 周末可加入"户外散步 30min"</div>
      </div>
    </div>
    <div class="highlight-row">
      <span class="h-emoji">&#x2705;</span>
      <div>
        <div class="h-text">周一做得好的地方：① 睡眠结构合理（5 段，符合推荐）② 高强度工作但有午休调整 ③ 事故处理 4h+ 体现开发者能力 ④ 完整看完 1.5h 电影（放松质量高）⑤ 女朋友陪伴良好 ⑥ 21:00 前回家，未过度熬夜 ⑦ 23:00 入睡（不算太晚）⑧ 10 个分类覆盖完整生活 ⑨ 卡路里技能优化后续效果显现（今日卡路里操作合并到餐饮，节省时间）</div>
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

REPORT_PATH = Path('/mnt/d/2Study/StudyNotes/SKILLS/作息管家/reports/2026-06-22.html')
REPORT_PATH.write_text(html, encoding='utf-8')
print(f"✓ HTML 报告已生成: {REPORT_PATH}")
print(f"  文件大小: {REPORT_PATH.stat().st_size} bytes")
