import sqlite3, datetime
from daily_checker import init_db, upsert_issue

init_db()

def run_calorie_lint():
    conn = sqlite3.connect('/mnt/d/2Study/StudyNotes/.db/calorie_data.db')
    c = conn.cursor()
    today = datetime.date.today().isoformat()

    print('===== 卡路里 Lint =====')

    # 1. 数据新鲜度
    c.execute('SELECT date, weight_kg FROM weight_log ORDER BY date DESC LIMIT 1')
    w = c.fetchone()
    print(f'最新体重: {w[0]} {w[1]}kg' if w else '无体重记录')

    c.execute('SELECT COUNT(*) FROM entries WHERE date = ?', (today,))
    print(f'今日饮食: {c.fetchone()[0]}条')

    c.execute('SELECT COUNT(*) FROM exercise_log WHERE date = ?', (today,))
    print(f'今日运动: {c.fetchone()[0]}条')

    # 2. 运动连续性
    c.execute('SELECT date FROM exercise_log ORDER BY date DESC LIMIT 1')
    le = c.fetchone()
    if le:
        days_since = (datetime.date.today() - datetime.date.fromisoformat(le[0])).days
        if days_since >= 3:
            upsert_issue('卡路里', 'exercise_overdue', f'连续{days_since}天未运动（最后运动：{le[0]}）')
            print(f'⚠️ 连续{days_since}天未运动（最后：{le[0]}）')
        else:
            print(f'✅ 末次运动: {le[0]}，间隔{days_since}天')
    else:
        upsert_issue('卡路里', 'exercise_overdue', '无运动记录')
        print('⚠️ 无运动记录')

    # 3. 热量趋势（连续超标3天）
    c.execute('''
        SELECT date, SUM(calories) as total
        FROM entries
        WHERE date >= date('now', '-7 days')
        GROUP BY date ORDER BY date
    ''')
    cal_rows = c.fetchall()
    c.execute('SELECT calorie_goal FROM daily_goal LIMIT 1')
    goal_row = c.fetchone()
    goal_cal = goal_row[0] if goal_row else 1800

    if len(cal_rows) >= 3:
        over_days = [r for r in cal_rows[-3:] if r[1] > goal_cal]
        if len(over_days) == 3:
            dstr = ' / '.join([f'{r[0]}:{int(r[1])}卡' for r in over_days])
            upsert_issue('卡路里', 'calorie_3day_overrun', f'连续3天超标（目标{goal_cal}卡）：{dstr}')
            print(f'⚠️ 连续3天超标: {dstr}')
        else:
            print(f'✅ 热量超标: {len(over_days)}/3天')

    # 4. 热量缺口（近7天净摄入）
    c.execute('SELECT COALESCE(SUM(calories), 0) FROM entries WHERE date >= date("now", "-7 days")')
    total_cal = c.fetchone()[0]
    c.execute('SELECT COALESCE(SUM(calories_burned), 0) FROM exercise_log WHERE date >= date("now", "-7 days")')
    total_ex = c.fetchone()[0]
    net = total_cal - total_ex
    print(f'近7天: 摄入{int(total_cal)}卡，运动{int(total_ex)}卡，净{int(net)}卡')
    if net > 5000:
        upsert_issue('卡路里', 'calorie_7day_net_positive', f'近7天净摄入{int(net)}卡（摄入{int(total_cal)}，运动{int(total_ex)}）')
        print(f'⚠️ 热量缺口异常: 净摄入{int(net)}卡')

    # 5. 体重目标
    c.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1')
    current_w = c.fetchone()
    if current_w:
        c.execute('SELECT weight_goal FROM daily_goal LIMIT 1')
        target = c.fetchone()
        if target and target[0]:
            diff = round(current_w[0] - target[0], 1)
            print(f'体重目标: 当前{current_w[0]}kg → 目标{target[0]}kg，差距{diff}kg')
            if diff > 10:
                upsert_issue('卡路里', 'weight_target_far', f'距目标{diff}kg（当前{current_w[0]}kg，目标{target[0]}kg）')

    conn.close()
    print('===== 卡路里完成 =====\n')


def run_home_lint():
    conn = sqlite3.connect('/mnt/d/2Study/StudyNotes/.db/home.db')
    c = conn.cursor()

    print('===== 居家管家 Lint =====')

    # 1. 标签完整性（少于2个标签的物品）
    c.execute('''
        SELECT i.id, i.name, COUNT(it.tag) as tag_count
        FROM items i
        LEFT JOIN item_tags it ON i.id = it.item_id
        GROUP BY i.id
        HAVING tag_count < 2
        LIMIT 20
    ''')
    few_tags = c.fetchall()
    if few_tags:
        print(f'⚠️ 标签过少(<2)的物品: {len(few_tags)}个')
        for item in few_tags[:5]:
            print(f'  - {item[1]}（{item[2]}个标签）')
        upsert_issue('居家管家', 'few_tags', f'{len(few_tags)}个物品标签少于2个')

    # 2. 无标签物品
    c.execute('''
        SELECT i.id, i.name FROM items i
        LEFT JOIN item_tags it ON i.id = it.item_id
        WHERE it.tag IS NULL
        LIMIT 20
    ''')
    no_tags = c.fetchall()
    if no_tags:
        print(f'⚠️ 无标签物品: {len(no_tags)}个')
        for item in no_tags[:5]:
            print(f'  - {item[1]}')
        upsert_issue('居家管家', 'no_tags', f'{len(no_tags)}个物品无标签')

    # 3. 状态时效性（location_status 异常超过14天）
    c.execute('''
        SELECT i.name, il.location_status, il.updated_at
        FROM items i
        JOIN item_locations il ON i.id = il.item_id
        WHERE il.location_status IN ('快递中', '旅游中', '洗护中', '维修中')
        AND date(il.updated_at) < date('now', '-14 days')
        LIMIT 20
    ''')
    stale = c.fetchall()
    if stale:
        print(f'⚠️ 状态异常物品（超14天未更新）: {len(stale)}个')
        for item in stale[:5]:
            print(f'  - {item[0]} | {item[1]} | {item[2]}')
        upsert_issue('居家管家', 'stale_status', f'{len(stale)}个物品状态超14天未更新')

    # 4. 位置规范性（单级位置）
    c.execute('''
        SELECT location, COUNT(*) as cnt
        FROM item_locations
        WHERE location NOT LIKE '%/%'
        GROUP BY location
        LIMIT 20
    ''')
    single_level = c.fetchall()
    if single_level:
        print(f'⚠️ 单级位置: {len(single_level)}个')
        for loc in single_level[:5]:
            print(f'  - {loc[0]}（{loc[1]}条记录）')
        upsert_issue('居家管家', 'single_level_location', f'{len(single_level)}个位置为单级路径')

    # 5. 总览
    c.execute('SELECT COUNT(*) FROM items')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM item_tags')
    tag_total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM item_locations')
    loc_total = c.fetchone()[0]
    print(f'物品: {total}，标签记录: {tag_total}，位置记录: {loc_total}')

    conn.close()
    print('===== 居家管家完成 =====\n')


def run_llm_wiki_lint():
    import os, re
    from collections import defaultdict

    print('===== llm-wiki Lint =====')

    possible_wikis = [
        '/mnt/d/2Study/StudyNotes/2026/learning-system/wiki',
        '/mnt/d/2Study/StudyNotes/成真/wiki',
    ]

    wiki = None
    for w in possible_wikis:
        if os.path.exists(w):
            wiki = w
            break

    if not wiki:
        print('⚠️ 未找到 wiki 目录')
        return

    print(f'Wiki路径: {wiki}')

    # ① 孤立页面（无 inbound 链接）
    all_pages = []
    wikilink_map = defaultdict(list)  # target page -> list of pages linking to it

    subdirs = ['entities', 'concepts', 'comparisons', 'queries', '']

    for sub in subdirs:
        dir_path = os.path.join(wiki, sub) if sub else wiki
        if not os.path.exists(dir_path):
            continue
        for fname in os.listdir(dir_path):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(dir_path, fname)
            page_key = os.path.relpath(fpath, wiki).replace('\\', '/')
            all_pages.append(page_key)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                links = re.findall(r'\[\[([^\]]+)\]\]', content)
                for link in links:
                    link_clean = link.strip()
                    # 去掉 .md 后缀
                    if link_clean.endswith('.md'):
                        link_clean = link_clean[:-3]
                    # 转为相对路径格式
                    link_clean = link_clean.replace('\\', '/')
                    wikilink_map[link_clean].append(page_key)
            except:
                pass

    orphans = [p for p in all_pages if p not in wikilink_map or len(wikilink_map[p]) == 0]
    if orphans:
        print(f'⚠️ 孤立页面: {len(orphans)}个')
        sample = orphans[:5]
        print(f'  例: {", ".join(sample)}...')
        upsert_issue('llm-wiki', 'orphan', f'共{len(orphans)}个孤立页面无inbound链接')
    else:
        print(f'✅ 无孤立页面')

    # ② 失效 wikilink
    broken_assets = []
    broken_pages = []

    for sub in subdirs:
        dir_path = os.path.join(wiki, sub) if sub else wiki
        if not os.path.exists(dir_path):
            continue
        for fname in os.listdir(dir_path):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(dir_path, fname)
            page_key = os.path.relpath(fpath, wiki).replace('\\', '/')
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                links = re.findall(r'\[\[([^\]]+)\]\]', content)
                for link in links:
                    link_clean = link.strip()
                    if link_clean.startswith('raw/'):
                        target_path = os.path.join(wiki, link_clean)
                        if not os.path.exists(target_path):
                            broken_assets.append(f'{page_key} -> {link_clean}')
                    elif link_clean.endswith('.md'):
                        link_clean = link_clean[:-3]
                        target = link_clean.replace('/', os.sep)
                        target_path = os.path.join(wiki, target + '.md')
                        if not os.path.exists(target_path):
                            broken_pages.append(f'{page_key} -> {link_clean}')
            except:
                pass

    if broken_assets:
        print(f'⚠️ 失效资源链接(raw/assets): {len(broken_assets)}个')
        upsert_issue('llm-wiki', 'broken_link_assets', f'{len(broken_assets)}个wikilink指向不存在的raw/assets文件')
    if broken_pages:
        print(f'⚠️ 失效页面链接: {len(broken_pages)}个')
        upsert_issue('llm-wiki', 'broken_link_other', f'{len(broken_pages)}个wikilink指向不存在的其他文件')
    if not broken_assets and not broken_pages:
        print(f'✅ 无失效链接')

    # ③ index.md 完整性
    index_path = os.path.join(wiki, 'index.md')
    if os.path.exists(index_path):
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_content = f.read()
            missing = []
            for page in all_pages:
                if page == 'index.md':
                    continue
                page_no_ext = page.replace('.md', '')
                if page not in index_content and page_no_ext not in index_content:
                    missing.append(page)
            if missing:
                print(f'⚠️ index.md缺失条目: {len(missing)}个')
                upsert_issue('llm-wiki', 'index_missing', f'{len(missing)}个页面未列入index.md')
        except:
            pass

    print('===== llm-wiki完成 =====\n')


if __name__ == '__main__':
    run_calorie_lint()
    run_home_lint()
    run_llm_wiki_lint()
    print('✅ 全部检查完成')