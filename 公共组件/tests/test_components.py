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


def _stack_titles(page):
    return page.evaluate("Array.from(document.querySelectorAll('#hm-toast-stack .hm-toast .hm-toast-title')).map(e => e.textContent)")


def test_toast_stack(page):
    _clear_toasts(page)
    page.evaluate("""
      window.toast('A','',{timeout:5000});
      window.toast('B','',{timeout:5000});
    """)
    page.wait_for_timeout(80)
    count = page.evaluate("document.querySelectorAll('.hm-toast').length")
    assert count == 2  # 堆叠: 同屏最多 N 条（N=5）同时可见
    titles = _stack_titles(page)
    assert titles == ['A', 'B']  # 老上旧下: A 在上（先入栈）, B 在下


def test_toast_stack_evict_oldest(page):
    _clear_toasts(page)
    page.evaluate("""
      ['A','B','C','D','E','F'].forEach(function(t){
        window.toast(t,'',{timeout:5000});
      });
    """)
    page.wait_for_timeout(80)
    titles = _stack_titles(page)
    assert len(titles) == 5  # 默认 N=5, 超 N 挤掉最旧
    assert 'A' not in titles
    assert titles == ['B', 'C', 'D', 'E', 'F']  # FIFO: B 成为最旧, 在顶部


def test_toast_stack_max_stack_opt(page):
    _clear_toasts(page)
    page.evaluate("""
      ['A','B','C'].forEach(function(t){
        window.toast(t,'',{timeout:5000,maxStack:2});
      });
    """)
    page.wait_for_timeout(80)
    titles = _stack_titles(page)
    assert titles == ['B', 'C']  # opts.maxStack=2: A 被挤掉, B 上 C 下


def test_toast_stack_mobile_cap(page):
    _clear_toasts(page)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.evaluate("""
      ['A','B','C','D'].forEach(function(t){
        window.toast(t,'',{timeout:5000});
      });
    """)
    page.wait_for_timeout(80)
    titles = _stack_titles(page)
    assert len(titles) == 3  # ≤820px 视口上限收窄为 3
    assert titles == ['B', 'C', 'D']  # 仍挤最旧


def test_toast_stack_dismiss_reflow(page):
    _clear_toasts(page)
    page.evaluate("""
      window.toast('A','',{timeout:300});
      window.toast('B','',{timeout:5000});
    """)
    page.wait_for_timeout(700)
    titles = _stack_titles(page)
    assert titles == ['B']  # A 到时消失, B 独立计时不受影响


def test_toast_flush_clears_stack(page):
    _clear_toasts(page)
    page.evaluate("""
      window.toast('A','',{timeout:5000});
      window.toast('B','',{timeout:5000});
      window.__hmToastFlush();
    """)
    page.wait_for_timeout(80)
    count = page.evaluate("document.querySelectorAll('.hm-toast').length")
    assert count == 0


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


def test_status_badge_invalid_value_fallback(page):
    """非法 status 值降级 empty（防无样式徽章, #290 加固）"""
    page.evaluate("document.getElementById('root').innerHTML = window.statusBadge('info','自定义') + window.statusBadge('unknown')")
    cls = page.evaluate("document.querySelectorAll('.hm-status')[0]?.className")
    txt = page.evaluate("document.querySelectorAll('.hm-status')[1]?.textContent")
    assert 'empty' in cls and txt == '无数据'  # 非法值 → empty 样式 + 默认文案


def test_status_badge_esc_anti_xss(page):
    """statusBadge text 转义, 防 XSS（#290 加固）"""
    page.evaluate("document.getElementById('root').innerHTML = window.statusBadge('warn','<img src=x onerror=alert(1)>')")
    img = page.evaluate("document.querySelector('.hm-status img') !== null")
    raw = page.evaluate("document.getElementById('root').innerHTML")
    assert img is False and '&lt;img' in raw and '<img src' not in raw


def test_empty_state(page):
    page.evaluate("document.getElementById('root').innerHTML = window.emptyState({icon:'📭',text:'今天没有记录',hint:'说「记作息」开始记录'})")
    assert page.evaluate("document.querySelector('.hm-empty-text')?.textContent") == '今天没有记录'
    assert page.evaluate("document.querySelector('.hm-empty-hint')?.textContent") == '说「记作息」开始记录'
    assert page.evaluate("document.querySelector('.hm-empty-icon')?.textContent") == '📭'


def test_empty_state_defaults(page):
    """emptyState 缺省 text 与 action 透传（#290 加固: action 受信 HTML, text 默认文案）"""
    page.evaluate("document.getElementById('root').innerHTML = window.emptyState({})")
    assert page.evaluate("document.querySelector('.hm-empty-text')?.textContent") == '暂无数据'
    page.evaluate("document.getElementById('root').innerHTML = window.emptyState({action:'<button class=\"copy\" onclick=\"window.__tap=1\">去记录</button>'})")
    btn = page.evaluate("document.querySelector('.hm-empty-action .copy')?.textContent")
    page.click('.hm-empty-action .copy')
    assert btn == '去记录' and page.evaluate('window.__tap') == 1


def test_empty_state_esc_anti_xss(page):
    """emptyState icon/text/hint 转义防 XSS; action 受信 HTML 透传（契约明示）"""
    page.evaluate("document.getElementById('root').innerHTML = window.emptyState({text:'<img src=x onerror=alert(1)>',hint:'<script>1</script>'})")
    img = page.evaluate("document.querySelector('.hm-empty img') !== null")
    hint_script = page.evaluate("document.querySelector('.hm-empty-hint script') !== null")
    assert img is False and hint_script is False


def test_error_receipt(page):
    """errorReceipt: message + retryPrompt + 显式 payload → 三按钮（08 §6.1 三层反馈）"""
    page.evaluate(
        "document.getElementById('root').innerHTML = window.errorReceipt({message:'写入失败',retryPrompt:'请重试',payload:" +
        json.dumps(VALID_PAYLOAD, ensure_ascii=False) + "})")
    assert page.evaluate("document.querySelector('.hm-error-title')?.textContent") == '❌ 写入失败'
    btns = page.evaluate("[...document.querySelectorAll('.hm-error .copy')].map(n=>n.textContent)")
    assert '修正重试' in btns and '复制数据' in btns and '复制日志' in btns
    # 按钮布局: 修正重试 wide 独立一行, 复制数据/日志一行（.hm-actions 网格）
    retry_cls = page.evaluate("document.querySelector('.hm-error .copy.primary')?.className")
    actions = page.evaluate("document.querySelectorAll('.hm-error .hm-actions').length")
    assert 'wide' in retry_cls and actions >= 1


def test_error_receipt_data_log_strings(page):
    """errorReceipt data/log 字符串直传, 不依赖全局 payload（#290 修复: 去掉 __hmPayload 强依赖）"""
    page.evaluate("window.__hmPayload = undefined")  # 清掉可能的全局残留, 验证不依赖
    page.evaluate("document.getElementById('root').innerHTML = window.errorReceipt({message:'失败',data:'现场数据',log:'故障链'})")
    data_btn = page.evaluate("document.querySelector('.hm-error .copy.ghost[data-t=\"现场数据\"]') !== null")
    log_btn = page.evaluate("document.querySelector('.hm-error .copy.ghost[data-t=\"故障链\"]') !== null")
    assert data_btn and log_btn


def test_error_receipt_no_payload_graceful(page):
    """errorReceipt 无 payload 无 data/log: 只渲染 message + 修正重试, 复制按钮不出现（不崩）"""
    page.evaluate("window.__hmPayload = undefined")
    page.evaluate("document.getElementById('root').innerHTML = window.errorReceipt({message:'失败',retryPrompt:'重试'})")
    btns = page.evaluate("[...document.querySelectorAll('.hm-error .copy')].map(n=>n.textContent)")
    assert btns == ['修正重试']  # 无数据可复制 → 不渲染复制数据/日志


def test_error_receipt_incomplete_payload_no_crash(page):
    """errorReceipt payload 结构不完整（缺 snapshot）: 复制按钮不渲染, 控件不抛错（#290 容错）"""
    bad = {'status': 'ok', 'data': {'meta': {}, 'scene': {'scene_id': 'x'}}}  # 无 snapshot
    page.evaluate(
        "document.getElementById('root').innerHTML = window.errorReceipt({message:'失败',payload:" +
        json.dumps(bad, ensure_ascii=False) + "})")
    btns = page.evaluate("[...document.querySelectorAll('.hm-error .copy')].map(n=>n.textContent)")
    assert '复制数据' not in btns and '复制日志' not in btns
    assert page.evaluate("document.querySelector('.hm-error-title')?.textContent") == '❌ 失败'


def test_error_receipt_esc_anti_xss(page):
    """errorReceipt message/data/log 转义防 XSS（#290 加固: 零注入面）"""
    page.evaluate("document.getElementById('root').innerHTML = window.errorReceipt({message:'<img src=x onerror=alert(1)>',data:'<script>1</script>'})")
    img = page.evaluate("document.querySelector('.hm-error-title img') !== null")
    script = page.evaluate("document.querySelector('.hm-error script') !== null")
    assert img is False and script is False


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
    chart_page.evaluate("window.charts.progress(document.getElementById('root'), 65, {animation:false})")
    fill = chart_page.evaluate("document.querySelector('.hm-c-p-fill')?.style.width")
    num = chart_page.evaluate("document.querySelector('.hm-c-p-n')?.textContent")
    assert fill == '65%' and num == '65%'


def test_charts_progress_clamps(chart_page):
    """超界收敛 0~100; 非数直接报错（v1.4 结构校验: 违规报错, 对齐 Base）"""
    chart_page.evaluate("window.charts.progress(document.getElementById('root'), 999, {animation:false})")
    num = chart_page.evaluate("document.querySelector('.hm-c-p-n')?.textContent")
    assert num == '100%'
    err = chart_page.evaluate("""() => { try { window.charts.progress(document.getElementById('root'), 'abc'); return ''; } catch(e) { return e.message; } }""")
    assert 'pct' in err and '无效' in err


def test_charts_progress_color_option(chart_page):
    chart_page.evaluate("window.charts.progress(document.getElementById('root'), 30, {color:'var(--ok,#34c759)'})")
    bg = chart_page.evaluate("document.querySelector('.hm-c-p-fill')?.style.background")
    assert '34c759' in bg


def test_charts_bar_renders(chart_page):
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'牛奶',value:3},{label:'面包',value:7},{label:'苹果',value:5}],
        {animation:false});
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


def test_charts_bar_non_array_throws(chart_page):
    """非数组输入 → 直接报错（v1.4 结构校验: 违规报错, 对齐 Base v1.2 拍板）"""
    err = chart_page.evaluate("""() => { try { window.charts.bar(document.getElementById('root'), null); return ''; } catch(e) { return e.message; } }""")
    assert 'items 必须是数组' in err


def test_charts_bar_onclick(chart_page):
    chart_page.evaluate("""
      window.__idx = -1;
      window.charts.bar(document.getElementById('root'),
        [{label:'A',value:1},{label:'B',value:2}],
        {onclick:function(i){window.__idx=i;},animation:false});
    """)
    chart_page.click('.hm-c-b[data-i="1"]')
    assert chart_page.evaluate('window.__idx') == 1


def test_charts_line_renders(chart_page):
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'),
        [{label:'周一',value:2},{label:'周二',value:5},{label:'周三',value:3}],
        {animation:false});
    """)
    path_d = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']")?.getAttribute(\'d\')')
    dots = chart_page.evaluate("document.querySelectorAll('.hm-c-dot').length")
    xs = chart_page.evaluate("document.querySelector('.hm-c-line-x')?.textContent")
    assert path_d and dots == 3 and '周一' in xs and '周三' in xs


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
         {label:'类别四',value:4},{label:'类别五',value:5},{label:'类别六',value:6}],
        {animation:false});
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
         {label:'客厅家具家装',value:14},{label:'儿童图书文具',value:22},{label:'日用百货杂项',value:17}],
        {animation:false});
    """)
    clipped = chart_page.evaluate("""
      (() => [...document.querySelectorAll('.hm-c-l')].map(el => el.scrollWidth > el.clientWidth))()
    """)
    assert clipped == [False] * 6, f'长标签被截断: {clipped}'

# ── v1.4 全参数测试 ──────────────────────────────────────

@pytest.fixture(autouse=True)
def _v14_desktop_viewport(chart_page):
    """v1.4 区测试统一桌面视口（修复 module 级 page 被前序手机测试改宽度的顺序污染）"""
    chart_page.set_viewport_size({'width': 1200, 'height': 800})
    yield

LINE_ITEMS = [
    {'label': '周一', 'value': 2}, {'label': '周二', 'value': 5},
    {'label': '周三', 'value': 3}, {'label': '周四', 'value': 8},
    {'label': '周五', 'value': 6},
]
BAR_ITEMS = [
    {'label': '牛奶', 'value': 3}, {'label': '面包', 'value': 7}, {'label': '苹果', 'value': 5},
]
DONUT_ITEMS = [
    {'label': '食品', 'value': 120}, {'label': '出行', 'value': 80}, {'label': '日用', 'value': 50},
]


# ── line: 16 项参数 ─────────────────────────────────────

def test_line_height_param(chart_page):
    """height 覆盖（默认 210 / 传 320）"""
    chart_page.set_viewport_size({'width': 1200, 'height': 800})
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false})', LINE_ITEMS)
    h1 = chart_page.evaluate("document.querySelector('.hm-c-line-wrap').getBoundingClientRect().height")
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, height:320})', LINE_ITEMS)
    h2 = chart_page.evaluate("document.querySelector('.hm-c-line-wrap').getBoundingClientRect().height")
    assert h1 == 210 and h2 == 320


def test_line_color_width_dashed(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, color:"#ff3b30", lineWidth:4, dashed:true})', LINE_ITEMS)
    stroke = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'stroke\')')
    sw = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'stroke-width\')')
    dash = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'stroke-dasharray\')')
    assert stroke == '#ff3b30' and sw == '4' and dash


def test_line_smooth_keeps_dots_on_curve(chart_page):
    """平滑曲线: 数据点仍落在真实位置（与曲线 path 节点一致）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, smooth:true})', LINE_ITEMS)
    path_d = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    assert 'C' in path_d  # 三次贝塞尔曲线
    dots = chart_page.evaluate("document.querySelectorAll('.hm-c-dot').length")
    assert dots == 5


def test_line_show_dots_off(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, showDots:false})', LINE_ITEMS)
    dots = chart_page.evaluate("document.querySelectorAll('.hm-c-dot').length")
    assert dots == 0


def test_line_area_fill(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, area:true})', LINE_ITEMS)
    area = chart_page.evaluate("document.querySelector('.hm-c-line-svg path[fill]')")
    assert area is not None
    op = chart_page.evaluate("document.querySelector('.hm-c-line-svg path[fill]').getAttribute('opacity')")
    assert op == '0.12'


def test_line_labels_all_none_select(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, labels:"all"})', LINE_ITEMS)
    n_all = chart_page.evaluate("document.querySelectorAll('.hm-c-line-x span').length")
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, labels:"none"})', LINE_ITEMS)
    n_none = chart_page.evaluate("document.querySelectorAll('.hm-c-line-x span').length")
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, labels:"select"})', LINE_ITEMS)
    n_sel = chart_page.evaluate("document.querySelectorAll('.hm-c-line-x span').length")
    assert n_all == 5 and n_none == 0 and n_sel == 3  # 首+峰+尾


def test_line_show_values(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, showValues:true})', LINE_ITEMS)
    vals = chart_page.evaluate("[...document.querySelectorAll('.hm-c-vt')].map(n=>n.textContent)")
    assert vals == ['2', '5', '3', '8', '6']


def test_line_format(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, format:"¥{v}", showValues:true})', LINE_ITEMS)
    vals = chart_page.evaluate("[...document.querySelectorAll('.hm-c-vt')].map(n=>n.textContent)")
    assert vals[0] == '¥2'


def test_line_y_axis_range(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, yMin:0, yMax:10})', LINE_ITEMS)
    # 无报错即通过（值域覆盖生效）


def test_line_grid_off(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, grid:false})', LINE_ITEMS)
    lines = chart_page.evaluate("document.querySelectorAll('.hm-c-line-svg line').length")
    assert lines == 0


def test_line_missing_value_breaks(chart_page):
    """缺失值断线: null 点不连线, path 分多段"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), [{label:'a',value:1},{label:'b',value:null},{label:'c',value:3}], {animation:false})")
    path_d = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    assert path_d.count('M') == 2  # 两段独立


def test_line_markline(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, markLine:{value:7,label:"目标 7"}})', LINE_ITEMS)
    mark = chart_page.evaluate('document.querySelector(".hm-c-line-svg line[stroke=\'#ff9500\']")')
    lbl = chart_page.evaluate("document.querySelector('.hm-c-markline-t')?.textContent")
    assert mark is not None and lbl == '目标 7'


def test_line_avg_line(chart_page):
    """移动均线叠加为虚线"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, avgLine:3})', LINE_ITEMS)
    paths = chart_page.evaluate('document.querySelectorAll(".hm-c-line-svg path[fill=\'none\']")')
    assert len(paths) == 2  # 主线 + 均线
    avg_dash = chart_page.evaluate('document.querySelectorAll(".hm-c-line-svg path[fill=\'none\']")[1].getAttribute(\'stroke-dasharray\')')
    assert avg_dash  # 均线虚线


def test_line_series_and_legend(chart_page):
    chart_page.evaluate("""
      (items) => window.charts.line(document.getElementById('root'), items, {animation:false,
        series:[{name:'录入',items:items},{name:'废弃',items:[{label:'周一',value:1},{label:'周二',value:2},{label:'周三',value:1},{label:'周四',value:3},{label:'周五',value:2}]}],
        legend:true});
    """, LINE_ITEMS)
    paths = chart_page.evaluate('document.querySelectorAll(".hm-c-line-svg path[fill=\'none\']").length')
    lg = chart_page.evaluate("[...document.querySelectorAll('.hm-c-lg')].map(n=>n.textContent)")
    assert paths == 2 and lg == ['录入', '废弃']


def test_line_highlight_last(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, highlightLast:true})', LINE_ITEMS)
    last = chart_page.evaluate("document.querySelector('.hm-c-dot-last')")
    assert last is not None


def test_line_ondrill(chart_page):
    chart_page.evaluate("""
      (items) => { window.__drill = -1;
      window.charts.line(document.getElementById('root'), items, {animation:false,
        ondrill:function(i){window.__drill=i;}}); }
    """, LINE_ITEMS)
    chart_page.click('.hm-c-line-svg svg')
    assert chart_page.evaluate('window.__drill') >= 0


def test_line_tooltip(chart_page):
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, tooltip:true})', LINE_ITEMS)
    chart_page.hover('.hm-c-line-svg')
    tip = chart_page.evaluate("document.querySelector('.hm-c-tip.show')?.textContent")
    assert tip is not None  # hover 最近点提示出现（中点=周三附近, 不断言具体点）


def test_line_validate_throws(chart_page):
    err = chart_page.evaluate("""() => { try { window.charts.line(document.getElementById('root'), [{label:'x'}]); return ''; } catch(e) { return e.message; } }""")
    assert 'value' in err
    err2 = chart_page.evaluate("""() => { try { window.charts.line(document.getElementById('root'), [{value:1}]); return ''; } catch(e) { return e.message; } }""")
    assert 'label' in err2


# ── bar: 参数对齐 ───────────────────────────────────────

def test_bar_format_and_single_color(chart_page):
    chart_page.evaluate('(items) => window.charts.bar(document.getElementById("root"), items, {animation:false, format:"¥{v}", singleColor:"#ff3b30"})', BAR_ITEMS)
    vals = chart_page.evaluate("[...document.querySelectorAll('.hm-c-v')].map(n=>n.textContent)")
    bg = chart_page.evaluate("document.querySelector('.hm-c-b').style.background")
    assert vals == ['¥3', '¥7', '¥5'] and ('#ff3b30' in bg or '255, 59, 48' in bg)


def test_bar_colors_palette(chart_page):
    chart_page.evaluate('(items) => window.charts.bar(document.getElementById("root"), items, {animation:false, colors:["#111111","#222222","#333333"]})', BAR_ITEMS)
    bgs = chart_page.evaluate("[...document.querySelectorAll('.hm-c-b')].map(n=>n.style.background)")
    # 浏览器可能归一化为 rgb() 或保留 hex —— 两种都接受
    norm = lambda c: c.replace('rgb(17, 17, 17)', '#111111').replace('rgb(34, 34, 34)', '#222222').replace('rgb(51, 51, 51)', '#333333')
    assert [norm(b) for b in bgs] == ['#111111', '#222222', '#333333']


def test_bar_labels_none(chart_page):
    chart_page.evaluate('(items) => window.charts.bar(document.getElementById("root"), items, {animation:false, labels:"none"})', BAR_ITEMS)
    n = chart_page.evaluate("document.querySelectorAll('.hm-c-labels .hm-c-l').length")
    assert n == 0


def test_bar_validate_throws(chart_page):
    err = chart_page.evaluate("""() => { try { window.charts.bar(document.getElementById('root'), 'abc'); return ''; } catch(e) { return e.message; } }""")
    assert '数组' in err


# ── donut: 参数对齐 ─────────────────────────────────────

def test_donut_format_and_size(chart_page):
    chart_page.evaluate('(items) => window.charts.donut(document.getElementById("root"), items, {animation:false, format:"¥{v}", size:200})', DONUT_ITEMS)
    v = chart_page.evaluate("document.querySelector('.hm-c-dl-v').textContent")
    sz = chart_page.evaluate("document.querySelector('.hm-c-donut').getBoundingClientRect().width")
    assert v == '¥120' and sz == 200


def test_donut_legend_none(chart_page):
    chart_page.evaluate('(items) => window.charts.donut(document.getElementById("root"), items, {animation:false, legend:"none"})', DONUT_ITEMS)
    n = chart_page.evaluate("document.querySelectorAll('.hm-c-dl').length")
    assert n == 0


def test_donut_show_percent_off(chart_page):
    chart_page.evaluate('(items) => window.charts.donut(document.getElementById("root"), items, {animation:false, showPercent:false})', DONUT_ITEMS)
    n = chart_page.evaluate("document.querySelectorAll('.hm-c-dl-p').length")
    assert n == 0


def test_donut_validate_throws(chart_page):
    err = chart_page.evaluate("""() => { try { window.charts.donut(document.getElementById('root'), 'x'); return ''; } catch(e) { return e.message; } }""")
    assert '数组' in err


# ── progress: 参数对齐 ──────────────────────────────────

def test_progress_gradient_and_height(chart_page):
    chart_page.evaluate("window.charts.progress(document.getElementById('root'), 60, {animation:false, gradient:true, height:14, color:'#34c759'})")
    bg = chart_page.evaluate("document.querySelector('.hm-c-p-fill').style.background")
    th = chart_page.evaluate("document.querySelector('.hm-c-p-track').style.height")
    assert 'gradient' in bg and th == '14px'


def test_progress_show_pct_off(chart_page):
    chart_page.evaluate("window.charts.progress(document.getElementById('root'), 60, {animation:false, showPct:false})")
    n = chart_page.evaluate("document.querySelectorAll('.hm-c-p-n').length")
    assert n == 0


# ── 复合形态 ────────────────────────────────────────────

def test_combo_renders(chart_page):
    chart_page.evaluate("""
      window.charts.combo(document.getElementById('root'),
        {bars:[{label:'1月',value:30},{label:'2月',value:60},{label:'3月',value:45}],
         lines:[{label:'1月',value:2},{label:'2月',value:4},{label:'3月',value:3}]},
        {animation:false});
    """)
    cols = chart_page.evaluate("document.querySelectorAll('.hm-c-col').length")
    dots = chart_page.evaluate("document.querySelectorAll('.hm-c-combo-dot').length")
    assert cols == 3 and dots == 3


def test_combo_line_dot_on_bar_top(chart_page):
    """combo 线点精确落在柱顶 + 分散在各柱列（回归: v1.6 初版双坐标系错位 + 点 left:50% 相对 plot 导致水平堆叠）"""
    chart_page.set_viewport_size({'width': 1200, 'height': 800})
    chart_page.evaluate("""
      window.charts.combo(document.getElementById('root'),
        {bars:[{label:'1月',value:30},{label:'2月',value:60},{label:'3月',value:45},{label:'4月',value:80},{label:'5月',value:55}],
         lines:[{label:'1月',value:12},{label:'2月',value:22},{label:'3月',value:16},{label:'4月',value:30},{label:'5月',value:20}]},
        {animation:false});
    """)
    res = chart_page.evaluate("""
      (() => {
        const dots = [...document.querySelectorAll('.hm-c-combo-dot')];
        const bars = [...document.querySelectorAll('.hm-c-b')];
        const errs = dots.map((d, i) => {
          const dr = d.getBoundingClientRect(), br = bars[i].getBoundingClientRect();
          return Math.abs((dr.y + dr.height/2) - br.y);
        });
        const xs = dots.map(d => d.getBoundingClientRect().x);
        const xDup = xs.length - new Set(xs.map(x => Math.round(x))).size;
        const xSpread = Math.max(...xs) - Math.min(...xs);
        return { errs, xDup, xSpread };
      })()
    """)
    assert all(e < 1.5 for e in res['errs']), f'combo 线点未落柱顶: {res["errs"]}'
    assert res['xDup'] == 0, f'combo 线点水平堆叠 {res["xDup"]} 个'
    assert res['xSpread'] > 50, 'combo 线点未分散各柱列'


def test_combo_throws_on_length_mismatch(chart_page):
    err = chart_page.evaluate("""() => { try { window.charts.combo(document.getElementById('root'), {bars:[{label:'a',value:1}],lines:[{label:'b',value:2},{label:'c',value:3}]}); return ''; } catch(e) { return e.message; } }""")
    assert '长度不一致' in err


def test_sparkline_up_down_color(chart_page):
    chart_page.evaluate("window.charts.sparkline(document.getElementById('root'), [{label:'a',value:1},{label:'b',value:3}])")
    up_cls = chart_page.evaluate("document.querySelector('.hm-c-sp-v').className")
    assert 'up' in up_cls
    chart_page.evaluate("window.charts.sparkline(document.getElementById('root'), [{label:'a',value:3},{label:'b',value:1}])")
    down_cls = chart_page.evaluate("document.querySelector('.hm-c-sp-v').className")
    assert 'down' in down_cls


def test_gauge_renders(chart_page):
    chart_page.evaluate("window.charts.gauge(document.getElementById('root'), 72, {label:'完成度', animation:false})")
    val = chart_page.evaluate("document.querySelector('.hm-c-gv').textContent")
    lbl = chart_page.evaluate("document.querySelector('.hm-c-gl').textContent")
    assert val == '72%' and lbl == '完成度'


def test_gauge_throws_on_invalid(chart_page):
    err = chart_page.evaluate("""() => { try { window.charts.gauge(document.getElementById('root'), 'x'); return ''; } catch(e) { return e.message; } }""")
    assert 'pct' in err
