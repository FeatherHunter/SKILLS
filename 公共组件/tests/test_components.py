# -*- coding: utf-8 -*-
"""Base 控件函数测试 v1.2

覆盖（Playwright 浏览器环境, 无 DB 接触）:
- snapshot 结构校验: 缺 title / summary 非数组 / sections 缺 heading → 报错（违规直接报错）
- buildDataText: text/json/csv 三种 format; 脱敏行; 头部/摘要/分节输出
- buildLogText: 6 段结构; 缺省字段兜底
- toast 增强: 徽章/操作/计数/队列/向后兼容
- 新控件: formPrompt（预览+空值拦截）/ selectList（计数联动）/ confirm / foldBox / statusBadge / emptyState / errorReceipt
"""
import json
import pathlib
import sys

import pytest

BASE_DIR = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

BASE_JS = (BASE_DIR / 'assets' / 'base.js').read_text(encoding='utf-8')
CHARTS_JS = (BASE_DIR / 'assets' / 'charts.js').read_text(encoding='utf-8')


def _has_playwright():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(not _has_playwright(), reason='需要 playwright')

from playwright.sync_api import sync_playwright  # noqa: E402


VALID_PAYLOAD = {
    'status': 'ok',
    'data': {
        'meta': {
            'command_cn': '记作息回执',
            'occurred_at': '2026-08-11 17:30',
            'skill_name': '作息管家',
            'wake_word': '记作息',
            'skill_version': 'v1.2',
        },
        'scene': {
            'scene_id': 'record-result',
            'snapshot': {
                'title': '记作息回执',
                'summary': ['今日已记录 5 条 · 累计 8h30m', '本条：工作 09:30-12:00 (2h30m)'],
                'sections': [
                    {'heading': '本条记录', 'rows': ['id=1024 · 2026-08-11', '工作 09:30-12:00']},
                    {'heading': '今日统计', 'rows': ['分类排名：工作 #1/4', '本周累计 12 条']},
                ],
            },
            'copy_log': {
                'thinking': '意图理解: 用户报作息 → add CLI 写库',
                'data_structure': 'schedule_records 表 · INSERT 1 行',
                'call_chain': 'schedule_cli.py add → render-record-result',
                'timestamp': '2026-08-11 17:30:00',
                'exception': '无',
            },
            'copy_log': {
                'thinking': '意图理解: 用户报作息 → add CLI 写库',
                'data_structure': 'schedule_records 表 · INSERT 1 行',
                'call_chain': 'schedule_cli.py add → render-record-result',
                'timestamp': '2026-08-11 17:30:00',
                'exception': '无',
            },
        },
    },
}


@pytest.fixture(scope='module')
def page():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(f'<html><body><div id="root"></div><script>{BASE_JS}</script></body></html>')
        yield pg
        b.close()


# ── snapshot 结构校验（违规直接报错）──────────────────────

@pytest.mark.parametrize('mutate,err_frag', [
    (lambda s: s.pop('title'), 'title'),
    (lambda s: s.update({'title': '  '}), 'title'),
    (lambda s: s.update({'summary': 'not-array'}), 'summary'),
    (lambda s: s.update({'sections': 'not-array'}), 'sections'),
    (lambda s: s['sections'].append({'heading': 'x'}), 'rows'),
    (lambda s: s['sections'].append({'rows': []}), 'heading'),
])
def test_snapshot_validation_blocked(page, mutate, err_frag):
    p = json.loads(json.dumps(VALID_PAYLOAD))
    mutate(p['data']['scene']['snapshot'])
    err = page.evaluate(
        '(p) => { try { window.buildDataText(p); return ""; } catch(e) { return e.message; } }',
        p)
    assert err and 'snapshot' in err and err_frag in err


# ── buildDataText format ──────────────────────────────────

def test_build_data_text_default(page):
    out = page.evaluate('(p) => window.buildDataText(p)', VALID_PAYLOAD)
    assert '【作息管家 · 记作息回执】' in out
    assert '今日已记录 5 条' in out
    assert '▍本条记录' in out and 'id=1024' in out
    assert '▍今日统计' in out


def test_build_data_text_json(page):
    out = page.evaluate('(p) => window.buildDataText(p, "json")', VALID_PAYLOAD)
    d = json.loads(out)
    assert d['title'] == '记作息回执'
    assert len(d['sections']) == 2


def test_build_data_text_csv(page):
    out = page.evaluate('(p) => window.buildDataText(p, "csv")', VALID_PAYLOAD)
    assert '记作息回执' in out
    assert '[本条记录]' in out and 'id=1024 · 2026-08-11' in out


def test_build_data_text_sensitive(page):
    p = json.loads(json.dumps(VALID_PAYLOAD))
    p['data']['scene']['snapshot']['sections'].append(
        {'heading': '凭证', 'rows': [{'text': 'api_key_123', 'sensitive': True}]})
    out = page.evaluate('(p) => window.buildDataText(p)', p)
    assert '****' in out and 'api_key_123' not in out


# ── buildLogText 6 段 ─────────────────────────────────────

def test_build_log_text_sections(page):
    out = page.evaluate('(p) => window.buildLogText(p)', VALID_PAYLOAD)
    for frag in ['① 场景标识', '② AI 思考链', '③ 底层数据结构', '④ 调用链', '⑤ 时间戳 + 版本', '⑥ 异常信息']:
        assert frag in out
    assert 'schedule_records 表' in out


def test_build_log_text_missing_defaults(page):
    p = {'status': 'ok', 'data': {'meta': {'command_cn': 'x', 'occurred_at': 't'}, 'scene': {}}}
    out = page.evaluate('(p) => window.buildLogText(p)', p)
    assert '(未知)' in out or '(本地渲染 · 无 AI 链)' in out


# ── toast 增强 ────────────────────────────────────────────

def _clear_toasts(page):
    page.evaluate("window.__hmToastFlush && window.__hmToastFlush()")
    page.wait_for_timeout(50)


def test_toast_backward_compat(page):
    _clear_toasts(page)
    page.evaluate("window.toast('已复制','粘贴给 AI')")
    page.wait_for_timeout(100)
    title = page.evaluate("document.querySelector('.hm-toast .hm-toast-title')?.textContent")
    detail = page.evaluate("document.querySelector('.hm-toast .hm-toast-detail')?.textContent")
    close = page.evaluate("document.querySelector('.hm-toast-close')?.textContent")
    assert title == '已复制' and detail == '粘贴给 AI' and close == '✓ 知道了'


def test_toast_badge(page):
    _clear_toasts(page)
    page.evaluate("window.toast('已复制','粘贴给 AI',{badge:{text:'成功',type:'ok'}})")
    page.wait_for_timeout(100)
    chip = page.evaluate("document.querySelector('.hm-toast-chip')?.textContent")
    assert chip == '成功'


def test_toast_count(page):
    _clear_toasts(page)
    page.evaluate("window.toast('已记录','累计 8h30m',{count:'5 条'})")
    page.wait_for_timeout(100)
    count = page.evaluate("document.querySelector('.hm-toast-count')?.textContent")
    assert count == '5 条'


def test_toast_action(page):
    _clear_toasts(page)
    page.evaluate("window.__clicked = false; window.toast('已修改','详情',{actions:[{label:'撤销',onClick:function(){window.__clicked=true;}}]})")
    page.wait_for_timeout(100)
    page.click('.hm-toast-act')
    page.wait_for_timeout(100)
    assert page.evaluate('window.__clicked') is True


def test_toast_queue(page):
    _clear_toasts(page)
    page.evaluate("""
      window.toast('A','',{timeout:300});
      window.toast('B','',{timeout:300});
    """)
    page.wait_for_timeout(80)
    count = page.evaluate("document.querySelectorAll('.hm-toast').length")
    assert count == 1  # 队列: 同一时刻最多 1 个
    page.wait_for_timeout(700)
    title = page.evaluate("document.querySelector('.hm-toast .hm-toast-title')?.textContent")
    assert title == 'B'  # 队列: A 消失后 B 显示


def test_toast_aria(page):
    _clear_toasts(page)
    page.evaluate("window.toast('X','Y')")
    page.wait_for_timeout(100)
    role = page.evaluate("document.querySelector('.hm-toast')?.getAttribute('role')")
    aria = page.evaluate("document.querySelector('.hm-toast')?.getAttribute('aria-live')")
    assert role == 'status' and aria == 'polite'


# ── 新控件 ────────────────────────────────────────────────

def test_form_prompt_preview_and_blank_block(page):
    page.evaluate("""
      window.__fp = window.formPrompt(
        [{key:'name',label:'物品名',default:'牛奶'},{key:'loc',label:'新位置',required:true}],
        '请帮我改物品（唤醒词：改物品）：\\n物品名: {name}\\n新位置: {loc}'
      );
      document.getElementById('root').innerHTML = window.__fp;
    """)
    page.wait_for_timeout(100)
    preview = page.evaluate("document.querySelector('.fp-preview-body')?.textContent")
    assert '物品名: 牛奶' in preview
    # 空值拦截: 清空必填字段 → 按钮禁用
    page.evaluate("document.querySelector('.fp-input[data-key=\"loc\"]').value=''; document.querySelector('.fp-input[data-key=\"loc\"]').dispatchEvent(new Event('input'))")
    page.wait_for_timeout(50)
    disabled = page.evaluate("document.querySelector('.fp-actions button')?.disabled")
    assert disabled is True


def test_select_list_count(page):
    page.evaluate("""
      document.getElementById('root').innerHTML = window.selectList(
        [{id:1,title:'牛奶',group:'冷藏'},{id:2,title:'面包',group:'冷藏'},{id:3,title:'苹果',group:'常温'}],
        [{label:'全带走',kind:'ok',onClick:function(){window.__ids=arguments[0];}}]
      );
    """)
    page.wait_for_timeout(100)
    page.check('.sl-item input[data-id="1"]')
    page.check('.sl-item input[data-id="2"]')
    page.wait_for_timeout(50)
    count = page.evaluate("document.querySelector('.sl-count')?.textContent")
    assert '已选 2/3' in count
    group = page.evaluate("document.querySelector('.sl-group-count')?.textContent")
    assert '本组已选 2/2' in group


def test_confirm_dialog(page):
    page.evaluate("window.__ok=false; window.confirm({title:'确认删除',danger:true,onOk:function(){window.__ok=true;}})")
    page.wait_for_timeout(100)
    assert page.evaluate("document.querySelector('.hm-confirm-panel')") is not None
    page.click('.hm-confirm-actions [data-c="1"]')
    page.wait_for_timeout(50)
    assert page.evaluate('window.__ok') is True
    assert page.evaluate("document.querySelector('.hm-confirm-overlay')") is None


def test_fold_box(page):
    page.evaluate("document.getElementById('root').innerHTML = window.foldBox('查看详情','<p>内容</p>')")
    summary = page.evaluate("document.querySelector('.hm-fold summary')?.textContent")
    assert summary == '查看详情'
    assert page.evaluate("document.querySelector('.hm-fold-body')") is not None


def test_status_badge(page):
    page.evaluate("document.getElementById('root').innerHTML = window.statusBadge('ok','完成') + window.statusBadge('danger')")
    ok = page.evaluate("document.querySelectorAll('.hm-status')[0]?.textContent")
    ok_cls = page.evaluate("document.querySelectorAll('.hm-status')[0]?.className")
    danger = page.evaluate("document.querySelectorAll('.hm-status')[1]?.textContent")
    assert ok == '完成' and 'ok' in ok_cls and danger == '失败'


def test_empty_state(page):
    page.evaluate("document.getElementById('root').innerHTML = window.emptyState({icon:'📭',text:'今天没有记录',hint:'说「记作息」开始记录'})")
    assert page.evaluate("document.querySelector('.hm-empty-text')?.textContent") == '今天没有记录'
    assert page.evaluate("document.querySelector('.hm-empty-hint')?.textContent") == '说「记作息」开始记录'
    assert page.evaluate("document.querySelector('.hm-empty-icon')?.textContent") == '📭'


def test_error_receipt(page):
    page.evaluate("window.__hmPayload=" + json.dumps(VALID_PAYLOAD, ensure_ascii=False) + "; document.getElementById('root').innerHTML = window.errorReceipt({message:'写入失败',retryPrompt:'请重试'})")
    assert page.evaluate("document.querySelector('.hm-error-title')?.textContent") == '❌ 写入失败'
    assert page.evaluate("document.querySelectorAll('.hm-error .copy').length") >= 3  # 修正重试 + 复制数据 + 复制日志


# ── 图表组件（v1.3 · CHARTS-HELPERS）────────────────────────

@pytest.fixture(scope='module')
def chart_page(page):
    """复用 page fixture 的同一浏览器上下文（避免嵌套 sync_playwright）;
    set_content 加载 base.js + charts.js（注入顺序: SHARED JS → CSS → CHARTS → DATA）"""
    page.set_content(
        f'<html><body><div id="root"></div>'
        f'<script>{BASE_JS}</script><script>{CHARTS_JS}</script></body></html>')
    return page


def test_charts_four_interfaces_exist(chart_page):
    """四接口必须全部可用（v1.3 验收标准: 柱状/折线/环形/进度）"""
    names = chart_page.evaluate(
        '["bar","line","donut","progress"].filter(k => typeof window.charts[k] !== "function")')
    assert names == [], f'缺少接口: {names}'


def test_charts_progress_renders(chart_page):
    chart_page.evaluate("window.charts.progress(document.getElementById('root'), 65)")
    fill = chart_page.evaluate("document.querySelector('.hm-c-p-fill')?.style.width")
    num = chart_page.evaluate("document.querySelector('.hm-c-p-n')?.textContent")
    assert fill == '65%' and num == '65%'


def test_charts_progress_clamps(chart_page):
    """非数兜底 0, 超界收敛 0~100"""
    chart_page.evaluate("window.charts.progress(document.getElementById('root'), 999)")
    num = chart_page.evaluate("document.querySelector('.hm-c-p-n')?.textContent")
    assert num == '100%'
    chart_page.evaluate("window.charts.progress(document.getElementById('root'), 'abc')")
    num2 = chart_page.evaluate("document.querySelector('.hm-c-p-n')?.textContent")
    assert num2 == '0%'


def test_charts_progress_color_option(chart_page):
    chart_page.evaluate("window.charts.progress(document.getElementById('root'), 30, {color:'var(--ok,#34c759)'})")
    bg = chart_page.evaluate("document.querySelector('.hm-c-p-fill')?.style.background")
    assert '34c759' in bg


def test_charts_bar_renders(chart_page):
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'牛奶',value:3},{label:'面包',value:7},{label:'苹果',value:5}]);
    """)
    cols = chart_page.evaluate("document.querySelectorAll('.hm-c-col').length")
    labels = chart_page.evaluate("[...document.querySelectorAll('.hm-c-l')].map(n=>n.textContent).join(',')")
    assert cols == 3 and labels == '牛奶,面包,苹果'
    # 高度按值比例: 面包(7) 柱子最高
    h = chart_page.evaluate("[...document.querySelectorAll('.hm-c-b')].map(n=>parseFloat(n.style.height))")
    assert h[1] == max(h)


def test_charts_bar_empty_links_empty_state(chart_page):
    """数据空 → emptyState 联动（base.js 的 emptyState 存在时用之）"""
    chart_page.evaluate("window.charts.bar(document.getElementById('root'), [])")
    text = chart_page.evaluate("document.querySelector('.hm-empty-text')?.textContent")
    assert text == '暂无数据'


def test_charts_bar_non_array_safe(chart_page):
    chart_page.evaluate("window.charts.bar(document.getElementById('root'), null)")
    text = chart_page.evaluate("document.querySelector('.hm-empty-text')?.textContent")
    assert text == '暂无数据'


def test_charts_bar_onclick(chart_page):
    chart_page.evaluate("""
      window.__idx = -1;
      window.charts.bar(document.getElementById('root'),
        [{label:'A',value:1},{label:'B',value:2}],
        {onclick:function(i){window.__idx=i;}});
    """)
    chart_page.click('.hm-c-b[data-i="1"]')
    assert chart_page.evaluate('window.__idx') == 1


def test_charts_line_renders(chart_page):
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'),
        [{label:'周一',value:2},{label:'周二',value:5},{label:'周三',value:3}]);
    """)
    poly = chart_page.evaluate("document.querySelector('.hm-c-line-svg polyline')?.getAttribute('points')")
    dots = chart_page.evaluate("document.querySelectorAll('.hm-c-dot').length")
    xs = chart_page.evaluate("document.querySelector('.hm-c-x')?.textContent")
    assert poly and dots == 3 and '周一' in xs and '周三' in xs


def test_charts_line_empty_links_empty_state(chart_page):
    chart_page.evaluate("window.charts.line(document.getElementById('root'), [])")
    text = chart_page.evaluate("document.querySelector('.hm-empty-text')?.textContent")
    assert text == '暂无数据'


def test_charts_donut_renders(chart_page):
    chart_page.evaluate("""
      window.charts.donut(document.getElementById('root'),
        [{label:'食品',value:120},{label:'出行',value:80},{label:'日用',value:50}],
        {centerLabel:'总支出'});
    """)
    segs = chart_page.evaluate("document.querySelectorAll('.hm-c-donut svg circle').length")
    legend = chart_page.evaluate("document.querySelectorAll('.hm-c-dl').length")
    center = chart_page.evaluate("document.querySelector('.hm-c-donut svg text')?.textContent")
    # 1 底环 + 3 段 = 4 个 circle; 图例 3 行; 中心文案存在
    assert segs == 4 and legend == 3 and center == '总支出'


def test_charts_donut_percent_sum_100(chart_page):
    chart_page.evaluate("""
      window.charts.donut(document.getElementById('root'),
        [{label:'A',value:25},{label:'B',value:75}]);
    """)
    pcts = chart_page.evaluate("[...document.querySelectorAll('.hm-c-dl-p')].map(n=>parseInt(n.textContent))")
    assert sum(pcts) == 100


def test_charts_donut_empty_links_empty_state(chart_page):
    chart_page.evaluate("window.charts.donut(document.getElementById('root'), [])")
    text = chart_page.evaluate("document.querySelector('.hm-empty-text')?.textContent")
    assert text == '暂无数据'


def test_charts_donut_zero_total_links_empty_state(chart_page):
    chart_page.evaluate("window.charts.donut(document.getElementById('root'), [{label:'A',value:0}])")
    text = chart_page.evaluate("document.querySelector('.hm-empty-text')?.textContent")
    assert text == '暂无数据'


def test_charts_mobile_375_no_overflow(chart_page):
    """手机 375px: 柱状图不横向撑破视口（.hm-c-bar 内部滚动）"""
    chart_page.set_viewport_size({'width': 375, 'height': 700})
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'类别一',value:1},{label:'类别二',value:2},{label:'类别三',value:3},
         {label:'类别四',value:4},{label:'类别五',value:5},{label:'类别六',value:6}]);
    """)
    scroll_w = chart_page.evaluate("document.querySelector('.hm-c-bar')?.scrollWidth")
    client_w = chart_page.evaluate("document.querySelector('.hm-c-bar')?.clientWidth")
    assert scroll_w is not None and scroll_w >= client_w  # 可横向滚动, 不硬撑
    # 页面本身不出现水平溢出滚动条
    body_overflow = chart_page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    assert body_overflow is False


def test_charts_standalone_without_base_js(chart_page):
    """charts.js 可独立注入（不依赖 base.js）: 空态用内联兜底而非 emptyState
    （删除 base.js 残留全局 + 重新执行 charts.js → 验证自包含: 本地 esc + 内联空态）"""
    chart_page.evaluate("""
      window.emptyState = undefined; window.esc = undefined;
      delete window.__chartsLoaded; delete window.charts;
    """)
    chart_page.evaluate(CHARTS_JS)
    chart_page.evaluate("window.charts.bar(document.getElementById('root'), [])")
    text = chart_page.evaluate("document.querySelector('.hm-c-empty')?.textContent")
    assert text == '📊 暂无数据'


# ── 图表视觉回归守卫（#288 验收抓 bug: donut 图例色点重叠）─────────────────

def test_charts_donut_legend_dot_not_overlapping_name(chart_page):
    """donut 图例色点与名称不得重叠（回归: v1.3 初版复用 .hm-c-dot 类 → 绝对定位拉出文档流叠到名称上）"""
    chart_page.evaluate("""
      window.charts.donut(document.getElementById('root'),
        [{label:'食品',value:120},{label:'出行',value:80},{label:'日用',value:50}]);
    """)
    rows = chart_page.evaluate("""
      (() => [...document.querySelectorAll('.hm-c-dl')].map(r => {
        const dot = r.querySelector('.hm-c-dl-dot');
        const name = r.querySelector('.hm-c-dl-n');
        if (!dot || !name) return {err: 'missing'};
        const dr = dot.getBoundingClientRect();
        const nr = name.getBoundingClientRect();
        return { overlapX: dr.x + dr.width > nr.x + 1, vGap: Math.round(nr.y - dr.y) };
      }))()
    """)
    assert len(rows) == 3
    for r in rows:
        assert 'err' not in r, r
        assert r['overlapX'] is False, f'色点与名称重叠: {r}'
        # 色点与名称垂直对齐（同一行, 高度差 < 色点高度）
        assert abs(r['vGap']) < 12, f'色点与名称错行: {r}'


def test_charts_donut_legend_dot_uses_own_class(chart_page):
    """donut 图例色点用独立类 .hm-c-dl-dot（不得复用折线图 .hm-c-dot 的绝对定位类）"""
    # line 渲染到 #cLine, donut 渲染到 #cDon —— 独立容器防互相覆盖
    chart_page.evaluate("""
      document.getElementById('root').innerHTML = '<div id="cLine"></div><div id="cDon"></div>';
      window.charts.line(document.getElementById('cLine'),
        [{label:'A',value:1},{label:'B',value:2},{label:'C',value:3}]);
      window.charts.donut(document.getElementById('cDon'),
        [{label:'食品',value:120},{label:'出行',value:80}]);
    """)
    line_dot_pos = chart_page.evaluate("""
      (() => {
        const el = document.querySelector('.hm-c-dot');
        return el ? getComputedStyle(el).position : 'n/a';
      })()
    """)
    don_dot_pos = chart_page.evaluate("""
      (() => {
        const el = document.querySelector('.hm-c-dl-dot');
        return el ? getComputedStyle(el).position : 'n/a';
      })()
    """)
    has_dl = chart_page.evaluate("document.querySelector('.hm-c-dl-dot') !== null")
    assert has_dl is True
    assert line_dot_pos == 'absolute'
    assert don_dot_pos in ('static', 'relative'), f'图例色点不应绝对定位: {don_dot_pos}'


def test_charts_bar_mobile_long_label_not_clipped(chart_page):
    """手机 375px: bar 长标签(6 字)完整显示, 不省略号截断（回归: 56px max-width 截断）"""
    chart_page.set_viewport_size({'width': 375, 'height': 700})
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'厨房小家电',value:26},{label:'数码产品配件',value:18},{label:'换季衣物鞋帽',value:31},
         {label:'客厅家具家装',value:14},{label:'儿童图书文具',value:22},{label:'日用百货杂项',value:17}]);
    """)
    clipped = chart_page.evaluate("""
      (() => [...document.querySelectorAll('.hm-c-l')].map(el => el.scrollWidth > el.clientWidth))()
    """)
    assert clipped == [False] * 6, f'长标签被截断: {clipped}'
