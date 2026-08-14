# -*- coding: utf-8 -*-
"""Base 控件函数测试 v1.2

覆盖（Playwright 浏览器环境, 无 DB 接触）:
- snapshot 结构校验: 缺 title / summary 非数组 / sections 缺 heading → 报错（违规直接报错）
- buildDataText: text/json/csv 三种 format; 脱敏行; 头部/摘要/分节输出
- buildLogText: 6 段结构; 缺省字段兜底
- toast 增强: 徽章/操作/计数/队列/向后兼容
- copyText 反馈钩子（v1.10 · #328）: toast 文案配置 + onOk/onFail 回调
- 新控件: formPrompt（预览+空值拦截）/ selectList（计数联动 + v1.9 行内控件）/ confirm / foldBox / statusBadge / emptyState / errorReceipt
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


# ── copyText 反馈钩子（v1.10 · #328）────────────────────────

def _stub_exec_command(page, ok):
    """钉死 document.execCommand 返回值, 让 copyText 走 _fbCopy 兜底路径（Playwright 无 clipboard, 确定性成败）"""
    page.evaluate("document.execCommand = function(){ return %s; }" % ('true' if ok else 'false'))


def test_copy_text_default_toast_regression(page):
    """无新选项: 成功/失败 toast 与 v1.9 逐字一致（向后兼容回归）"""
    _clear_toasts(page)
    _stub_exec_command(page, True)
    page.evaluate("window.copyText('abc')")
    page.wait_for_timeout(80)
    title = page.evaluate("document.querySelector('.hm-toast .hm-toast-title')?.textContent")
    detail = page.evaluate("document.querySelector('.hm-toast .hm-toast-detail')?.textContent")
    assert title == '已复制' and detail == '粘贴给 AI'
    _clear_toasts(page)
    _stub_exec_command(page, False)
    page.evaluate("window.copyText('abc')")
    page.wait_for_timeout(80)
    title = page.evaluate("document.querySelector('.hm-toast .hm-toast-title')?.textContent")
    detail = page.evaluate("document.querySelector('.hm-toast .hm-toast-detail')?.textContent")
    chip = page.evaluate("document.querySelector('.hm-toast-chip')?.textContent")
    assert title == '复制失败' and detail == '长按选择文本手动复制' and chip == '失败'


def test_copy_text_custom_toast_texts(page):
    """opts.toast 自定义文案: 成功/失败分别用自定义 msg+detail"""
    _clear_toasts(page)
    _stub_exec_command(page, True)
    page.evaluate("window.copyText('abc',{toast:{ok:{msg:'已存剪贴板',detail:'发给 AI 执行'},fail:{msg:'复制失败啦',detail:'请长按手动复制'}}})")
    page.wait_for_timeout(80)
    title = page.evaluate("document.querySelector('.hm-toast .hm-toast-title')?.textContent")
    detail = page.evaluate("document.querySelector('.hm-toast .hm-toast-detail')?.textContent")
    assert title == '已存剪贴板' and detail == '发给 AI 执行'
    _clear_toasts(page)
    _stub_exec_command(page, False)
    page.evaluate("window.copyText('abc',{toast:{ok:{msg:'已存剪贴板',detail:'发给 AI 执行'},fail:{msg:'复制失败啦',detail:'请长按手动复制'}}})")
    page.wait_for_timeout(80)
    title = page.evaluate("document.querySelector('.hm-toast .hm-toast-title')?.textContent")
    detail = page.evaluate("document.querySelector('.hm-toast .hm-toast-detail')?.textContent")
    assert title == '复制失败啦' and detail == '请长按手动复制'


def test_copy_text_toast_partial_override(page):
    """只覆盖部分字段: 缺省回落默认（msg 自定义 + detail 缺省）"""
    _clear_toasts(page)
    _stub_exec_command(page, True)
    page.evaluate("window.copyText('abc',{toast:{ok:{msg:'已复制!'}}})")
    page.wait_for_timeout(80)
    title = page.evaluate("document.querySelector('.hm-toast .hm-toast-title')?.textContent")
    detail = page.evaluate("document.querySelector('.hm-toast .hm-toast-detail')?.textContent")
    assert title == '已复制!' and detail == '粘贴给 AI'


def test_copy_text_icon_override(page):
    """opts.toast 图标覆盖: 成功/失败 toast 图标换自定义 emoji"""
    _clear_toasts(page)
    _stub_exec_command(page, True)
    page.evaluate("window.copyText('abc',{toast:{ok:{icon:'🎉'},fail:{icon:'😭'}}})")
    page.wait_for_timeout(80)
    icon = page.evaluate("document.querySelector('.hm-toast-icon')?.textContent")
    assert icon == '🎉'
    _clear_toasts(page)
    _stub_exec_command(page, False)
    page.evaluate("window.copyText('abc',{toast:{ok:{icon:'🎉'},fail:{icon:'😭'}}})")
    page.wait_for_timeout(80)
    icon = page.evaluate("document.querySelector('.hm-toast-icon')?.textContent")
    assert icon == '😭'


def test_copy_text_on_ok_on_fail_callbacks(page):
    """onOk 成功触发 / onFail 最终失败触发, 互斥"""
    _clear_toasts(page)
    _stub_exec_command(page, True)
    page.evaluate("window.__ok = 0; window.__fail = 0; window.copyText('abc',{onOk:function(){window.__ok=1;},onFail:function(){window.__fail=1;}})")
    page.wait_for_timeout(80)
    assert page.evaluate('window.__ok') == 1 and page.evaluate('window.__fail') == 0
    _clear_toasts(page)
    _stub_exec_command(page, False)
    page.evaluate("window.__ok = 0; window.__fail = 0; window.copyText('abc',{onOk:function(){window.__ok=1;},onFail:function(){window.__fail=1;}})")
    page.wait_for_timeout(80)
    assert page.evaluate('window.__ok') == 0 and page.evaluate('window.__fail') == 1


def test_copy_text_silent_keeps_callbacks(page):
    """silent + 钩子组合: 不弹 toast 仍触发回调（08 规范定制文案场景）"""
    _clear_toasts(page)
    _stub_exec_command(page, True)
    page.evaluate("window.__ok = 0; window.copyText('abc',{silent:true,onOk:function(){window.__ok=1;}})")
    page.wait_for_timeout(80)
    assert page.evaluate('window.__ok') == 1
    assert page.evaluate("document.querySelectorAll('.hm-toast').length") == 0


def test_copy_text_empty_string_noop(page):
    """空串复制: 直接 return, 无 toast 无回调"""
    _clear_toasts(page)
    _stub_exec_command(page, True)
    page.evaluate("window.__ok = 0; window.copyText('',{onOk:function(){window.__ok=1;}})")
    page.wait_for_timeout(80)
    assert page.evaluate('window.__ok') == 0
    assert page.evaluate("document.querySelectorAll('.hm-toast').length") == 0


def test_copy_text_clipboard_promise_path(page):
    """navigator.clipboard Promise 路径（主路径）: resolve → onOk; reject+兜底失败 → onFail
    （前 7 项走 _fbCopy 兜底路径; 本项钉死 clipboard 主路径, 两路径共享 ok()/fail() 须行为一致）"""
    _clear_toasts(page)
    page.evaluate("""
      Object.defineProperty(navigator, 'clipboard', {value: {writeText: function(){ return Promise.resolve(); }}, configurable: true});
      window.__ok = 0; window.__fail = 0;
      window.copyText('abc',{onOk:function(){window.__ok=1;},onFail:function(){window.__fail=1;}});
    """)
    page.wait_for_timeout(120)
    assert page.evaluate('window.__ok') == 1 and page.evaluate('window.__fail') == 0
    _clear_toasts(page)
    _stub_exec_command(page, False)
    page.evaluate("""
      Object.defineProperty(navigator, 'clipboard', {value: {writeText: function(){ return Promise.reject(new Error('denied')); }}, configurable: true});
      window.__ok = 0; window.__fail = 0;
      window.copyText('abc',{onOk:function(){window.__ok=1;},onFail:function(){window.__fail=1;}});
    """)
    page.wait_for_timeout(120)
    assert page.evaluate('window.__ok') == 0 and page.evaluate('window.__fail') == 1


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


# ── selectList 行内控件（v1.9 · #327）──────────────────────

def test_select_list_widget_text_renders(page):
    """text 控件: 输入框 + label + placeholder 渲染, 与勾选行共存"""
    page.evaluate("""
      document.getElementById('root').innerHTML = window.selectList(
        [{id:'a',title:'牛奶',widget:{type:'text',key:'qty',label:'数量',placeholder:'如 2 瓶'}}],
        [{label:'确认',kind:'ok',onClick:function(){}}]
      );
    """)
    page.wait_for_timeout(100)
    typ = page.evaluate("document.querySelector('.sl-widget-input').type")
    label = page.evaluate("document.querySelector('.sl-widget-label')?.textContent")
    ph = page.evaluate("document.querySelector('.sl-widget-input').placeholder")
    title = page.evaluate("document.querySelector('.sl-item-title')?.textContent")
    cb = page.evaluate("document.querySelector('.sl-item input[type=checkbox]') !== null")
    assert typ == 'text' and label == '数量' and ph == '如 2 瓶'
    assert title == '牛奶' and cb is True  # 与勾选行共存


def test_select_list_widget_date_renders(page):
    """date 控件: type=date 输入框"""
    page.evaluate("""
      document.getElementById('root').innerHTML = window.selectList(
        [{id:'a',title:'换分类',widget:{type:'date',key:'date',label:'日期'}}]
      );
    """)
    page.wait_for_timeout(100)
    typ = page.evaluate("document.querySelector('.sl-widget-input').type")
    assert typ == 'date'


def test_select_list_widget_select_renders(page):
    """select 控件: options 渲染（value+label 分离）"""
    page.evaluate("""
      document.getElementById('root').innerHTML = window.selectList(
        [{id:'a',title:'分类',widget:{type:'select',key:'cat',label:'新分类',
          options:[{value:'食',label:'食品'},{value:'用',label:'日用'}]}}]
      );
    """)
    page.wait_for_timeout(100)
    opts = page.evaluate("[...document.querySelectorAll('.sl-widget-input option')].map(o => o.value + ':' + o.textContent)")
    assert opts == ['食:食品', '用:日用']
    sel = page.evaluate("document.querySelector('.sl-widget-input').selectedIndex")
    assert sel == 0  # 默认选第一项


def test_select_list_on_submit_reads_all_values(page):
    """读取接口 opts.onSubmit: 全部行内值（含未勾选条目）, 未填 → null"""
    page.evaluate("""
      window.__sub = null;
      document.getElementById('root').innerHTML = window.selectList(
        [
          {id:'a',title:'牛奶',widget:{type:'text',key:'qty'}},
          {id:'b',title:'面包',widget:{type:'select',key:'cat',options:['冷藏','常温']}},
          {id:'c',title:'苹果',widget:{type:'date',key:'day'}}
        ],
        [{label:'确认',kind:'ok',onClick:function(){}}],
        {onSubmit:function(ids, values){window.__sub = {ids: ids, values: values};}}
      );
    """)
    page.wait_for_timeout(100)
    page.check('.sl-item input[data-id="a"]')
    page.check('.sl-item input[data-id="c"]')
    page.fill('label.sl-item:has(input[data-id="a"]) .sl-widget-input', '2')
    page.select_option('label.sl-item:has(input[data-id="b"]) .sl-widget-input', '常温')
    page.click('[data-batch="确认"]')
    page.wait_for_timeout(50)
    sub = page.evaluate('window.__sub')
    assert sub['ids'] == ['a', 'c']                  # 勾选 a、c
    assert sub['values']['a'] == {'qty': '2'}        # 已填
    assert sub['values']['b'] == {'cat': '常温'}     # 未勾选条目也在全部值里
    assert sub['values']['c'] == {'day': None}       # 未填 → null


def test_select_list_batch_onclick_reads_checked_values(page):
    """批量回调第二参 = 勾选条目行内值（只读勾选; 未勾选不参与; 未填 → null 不报错）"""
    page.evaluate("""
      window.__cb = null;
      document.getElementById('root').innerHTML = window.selectList(
        [
          {id:'a',title:'牛奶',widget:{type:'text',key:'qty'}},
          {id:'b',title:'面包',widget:{type:'select',key:'cat',options:['冷藏','常温']}},
          {id:'c',title:'苹果',widget:{type:'date',key:'day'}}
        ],
        [{label:'确认',kind:'ok',onClick:function(ids, values){window.__cb = {ids: ids, values: values};}}]
      );
    """)
    page.wait_for_timeout(100)
    page.check('.sl-item input[data-id="a"]')
    page.check('.sl-item input[data-id="b"]')
    page.fill('label.sl-item:has(input[data-id="a"]) .sl-widget-input', '2')
    page.click('[data-batch="确认"]')
    page.wait_for_timeout(50)
    cb = page.evaluate('window.__cb')
    assert cb['ids'] == ['a', 'b']
    assert cb['values']['a'] == {'qty': '2'}
    assert cb['values']['b'] == {'cat': '冷藏'}      # 勾选条目含 select 默认值
    assert 'c' not in cb['values']                   # 未勾选条目不参与批量回调


def test_select_list_widget_change_not_affect_count(page):
    """控件值变化不干扰计数联动（#327: 计数只随勾选态）"""
    page.evaluate("""
      document.getElementById('root').innerHTML = window.selectList(
        [{id:'a',title:'牛奶',widget:{type:'text',key:'qty'}},
         {id:'b',title:'面包',widget:{type:'text',key:'qty'}}],
        [{label:'确认',kind:'ok',onClick:function(){}}]
      );
    """)
    page.wait_for_timeout(100)
    page.check('.sl-item input[data-id="a"]')
    page.wait_for_timeout(50)
    assert '已选 1/2' in page.evaluate("document.querySelector('.sl-count')?.textContent")
    page.fill('label.sl-item:has(input[data-id="b"]) .sl-widget-input', 'x')
    page.wait_for_timeout(50)
    assert '已选 1/2' in page.evaluate("document.querySelector('.sl-count')?.textContent")
    page.uncheck('.sl-item input[data-id="a"]')
    page.wait_for_timeout(50)
    assert '已选 0/2' in page.evaluate("document.querySelector('.sl-count')?.textContent")


def test_select_list_widget_input_click_not_toggle(page):
    """点击行内输入框不切换勾选态（label 激活只作用于非交互区）"""
    page.evaluate("""
      document.getElementById('root').innerHTML = window.selectList(
        [{id:'a',title:'牛奶',widget:{type:'text',key:'qty'}}]
      );
    """)
    page.wait_for_timeout(100)
    page.click('label.sl-item:has(input[data-id="a"]) .sl-widget-input')
    page.wait_for_timeout(50)
    checked = page.evaluate("document.querySelector('.sl-item input[data-id=\"a\"]').checked")
    assert checked is False


def test_select_list_no_widget_backward_compat(page):
    """未声明 widget: 行渲染逐字节不变 + 批量回调照旧（守卫回归）"""
    page.evaluate("""
      window.__ids = null;
      document.getElementById('root').innerHTML = window.selectList(
        [{id:'1',title:'牛奶',sub:'2 瓶',group:'冷藏'},{id:'2',title:'面包',group:'冷藏'}],
        [{label:'全带走',kind:'ok',onClick:function(ids){window.__ids = ids;}}]
      );
    """)
    page.wait_for_timeout(100)
    row = page.evaluate("document.querySelector('.sl-group-items .sl-item').outerHTML")
    assert row == ('<label class="sl-item"><input type="checkbox" data-id="1" data-g="冷藏">'
                   '<span class="sl-item-body"><span class="sl-item-title">牛奶</span>'
                   '<span class="sl-item-sub">2 瓶</span></span></label>')
    assert page.evaluate("document.querySelectorAll('.sl-widget').length") == 0
    page.check('.sl-item input[data-id="1"]')
    page.click('[data-batch="全带走"]')
    page.wait_for_timeout(50)
    assert page.evaluate('window.__ids') == ['1']  # 第一参照旧


def test_select_list_widget_esc_anti_xss(page):
    """行内控件 label/placeholder/option value+label 一律 esc, 零注入面（#327）"""
    page.evaluate("""
      document.getElementById('root').innerHTML = window.selectList(
        [{id:'a',title:'x',
          widget:{type:'select',key:'cat',label:'<img src=x onerror=alert(1)>',
                  placeholder:'<script>1</script>',
                  options:[{value:'<img src=x onerror=alert(1)>',label:'<script>alert(2)</script>'}]}},
         {id:'b',title:'y',widget:{type:'text',key:'q',placeholder:'<img src=x onerror=alert(3)>'}}]
      );
    """)
    page.wait_for_timeout(100)
    img = page.evaluate("document.querySelector('.sl img') !== null")
    script = page.evaluate("document.querySelector('.sl script') !== null")
    raw = page.evaluate("document.getElementById('root').innerHTML")
    assert img is False and script is False
    assert '&lt;img' in raw and '&lt;script' in raw and '<img src' not in raw


def test_select_list_widget_invalid_type_degrades_text(page):
    """非法 widget.type 降级 text（宽容渲染, 不报错）; key 缺省 'w'+行号"""
    page.evaluate("""
      window.__sub = null;
      document.getElementById('root').innerHTML = window.selectList(
        [{id:'a',title:'x',widget:{type:'color',key:'c'}}],
        [{label:'确认',kind:'ok',onClick:function(){}}],
        {onSubmit:function(ids, values){window.__sub = values;}}
      );
    """)
    page.wait_for_timeout(100)
    typ = page.evaluate("document.querySelector('.sl-widget-input').type")
    assert typ == 'text'
    page.check('.sl-item input[data-id="a"]')
    page.fill('label.sl-item:has(input[data-id="a"]) .sl-widget-input', '7')
    page.click('[data-batch="确认"]')
    page.wait_for_timeout(50)
    assert page.evaluate('window.__sub') == {'a': {'c': '7'}}


def test_select_list_on_submit_requires_checked(page):
    """无勾选点击批量 → 提示 toast, onSubmit 不触发（与既有拦截一致）"""
    _clear_toasts(page)
    page.evaluate("""
      window.__sub = 0;
      document.getElementById('root').innerHTML = window.selectList(
        [{id:'a',title:'x',widget:{type:'text',key:'qty'}}],
        [{label:'确认',kind:'ok',onClick:function(){}}],
        {onSubmit:function(){window.__sub = 1;}}
      );
    """)
    page.wait_for_timeout(100)
    page.click('[data-batch="确认"]')
    page.wait_for_timeout(80)
    assert page.evaluate('window.__sub') == 0
    title = page.evaluate("document.querySelector('.hm-toast .hm-toast-title')?.textContent")
    assert title == '请先勾选'


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
      window.__savedEsc = window.esc;
      window.emptyState = undefined; window.esc = undefined;
      delete window.__chartsLoaded; delete window.charts;
    """)
    chart_page.evaluate(CHARTS_JS)
    chart_page.evaluate("window.charts.bar(document.getElementById('root'), [])")
    text = chart_page.evaluate("document.querySelector('.hm-c-empty')?.textContent")
    assert text == '📊 暂无数据'
    # 测试卫生: 恢复被清空的全局 esc（chart_page 与 page 同浏览器上下文, 防污染后续用例, #312 追加）
    chart_page.evaluate("window.esc = window.__savedEsc; delete window.__savedEsc;")


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


def test_charts_donut_thick_ring_not_clipped(chart_page):
    """donut ringWidth > 16 圆环不被 svg 视口裁切（回归 #317 验收: 固定 r=52 时 ringWidth 26 外缘超 viewBox 呈"方框圆环"）"""
    chart_page.evaluate("""
      window.charts.donut(document.getElementById('root'),
        [{label:'A',value:60},{label:'B',value:40}],
        {size:220, ringWidth:26, legend:'none', animation:false});
    """)
    clip = chart_page.evaluate("""
      (() => {
        const svg = document.querySelector('.hm-c-donut svg');
        const r = svg.getBoundingClientRect();
        const c = svg.querySelector('circle[stroke-dashoffset]');
        const outer = (parseFloat(c.getAttribute('r')) + parseFloat(c.getAttribute('stroke-width')) / 2) * (r.width / 120);
        return { outerPx: outer, halfPx: r.width / 2 };
      })()
    """)
    assert clip['outerPx'] < clip['halfPx'], f'圆环外缘({clip["outerPx"]:.1f}px)超出视口半宽({clip["halfPx"]:.1f}px)被裁切'


def test_charts_line_xlabels_not_overflow_wrap(chart_page):
    """line x 轴标签行不溢出 wrap 底部（回归 #317 验收: svg height:100% + x 标签行在 wrap 外 → 与下方内容重叠）"""
    chart_page.evaluate("""
      document.getElementById('root').innerHTML = '<div style="height:300px"></div>';
      window.charts.line(document.getElementById('root'),
        [{label:'周一',value:2},{label:'周二',value:5},{label:'周三',value:3},{label:'周四',value:4}],
        {height:220, labels:'all', animation:false});
    """)
    overflow = chart_page.evaluate("""
      (() => {
        const wrap = document.querySelector('.hm-c-line-wrap');
        const xl = wrap.querySelector('.hm-c-line-x');
        const wr = wrap.getBoundingClientRect();
        const xr = xl.getBoundingClientRect();
        return { xlBottom: xr.bottom, wrapBottom: wr.bottom };
      })()
    """)
    assert overflow['xlBottom'] <= overflow['wrapBottom'] + 1, \
        f'x 标签底部({overflow["xlBottom"]:.1f})超出 wrap 底部({overflow["wrapBottom"]:.1f})'


def test_charts_donut_center_text_can_be_empty(chart_page):
    """donut 中心文字可显式关闭（centerLabel/centerValue 传空串 → 不渲染 svg text; #317 验收: 技能用 HTML 覆盖层显示中心）"""
    chart_page.evaluate("""
      window.charts.donut(document.getElementById('root'),
        [{label:'完成度',value:100}],
        {centerLabel:'', centerValue:'', animation:false});
    """)
    texts = chart_page.evaluate("[...document.querySelectorAll('.hm-c-donut svg text')].map(t => t.textContent)")
    assert texts == [], f'中心文字未关闭: {texts}'


def test_charts_line_animation_clears_dasharray(chart_page):
    """line 动画结束后 stroke-dasharray 必须清空（回归 #317 验收: style 内 dasharray 按屏幕像素解释,
    preserveAspectRatio=none 拉伸后与路径实长不符 → 中段断线; 过渡完须清除恢复实线）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'),
        [{label:'周一',value:2},{label:'周二',value:5},{label:'周三',value:3},{label:'周四',value:4},{label:'周五',value:6}],
        {height:220, animation:true});
    """)
    # 动画 1s, 等待 1.5s 后 dasharray 应为 none
    chart_page.wait_for_timeout(1500)
    dash = chart_page.evaluate("getComputedStyle(document.querySelector('.hm-c-line-svg path[fill=\\'none\\']')).strokeDasharray")
    assert dash in ('none', 'initial', ''), f'动画后 dasharray 未清除: {dash}'


def test_charts_line_animation_off_no_dash(chart_page):
    """line animation:false 时不应设置 dasharray（无动画路径直接实线）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'),
        [{label:'A',value:1},{label:'B',value:3}],
        {animation:false});
    """)
    dash = chart_page.evaluate("getComputedStyle(document.querySelector('.hm-c-line-svg path[fill=\\'none\\']')).strokeDasharray")
    assert dash in ('none', 'initial', ''), f'animation:false 不应有 dasharray: {dash}'


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


def test_line_markline_label_html_not_stretched(chart_page):
    """markLine 标签为 HTML 覆盖层（不在 SVG 内）: preserveAspectRatio=none 拉伸不作用于文字（v1.16 · #333 验收修复）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, markLine:{value:7,label:"目标 7"}})', LINE_ITEMS)
    in_svg = chart_page.evaluate("document.querySelector('.hm-c-line-svg svg .hm-c-markline-t') !== null")
    tag = chart_page.evaluate("document.querySelector('.hm-c-markline-t').tagName")
    fs = chart_page.evaluate("getComputedStyle(document.querySelector('.hm-c-markline-t')).fontSize")
    assert not in_svg and tag == 'I' and fs == '10px'


def test_line_markline_label_on_top(chart_page):
    """markLine 标签最后插入（在 area/线/刻度之上）: 不被路径遮挡（v1.16 · #333 验收发现）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, markLine:{value:7,label:"目标 7"}, area:true})', LINE_ITEMS)
    last = chart_page.evaluate("document.querySelector('.hm-c-line-svg').lastElementChild.className")
    assert 'hm-c-markline-t' in last


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

# ── line: connectNulls 缺失值连线（v1.14 · #356）────────────────

def test_line_connect_nulls_connects(chart_page):
    """connectNulls:true: 跨 null 连线（单段 M）、缺值日无 dot"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), "
        "[{label:'d1',value:62.7},{label:'d2',value:null},{label:'d3',value:64.2},"
        "{label:'d4',value:null},{label:'d5',value:63.5}], "
        "{animation:false, connectNulls:true})")
    path_d = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    assert path_d == 'M14.0 91.6L160.0 18.4L306.0 52.6'  # 跨两个 null 直连（点位置与断线模式一致）
    dots = chart_page.evaluate("document.querySelectorAll('.hm-c-dot').length")
    assert dots == 3  # 缺值日不画点


def test_line_connect_nulls_false_byte_identical(chart_page):
    """connectNulls 未传/false: 断线行为与默认逐字节一致（回归）"""
    items = "[{label:'a',value:1},{label:'b',value:null},{label:'c',value:3}]"
    chart_page.evaluate("window.charts.line(document.getElementById('root'), " + items + ", {animation:false})")
    d_default = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    chart_page.evaluate("window.charts.line(document.getElementById('root'), " + items + ", {animation:false, connectNulls:false})")
    d_false = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    assert d_false == d_default
    assert d_default.count('M') == 2  # 既有断线语义保持


def test_line_connect_nulls_edges_not_extended(chart_page):
    """首尾 null 不向图外延伸: 路径从首个有效点起、到最后一个有效点止"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), "
        "[{label:'a',value:null},{label:'b',value:1},{label:'c',value:2},{label:'d',value:null}], "
        "{animation:false, connectNulls:true})")
    path_d = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    assert path_d == 'M111.3 91.6L208.7 18.4'


def test_line_connect_nulls_all_null_empty(chart_page):
    """全 null 系列 + connectNulls:true: 仍空路径, 无 dot, 不报错"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), "
        "[{label:'a',value:null},{label:'b',value:null}], {animation:false, connectNulls:true})")
    path_d = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    dots = chart_page.evaluate("document.querySelectorAll('.hm-c-dot').length")
    assert path_d == '' and dots == 0


def test_line_connect_nulls_smooth(chart_page):
    """smooth + connectNulls:true: 曲线跨 null 单段连续（不切段）"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), "
        "[{label:'a',value:1},{label:'b',value:null},{label:'c',value:3},{label:'d',value:null},{label:'e',value:5}], "
        "{animation:false, connectNulls:true, smooth:true})")
    path_d = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    assert path_d.count('M') == 1 and 'C' in path_d


def test_line_connect_nulls_step(chart_page):
    """step + connectNulls:true: 阶梯线跨 null 连续"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), "
        "[{label:'a',value:1},{label:'b',value:null},{label:'c',value:3}], "
        "{animation:false, connectNulls:true, step:true})")
    path_d = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    assert path_d.count('M') == 1 and 'L' in path_d


def test_line_connect_nulls_area(chart_page):
    """area + connectNulls:true: 面积跨 null 连续填充（单段 M + Z 闭合）; 默认面积断两段"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), "
        "[{label:'a',value:1},{label:'b',value:null},{label:'c',value:3}], "
        "{animation:false, connectNulls:true, area:true})")
    area_d = chart_page.evaluate("document.querySelector('.hm-c-line-svg path[fill]').getAttribute('d')")
    assert area_d.count('M') == 1 and area_d.endswith('Z')
    chart_page.evaluate("window.charts.line(document.getElementById('root'), "
        "[{label:'a',value:1},{label:'b',value:null},{label:'c',value:3}], "
        "{animation:false, area:true})")
    area_d2 = chart_page.evaluate("document.querySelector('.hm-c-line-svg path[fill]').getAttribute('d')")
    assert area_d2.count('M') == 2


def test_line_connect_nulls_avgline(chart_page):
    """avgLine + connectNulls:true: 均线跨 null 连线（显式断言）; 默认均线断段"""
    items = "[{label:'a',value:10},{label:'b',value:null},{label:'c',value:null},{label:'d',value:null},{label:'e',value:30}]"
    chart_page.evaluate("window.charts.line(document.getElementById('root'), " + items + ", {animation:false, connectNulls:true, avgLine:3})")
    avg_d = chart_page.evaluate('document.querySelectorAll(".hm-c-line-svg path[fill=\'none\']")[1].getAttribute(\'d\')')
    assert avg_d.count('M') == 1  # 均线跨 null 连线
    chart_page.evaluate("window.charts.line(document.getElementById('root'), " + items + ", {animation:false, avgLine:3})")
    avg_d2 = chart_page.evaluate('document.querySelectorAll(".hm-c-line-svg path[fill=\'none\']")[1].getAttribute(\'d\')')
    assert avg_d2.count('M') == 2  # 默认均线断段


def test_line_connect_nulls_series(chart_page):
    """series 多序列 + connectNulls:true: 每序列独立跨 null 连线"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), [{label:'a',value:1}], "
        "{animation:false, connectNulls:true, "
        "series:[{name:'A',items:[{label:'a',value:1},{label:'b',value:null},{label:'c',value:3}]},"
        "{name:'B',items:[{label:'a',value:2},{label:'b',value:4},{label:'c',value:null}]}]})")
    ds = chart_page.evaluate('[...document.querySelectorAll(".hm-c-line-svg path[fill=\'none\']")].map(p => p.getAttribute(\'d\'))')
    assert len(ds) == 2 and all(d.count('M') == 1 for d in ds)


# ── line: yTicks 轴刻度文字（v1.15 · #333）────────────────

def test_line_yticks_renders_four(chart_page):
    """yTicks:4: DOM 出现 4 条刻度短线 + 4 个刻度文字, 值 = 共享 Y 域(含 padding)均分"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, yTicks:4})', LINE_ITEMS)
    lines = chart_page.evaluate("document.querySelectorAll('.hm-c-yt-l').length")
    labels = chart_page.evaluate("[...document.querySelectorAll('.hm-c-yt')].map(n=>n.textContent)")
    assert lines == 4
    # LINE_ITEMS min=2 max=8 range=6 pad=0.36 → 域 [1.64, 8.36] 均分 4 段
    assert labels == ['1.64', '3.88', '6.12', '8.36']


def test_line_yticks_positions_inside(chart_page):
    """贴边防裁剪: 最上/最下刻度文字均落在 svg 区上下界内（不裁剪不重叠）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, yTicks:4})', LINE_ITEMS)
    pos = chart_page.evaluate("""() => {
      const svg = document.querySelector('.hm-c-line-svg').getBoundingClientRect();
      const ys = [...document.querySelectorAll('.hm-c-yt')].map(n => n.getBoundingClientRect());
      return {top: ys[0].top - svg.top, bottom: ys[ys.length-1].bottom - svg.top, h: svg.height};
    }""")
    assert pos['top'] >= 0 and pos['bottom'] <= pos['h']


def test_line_yticks_default_and_false_absent(chart_page):
    """缺省/false: 无任何刻度元素（既有渲染逐字节不变）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false})', LINE_ITEMS)
    n1 = chart_page.evaluate("document.querySelectorAll('.hm-c-yt,.hm-c-yt-l').length")
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, yTicks:false})', LINE_ITEMS)
    n2 = chart_page.evaluate("document.querySelectorAll('.hm-c-yt,.hm-c-yt-l').length")
    assert n1 == 0 and n2 == 0


def test_line_yticks_byte_identical(chart_page):
    """yTicks 未传 vs false: 整段 innerHTML 逐字节一致（回归断言）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false})', LINE_ITEMS)
    html1 = chart_page.evaluate("document.getElementById('root').innerHTML")
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, yTicks:false})', LINE_ITEMS)
    html2 = chart_page.evaluate("document.getElementById('root').innerHTML")
    assert html1 == html2


def test_line_yticks_format(chart_page):
    """刻度文字走 format（与 tooltip 同一格式化器）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, yTicks:4, format:"¥{v}"})', LINE_ITEMS)
    labels = chart_page.evaluate("[...document.querySelectorAll('.hm-c-yt')].map(n=>n.textContent)")
    assert labels[0] == '¥1.64' and all(l.startswith('¥') for l in labels)


def test_line_yticks_clamped(chart_page):
    """刻度数收敛 2-6: 1→2, 20→6; 非数字字符串/0 → 关闭"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, yTicks:1})', LINE_ITEMS)
    n1 = chart_page.evaluate("document.querySelectorAll('.hm-c-yt').length")
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, yTicks:20})', LINE_ITEMS)
    n2 = chart_page.evaluate("document.querySelectorAll('.hm-c-yt').length")
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, yTicks:"4"})', LINE_ITEMS)
    n3 = chart_page.evaluate("document.querySelectorAll('.hm-c-yt').length")
    assert n1 == 2 and n2 == 6 and n3 == 0


def test_line_yticks_extremes(chart_page):
    """极端值: 全 0 / 全相同值 → 正常渲染 4 刻度不报错"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), [{label:'a',value:0},{label:'b',value:0},{label:'c',value:0}], {animation:false, yTicks:4})")
    n1 = chart_page.evaluate("document.querySelectorAll('.hm-c-yt').length")
    chart_page.evaluate("window.charts.line(document.getElementById('root'), [{label:'a',value:5},{label:'b',value:5},{label:'c',value:5}], {animation:false, yTicks:4})")
    n2 = chart_page.evaluate("document.querySelectorAll('.hm-c-yt').length")
    assert n1 == 4 and n2 == 4


def test_line_yticks_series_shared_domain(chart_page):
    """series 多序列: 刻度 = 共享 Y 域（所有序列并入同一域均分）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'a',value:150}], {animation:false, yTicks:4,
        series:[{name:'A',items:[{label:'a',value:10},{label:'b',value:20}]},
                {name:'B',items:[{label:'a',value:100},{label:'b',value:200}]}]})
    """)
    labels = chart_page.evaluate("[...document.querySelectorAll('.hm-c-yt')].map(n=>n.textContent)")
    assert len(labels) == 4
    # 全域 min=10 max=200 range=190 pad=11.4 → [-1.4, 211.4] 均分 4: -1.4/69.53/140.47/211.4
    assert labels == ['-1.4', '69.53', '140.47', '211.4']


def test_line_yticks_grid_off_still_marks(chart_page):
    """grid:false + yTicks:4: 仍画 4 条刻度短线 + 4 文字（刻度独立于网格）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, grid:false, yTicks:4})', LINE_ITEMS)
    lines = chart_page.evaluate("document.querySelectorAll('.hm-c-yt-l').length")
    labels = chart_page.evaluate("document.querySelectorAll('.hm-c-yt').length")
    assert lines == 4 and labels == 4


# ── line: series[].ownScale 独立刻度（v1.17 · #334）────────────────

def test_line_ownscale_fills_height(chart_page):
    """ownScale:true: 每系列独立归一化各自铺满图高（量级差 100 倍不压平）; 缺省共享域小量级被压扁"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'x',value:50}], {animation:false,
        series:[{name:'A',items:[{label:'a',value:10},{label:'b',value:20}]},
                {name:'B',items:[{label:'a',value:100},{label:'b',value:110}]}]})
    """)
    ds_shared = chart_page.evaluate('[...document.querySelectorAll(".hm-c-line-svg path[fill=\'none\']")].map(p => p.getAttribute(\'d\'))')
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'x',value:50}], {animation:false,
        series:[{name:'A',items:[{label:'a',value:10},{label:'b',value:20}],ownScale:true},
                {name:'B',items:[{label:'a',value:100},{label:'b',value:110}],ownScale:true}]})
    """)
    ds_own = chart_page.evaluate('[...document.querySelectorAll(".hm-c-line-svg path[fill=\'none\']")].map(p => p.getAttribute(\'d\'))')
    # 共享域: 全域 [4, 116] → A 压缩贴底(91.6/84.3), B 压平贴顶(25.7/18.4)
    assert ds_shared == ['M14.0 91.6L306.0 84.3', 'M14.0 25.7L306.0 18.4']
    # ownScale: 各自域 [9.4,20.6]/[99.4,110.6] → 两系列同样铺满图高(91.6 → 18.4)
    assert ds_own == ['M14.0 91.6L306.0 18.4', 'M14.0 91.6L306.0 18.4']


def test_line_ownscale_does_not_pollute_axis(chart_page):
    """ownScale 序列不参与共享域: yTicks/网格仍以主序列域为准（极端量级序列不污染主轴刻度）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'x',value:5}], {animation:false, yTicks:4,
        series:[{name:'A',items:[{label:'a',value:2},{label:'b',value:5},{label:'c',value:8}]},
                {name:'B',items:[{label:'a',value:0},{label:'b',value:5000},{label:'c',value:10000}],ownScale:true}]})
    """)
    labels = chart_page.evaluate("[...document.querySelectorAll('.hm-c-yt')].map(n=>n.textContent)")
    assert labels == ['1.64', '3.88', '6.12', '8.36']  # 仅 A 的域 [1.64, 8.36]


def test_line_ownscale_legend_note(chart_page):
    """ownScale + legend:true: 图例注明「各指标独立刻度」; 缺省无此注记"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'x',value:50}], {animation:false, legend:true,
        series:[{name:'A',items:[{label:'a',value:10},{label:'b',value:20}],ownScale:true},
                {name:'B',items:[{label:'a',value:100},{label:'b',value:110}],ownScale:true}]})
    """)
    lg1 = chart_page.evaluate("[...document.querySelectorAll('.hm-c-lg')].map(n=>n.textContent)")
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'x',value:50}], {animation:false, legend:true,
        series:[{name:'A',items:[{label:'a',value:10},{label:'b',value:20}]},
                {name:'B',items:[{label:'a',value:100},{label:'b',value:110}]}]})
    """)
    lg2 = chart_page.evaluate("[...document.querySelectorAll('.hm-c-lg')].map(n=>n.textContent)")
    assert '各指标独立刻度' in lg1 and lg1 == ['A', 'B', '各指标独立刻度']
    assert lg2 == ['A', 'B'] and '各指标独立刻度' not in lg2


def test_line_ownscale_single_series_noop(chart_page):
    """单序列 ownScale:true: 与单序列共享域渲染一致（单系列本就按自身域铺满, 无行为差异）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, series:[{name:"A",items:items}]})', LINE_ITEMS)
    d1 = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, series:[{name:"A",items:items,ownScale:true}]})', LINE_ITEMS)
    d2 = chart_page.evaluate('document.querySelector(".hm-c-line-svg path[fill=\'none\']").getAttribute(\'d\')')
    assert d1 == d2


# ── line: markPoint 峰谷点标注（v1.18 · #319）────────────────

def test_line_markpoint_default_max(chart_page):
    """markPoint:true: 主序列最大值点出现高亮标记 + 文字标注（值走 format）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, markPoint:true, format:"¥{v}"})', LINE_ITEMS)
    dots = chart_page.evaluate("document.querySelectorAll('.hm-c-mp').length")
    lbl = chart_page.evaluate("document.querySelector('.hm-c-mp-t')?.textContent")
    assert dots == 1 and lbl == '¥8'  # LINE_ITEMS 最大值 8（index 3）


def test_line_markpoint_index_override(chart_page):
    """markPoint:{index}: 指定点标注 + 自定义 label"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), [{label:'a',value:1},{label:'b',value:5},{label:'c',value:3}], {animation:false, markPoint:{index:1,label:'峰值'}})")
    lbl = chart_page.evaluate("document.querySelector('.hm-c-mp-t')?.textContent")
    assert lbl == '峰值'


def test_line_markpoint_value_match(chart_page):
    """markPoint:{value}: 按值匹配首个点"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), [{label:'a',value:3},{label:'b',value:5},{label:'c',value:5}], {animation:false, markPoint:{value:5}})")
    mp = chart_page.evaluate("document.querySelector('.hm-c-mp')?.getBoundingClientRect()")
    dot1 = chart_page.evaluate("[...document.querySelectorAll('.hm-c-dot')].map(n=>(n.getBoundingClientRect().x + n.getBoundingClientRect().width/2))")
    assert mp is not None and abs((mp['x'] + mp['width']/2) - dot1[1]) < 2  # 与第 2 个数据点中心对齐（首个 value=5）


def test_line_markpoint_edge_not_clipped(chart_page):
    """贴边防裁剪: index 0（最左）长标注不超出容器左边界"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), [{label:'a',value:9},{label:'b',value:1},{label:'c',value:2}], {animation:false, markPoint:{index:0,label:'很长很长很长的标注文字'}})")
    box = chart_page.evaluate("""() => {
      const svg=document.querySelector('.hm-c-line-svg').getBoundingClientRect();
      const l=document.querySelector('.hm-c-mp-t').getBoundingClientRect();
      return {l: l.left-svg.left, r: l.right-svg.left, w: svg.width};
    }""")
    assert box['l'] >= 0 and box['r'] <= box['w']


def test_line_markpoint_default_absent_byte_identical(chart_page):
    """缺省: 无 .hm-c-mp 元素; markPoint:false 与未传渲染逐字节一致"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false})', LINE_ITEMS)
    n1 = chart_page.evaluate("document.querySelectorAll('.hm-c-mp,.hm-c-mp-t').length")
    html1 = chart_page.evaluate("document.getElementById('root').innerHTML")
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, markPoint:false})', LINE_ITEMS)
    n2 = chart_page.evaluate("document.querySelectorAll('.hm-c-mp,.hm-c-mp-t').length")
    html2 = chart_page.evaluate("document.getElementById('root').innerHTML")
    assert n1 == 0 and n2 == 0 and html1 == html2


def test_line_markpoint_series_main_series(chart_page):
    """series 场景: 标注作用于主序列（series[0]）最大值点, 不取其他序列更大值"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'x',value:1}], {animation:false, markPoint:true,
        series:[{name:'A',items:[{label:'a',value:2},{label:'b',value:9},{label:'c',value:4}]},
                {name:'B',items:[{label:'a',value:50},{label:'b',value:60},{label:'c',value:70}]}]})
    """)
    mp = chart_page.evaluate("document.querySelector('.hm-c-mp')?.getBoundingClientRect()")
    dots = chart_page.evaluate("[...document.querySelectorAll('.hm-c-dot')].map(n=>(n.getBoundingClientRect().x + n.getBoundingClientRect().width/2))")
    assert mp is not None and abs((mp['x'] + mp['width']/2) - dots[1]) < 2  # B 值更大但标注在 A 序列 max(9) 点中心


# ── line: band 置信带（v1.19 · #335）────────────────

def test_line_band_renders(chart_page):
    """band:{hi,lo}: DOM 出现 .hm-c-band 面积路径（半透明 0.15）, 覆盖 hi/lo 区间"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'),
        [{label:'a',value:5},{label:'b',value:6},{label:'c',value:4}],
        {animation:false, band:{hi:[7,8,6], lo:[3,4,2]}})
    """)
    band = chart_page.evaluate("document.querySelector('.hm-c-band')?.getAttribute('d')")
    opacity = chart_page.evaluate("document.querySelector('.hm-c-band')?.getAttribute('opacity')")
    assert band and band.startswith('M') and band.endswith('Z') and opacity == '0.15'


def test_line_band_default_absent_byte_identical(chart_page):
    """缺省: 无 .hm-c-band 元素; band:null 与未传渲染逐字节一致"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false})', LINE_ITEMS)
    n1 = chart_page.evaluate("document.querySelectorAll('.hm-c-band').length")
    html1 = chart_page.evaluate("document.getElementById('root').innerHTML")
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, band:null})', LINE_ITEMS)
    n2 = chart_page.evaluate("document.querySelectorAll('.hm-c-band').length")
    html2 = chart_page.evaluate("document.getElementById('root').innerHTML")
    assert n1 == 0 and n2 == 0 and html1 == html2


def test_line_band_null_breaks_segments(chart_page):
    """hi/lo 含 null 断点: 该段断开（两个独立封闭区）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'),
        [{label:'a',value:5},{label:'b',value:6},{label:'c',value:4},{label:'d',value:5}],
        {animation:false, band:{hi:[7,8,null,7], lo:[3,4,null,3]}})
    """)
    d = chart_page.evaluate("document.querySelector('.hm-c-band')?.getAttribute('d')")
    segs = d.count('M')
    assert segs == 2


def test_line_band_length_mismatch_throws(chart_page):
    """band.hi/lo 长度与 items 不等 → 直接报错"""
    err = chart_page.evaluate("""() => { try {
      window.charts.line(document.getElementById('root'),
        [{label:'a',value:5},{label:'b',value:6}],
        {animation:false, band:{hi:[7,8,9], lo:[3,4,5]}});
      return ''; } catch(e) { return e.message; } }""")
    assert 'band.hi/lo 长度必须与 items 等长' in err


def test_line_band_expands_domain(chart_page):
    """band 值并入共享域: hi 超出主线最大值 → yTicks 顶刻度随之扩展（不裁剪）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'),
        [{label:'a',value:2},{label:'b',value:8}],
        {animation:false, yTicks:4, band:{hi:[10,10], lo:[0,0]}})
    """)
    labels = chart_page.evaluate("[...document.querySelectorAll('.hm-c-yt')].map(n=>n.textContent)")
    # 域 min=0 max=10 range=10 pad=0.6 → [−0.6, 10.6], 顶刻度 10.6
    assert labels[-1] == '10.6'


def test_line_band_under_line(chart_page):
    """绘制顺序: band 在折线路径之前（区间不遮挡主线）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'),
        [{label:'a',value:5},{label:'b',value:6},{label:'c',value:4}],
        {animation:false, band:{hi:[7,8,6], lo:[3,4,2]}})
    """)
    order = chart_page.evaluate("""() => {
      const svg = document.querySelector('.hm-c-line-svg svg');
      const kids = [...svg.children];
      return kids.indexOf(svg.querySelector('.hm-c-band')) < kids.indexOf(svg.querySelector('path[fill="none"]'));
    }""")
    assert order


# ── line: markLine 竖线 xValue（v1.20 · #340）────────────────

def test_line_markline_xvalue_index(chart_page):
    """markLine:{xValue: 索引}: 竖线元素（x1==x2）+ 顶部标注"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, markLine:{xValue:3,label:"里程碑"}})', LINE_ITEMS)
    vline = chart_page.evaluate("document.querySelector('.hm-c-markline-v')")
    lbl = chart_page.evaluate("document.querySelector('.hm-c-markline-t')?.textContent")
    assert vline is not None and lbl == '里程碑'
    x1 = chart_page.evaluate("document.querySelector('.hm-c-markline-v')?.getAttribute('x1')")
    x2 = chart_page.evaluate("document.querySelector('.hm-c-markline-v')?.getAttribute('x2')")
    assert x1 == x2  # 竖线


def test_line_markline_xvalue_label_match(chart_page):
    """markLine:{xValue: label}: 按 items label 匹配; 缺省标注文字 = 该点 label"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), [{label:'一月',value:3},{label:'二月',value:6},{label:'三月',value:4}], {animation:false, markLine:{xValue:'二月'}})")
    lbl = chart_page.evaluate("document.querySelector('.hm-c-markline-t')?.textContent")
    assert lbl == '二月'


def test_line_markline_xvalue_out_of_range_ignored(chart_page):
    """xValue 越界索引: 忽略不报错, 无竖线元素"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, markLine:{xValue:99}})', LINE_ITEMS)
    n = chart_page.evaluate("document.querySelectorAll('.hm-c-markline-v').length")
    assert n == 0


def test_line_markline_horizontal_unchanged(chart_page):
    """既有 {value} 水平阈值线行为不变: 横线 + 右侧标注; 无竖线"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, markLine:{value:5,label:"目标"}})', LINE_ITEMS)
    vn = chart_page.evaluate("document.querySelectorAll('.hm-c-markline-v').length")
    x1 = chart_page.evaluate("document.querySelector('.hm-c-line-svg line:not(.hm-c-markline-v):not(.hm-c-yt-l)')?.getAttribute('x1')")
    x2 = chart_page.evaluate("document.querySelector('.hm-c-line-svg line:not(.hm-c-markline-v):not(.hm-c-yt-l)')?.getAttribute('x2')")
    lbl = chart_page.evaluate("document.querySelector('.hm-c-markline-t')?.textContent")
    assert vn == 0 and x1 == '14' and x2 == '306' and lbl == '目标'


def test_line_markline_both_horizontal_vertical(chart_page):
    """value + xValue 同传: 横线 + 竖线同时渲染"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, markLine:{value:5, xValue:1}})', LINE_ITEMS)
    vn = chart_page.evaluate("document.querySelectorAll('.hm-c-markline-v').length")
    lines = chart_page.evaluate("document.querySelectorAll('.hm-c-line-svg line').length")
    assert vn == 1 and lines >= 2  # 竖线 + 横线（另有网格线）


def test_line_markline_xvalue_edge_not_clipped(chart_page):
    """xValue 0（最左）: 标注不超出容器左边界"""
    chart_page.evaluate("window.charts.line(document.getElementById('root'), [{label:'一月',value:9},{label:'二月',value:1},{label:'三月',value:2}], {animation:false, markLine:{xValue:0,label:'很长很长很长的标注文字'}})")
    box = chart_page.evaluate("""() => {
      const svg=document.querySelector('.hm-c-line-svg').getBoundingClientRect();
      const l=document.querySelector('.hm-c-markline-t').getBoundingClientRect();
      return {l: l.left-svg.left, r: l.right-svg.left, w: svg.width};
    }""")
    assert box['l'] >= 0 and box['r'] <= box['w']


# ── line: fillBetween 线间填充（v1.21 · #338）────────────────

def test_line_fillbetween_renders(chart_page):
    """fillBetween:{a,b}: 两系列之间出现填充 path（透明度 = areaOpacity）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'x',value:1}], {animation:false,
        series:[{name:'摄入',items:[{label:'a',value:10},{label:'b',value:20},{label:'c',value:15}]},
                {name:'消耗',items:[{label:'a',value:25},{label:'b',value:30},{label:'c',value:28}]}],
        fillBetween:{a:0,b:1}})
    """)
    fb = chart_page.evaluate("document.querySelector('.hm-c-fillbetween')?.getAttribute('d')")
    opacity = chart_page.evaluate("document.querySelector('.hm-c-fillbetween')?.getAttribute('opacity')")
    assert fb and fb.startswith('M') and fb.endswith('Z') and opacity == '0.12'


def test_line_fillbetween_default_absent_byte_identical(chart_page):
    """缺省: 无 .hm-c-fillbetween 元素; fillBetween:null 与未传渲染逐字节一致"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false})', LINE_ITEMS)
    n1 = chart_page.evaluate("document.querySelectorAll('.hm-c-fillbetween').length")
    html1 = chart_page.evaluate("document.getElementById('root').innerHTML")
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, fillBetween:null})', LINE_ITEMS)
    n2 = chart_page.evaluate("document.querySelectorAll('.hm-c-fillbetween').length")
    html2 = chart_page.evaluate("document.getElementById('root').innerHTML")
    assert n1 == 0 and n2 == 0 and html1 == html2


def test_line_fillbetween_null_breaks(chart_page):
    """任一侧 null 断点: 该段断开不填充（两个独立封闭区）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'x',value:1}], {animation:false,
        series:[{name:'A',items:[{label:'a',value:10},{label:'b',value:20},{label:'c',value:15},{label:'d',value:12}]},
                {name:'B',items:[{label:'a',value:25},{label:'b',value:null},{label:'c',value:28},{label:'d',value:26}]}],
        fillBetween:{a:0,b:1}})
    """)
    d = chart_page.evaluate("document.querySelector('.hm-c-fillbetween')?.getAttribute('d')")
    assert d.count('M') == 2


def test_line_fillbetween_out_of_range_throws(chart_page):
    """a/b 越界 → 直接报错"""
    err = chart_page.evaluate("""() => { try {
      window.charts.line(document.getElementById('root'), [{label:'x',value:1}], {animation:false,
        series:[{name:'A',items:[{label:'a',value:1}]},{name:'B',items:[{label:'a',value:2}]}],
        fillBetween:{a:0,b:5}});
      return ''; } catch(e) { return e.message; } }""")
    assert 'fillBetween.a/b 越界' in err


def test_line_fillbetween_single_series_throws(chart_page):
    """无 series（单序列）: b=1 越界 → 报错（fillBetween 需要两系列）"""
    err = chart_page.evaluate('(items) => { try { window.charts.line(document.getElementById("root"), items, {animation:false, fillBetween:{a:0,b:1}}); return ""; } catch(e) { return e.message; } }', LINE_ITEMS)
    assert 'fillBetween.a/b 越界' in err


def test_line_fillbetween_color_override(chart_page):
    """fillBetween.color 覆盖填充色"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'x',value:1}], {animation:false,
        series:[{name:'A',items:[{label:'a',value:10},{label:'b',value:20}]},
                {name:'B',items:[{label:'a',value:25},{label:'b',value:30}]}],
        fillBetween:{a:0,b:1,color:'#ff9500'}})
    """)
    fill = chart_page.evaluate("document.querySelector('.hm-c-fillbetween')?.getAttribute('fill')")
    assert fill == '#ff9500'


# ── line: 小缺口（v1.22 · #341）异常点/拐点圈选/首尾标签避让 ──

def test_line_anomaly_dot_red(chart_page):
    """items 每点 anomaly:true → 该点数据点染警示红; 正常点不变"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'),
        [{label:'a',value:3,anomaly:true},{label:'b',value:5},{label:'c',value:4}],
        {animation:false})
    """)
    styles = chart_page.evaluate("[...document.querySelectorAll('.hm-c-dot')].map(n=>n.getAttribute('style'))")
    assert 'ff3b30' in styles[0] and 'ff3b30' not in styles[1]


def test_line_anomaly_default_absent(chart_page):
    """缺省: 无 anomaly 染红; 渲染与未传 anomaly 时一致（无 .hm-c-dot-anomaly）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false})', LINE_ITEMS)
    n = chart_page.evaluate("document.querySelectorAll('.hm-c-dot-anomaly').length")
    assert n == 0


def test_line_highlight_turns(chart_page):
    """highlightPoints:'turns': 方向变化点出现圈选环（[2,5,3,8,6] → 拐点 index 1,2,3 共 3 个）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'),
        [{label:'a',value:2},{label:'b',value:5},{label:'c',value:3},{label:'d',value:8},{label:'e',value:6}],
        {animation:false, highlightPoints:'turns'})
    """)
    rings = chart_page.evaluate("[...document.querySelectorAll('.hm-c-dot-hl')].map(n=>n.getAttribute('data-i'))")
    assert rings == ['1', '2', '3']


def test_line_highlight_crossings(chart_page):
    """highlightPoints:'crossings': 双线相交点出现圈选环（A[0,10,10] vs B[10,0,0] → 仅段 0-1 相交 → 交点 index 1）"""
    chart_page.evaluate("""
      window.charts.line(document.getElementById('root'), [{label:'x',value:1}], {animation:false, highlightPoints:'crossings',
        series:[{name:'A',items:[{label:'a',value:0},{label:'b',value:10},{label:'c',value:10}]},
                {name:'B',items:[{label:'a',value:10},{label:'b',value:0},{label:'c',value:0}]}]})
    """)
    rings = chart_page.evaluate("[...document.querySelectorAll('.hm-c-dot-hl')].map(n=>n.getAttribute('data-i'))")
    assert rings == ['1']


def test_line_show_values_edge(chart_page):
    """showValues:'edge': 只标首尾有效点（LINE_ITEMS → 2 个标签: 首 2 / 末值）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, showValues:"edge"})', LINE_ITEMS)
    labels = chart_page.evaluate("[...document.querySelectorAll('.hm-c-vt')].map(n=>n.textContent)")
    assert len(labels) == 2 and labels[0] == '2'


def test_line_show_values_collision_avoid(chart_page):
    """密集数据(30 点) showValues:true: 重叠标签被跳过一个 → 标签数 < 点数（避让生效）"""
    chart_page.evaluate("""() => {
      const items = [];
      for (let i = 0; i < 30; i++) items.push({label:'p'+i, value: i % 7 + 1});
      window.charts.line(document.getElementById('root'), items, {animation:false, showValues:true});
      return [...document.querySelectorAll('.hm-c-vt')].length;
    }""")
    n = chart_page.evaluate("[...document.querySelectorAll('.hm-c-vt')].length")
    assert 0 < n < 30


def test_line_show_values_sparse_all_kept(chart_page):
    """稀疏数据(间距 ≥26 单位) showValues:true: 全部标签保留（避让阈值不过度跳标）"""
    chart_page.evaluate('(items) => window.charts.line(document.getElementById("root"), items, {animation:false, showValues:true})', LINE_ITEMS)
    labels = chart_page.evaluate("[...document.querySelectorAll('.hm-c-vt')].map(n=>n.textContent)")
    assert len(labels) == len(LINE_ITEMS)


# ── bar: stacked 堆叠柱（v1.23 · #336 多值 item 结构单一真相源）──

def test_bar_stacked_renders_percent(chart_page):
    """stacked:true 默认 percent 模式: 每柱 N 段, 高度合计 100%（段高占比正确）"""
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'周一',values:[30,50,20]},{label:'周二',values:[40,40,20]}],
        {stacked:true, animation:false});
    """)
    segs = chart_page.evaluate("document.querySelectorAll('.hm-c-sg').length")
    heights = chart_page.evaluate("[...document.querySelectorAll('.hm-c-sg')].map(n=>parseFloat(n.style.height))")
    assert segs == 6
    assert heights[:3] == [30.0, 50.0, 20.0]  # 周一三段 30/50/20
    assert sum(heights[:3]) == 100.0 and sum(heights[3:]) == 100.0


def test_bar_stacked_absolute_mode(chart_page):
    """stackMode:'absolute': 高度相对全局最大值（maxTotal）"""
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'周一',values:[30,50,20]},{label:'周二',values:[10,10,10]}],
        {stacked:true, stackMode:'absolute', animation:false});
    """)
    heights = chart_page.evaluate("[...document.querySelectorAll('.hm-c-sg')].map(n=>parseFloat(n.style.height))")
    assert heights[0] == 30.0  # maxTotal=100, 段 30 → 30%
    assert heights[3] == 10.0  # 周二首段 10 → 10%


def test_bar_stacked_validation_throws(chart_page):
    """缺 values / 段值非数字 / 各 item 段数不一致 → 直接报错"""
    e1 = chart_page.evaluate("""() => { try { window.charts.bar(document.getElementById('root'), [{label:'a',value:1}], {stacked:true}); return ''; } catch(e) { return e.message; } }""")
    e2 = chart_page.evaluate("""() => { try { window.charts.bar(document.getElementById('root'), [{label:'a',values:[1,'x']}], {stacked:true}); return ''; } catch(e) { return e.message; } }""")
    e3 = chart_page.evaluate("""() => { try { window.charts.bar(document.getElementById('root'), [{label:'a',values:[1,2]},{label:'b',values:[1]}], {stacked:true}); return ''; } catch(e) { return e.message; } }""")
    assert '必须含 values 数组' in e1 and '无效' in e2 and '长度必须一致' in e3


def test_bar_stacked_legend_and_colors(chart_page):
    """legend:true → segNames 图例（段色板）; colors 色板逐段取色"""
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'周一',values:[30,50,20]}],
        {stacked:true, legend:true, segNames:['蛋白质','脂肪','碳水'], colors:['#111','#222','#333'], animation:false});
    """)
    lg = chart_page.evaluate("[...document.querySelectorAll('.hm-c-lg')].map(n=>n.textContent)")
    segs_bg = chart_page.evaluate("[...document.querySelectorAll('.hm-c-sg')].map(n=>n.style.background)")
    assert lg == ['蛋白质', '脂肪', '碳水']
    # 浏览器归一化为 rgb: #111→rgb(17,17,17) / #222→rgb(34,34,34) / #333→rgb(51,51,51)
    assert segs_bg == ['rgb(17, 17, 17)', 'rgb(34, 34, 34)', 'rgb(51, 51, 51)']


def test_bar_stacked_total_label(chart_page):
    """showValues: 柱顶显示合计值（走 format）"""
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'周一',values:[30,50,20]}],
        {stacked:true, showValues:true, format:'{v}%', animation:false});
    """)
    v = chart_page.evaluate("document.querySelector('.hm-c-v')?.textContent")
    assert v == '100%'


def test_bar_stacked_default_byte_identical(chart_page):
    """缺省（不传 stacked/grouped）: 既有单柱渲染逐字节不变"""
    chart_page.evaluate('(items) => window.charts.bar(document.getElementById("root"), items, {animation:false})', LINE_ITEMS)
    html1 = chart_page.evaluate("document.getElementById('root').innerHTML")
    chart_page.evaluate('(items) => window.charts.bar(document.getElementById("root"), items, {animation:false, stacked:false})', LINE_ITEMS)
    html2 = chart_page.evaluate("document.getElementById('root').innerHTML")
    assert html1 == html2


# ── bar: grouped 分组双柱（v1.24 · #339 复用 #336 多值结构）──

def test_bar_grouped_renders_side_by_side(chart_page):
    """grouped:true: 每列 N 根并排子柱（宽度均分）; 高度按共享域"""
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'一月',values:[2,8]},{label:'二月',values:[4,6]}],
        {grouped:true, animation:false});
    """)
    gbs = chart_page.evaluate("[...document.querySelectorAll('.hm-c-gb')].map(n=>({w:n.getBoundingClientRect().width, h:parseFloat(n.style.height)}))")
    assert len(gbs) == 4
    assert abs(gbs[0]['w'] - gbs[1]['w']) < 1  # 子柱宽度均分
    assert gbs[1]['h'] > gbs[0]['h']  # 8 > 2


def test_bar_grouped_values_shared_domain(chart_page):
    """高度相对共享域（全域 max/min, 对齐单柱语义）: 值 8 → 100%"""
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'一月',values:[2,8]}],
        {grouped:true, animation:false});
    """)
    heights = chart_page.evaluate("[...document.querySelectorAll('.hm-c-gb')].map(n=>parseFloat(n.style.height))")
    # 域 [0,8]: 2→25%, 8→100%
    assert heights == [25.0, 100.0]


def test_bar_grouped_validation_throws(chart_page):
    """grouped 复用多值校验: 缺 values 数组 → 直接报错"""
    err = chart_page.evaluate("""() => { try { window.charts.bar(document.getElementById('root'), [{label:'a',value:1}], {grouped:true}); return ''; } catch(e) { return e.message; } }""")
    assert '必须含 values 数组' in err


def test_bar_grouped_legend_and_showvalues(chart_page):
    """legend: segNames 图例; showValues: 每根子柱顶部数值标签"""
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'一月',values:[2,8]}],
        {grouped:true, legend:true, segNames:['实做','计划'], showValues:true, format:'{v}件', animation:false});
    """)
    lg = chart_page.evaluate("[...document.querySelectorAll('.hm-c-lg')].map(n=>n.textContent)")
    vals = chart_page.evaluate("[...document.querySelectorAll('.hm-c-gv2')].map(n=>n.textContent)")
    assert lg == ['实做', '计划']
    assert vals == ['2件', '8件']


def test_bar_grouped_colors_palette(chart_page):
    """colors 色板逐子柱取色"""
    chart_page.evaluate("""
      window.charts.bar(document.getElementById('root'),
        [{label:'一月',values:[2,8]}],
        {grouped:true, colors:['#007aff','#ff9500'], animation:false});
    """)
    bgs = chart_page.evaluate("[...document.querySelectorAll('.hm-c-gb')].map(n=>n.style.background)")
    assert bgs == ['rgb(0, 122, 255)', 'rgb(255, 149, 0)']


def test_bar_grouped_default_byte_identical(chart_page):
    """缺省（不传 grouped）: 既有单柱渲染逐字节不变"""
    chart_page.evaluate('(items) => window.charts.bar(document.getElementById("root"), items, {animation:false})', LINE_ITEMS)
    html1 = chart_page.evaluate("document.getElementById('root').innerHTML")
    chart_page.evaluate('(items) => window.charts.bar(document.getElementById("root"), items, {animation:false, grouped:false})', LINE_ITEMS)
    html2 = chart_page.evaluate("document.getElementById('root').innerHTML")
    assert html1 == html2


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


# ── smartSelect 选择器组件（v1.11 · #312 · 复用优先·新建其次）────────────────────

BASE_SS_CFG = {
    'options': [
        {'name': '美团', 'disabled': False},
        {'name': '微信', 'disabled': False},
        {'name': '支付宝', 'disabled': True},
    ],
    'inferred': '美团',
    'recommended_new': '美团月付',
}


def _mount_ss(page, cfg, value=''):
    """root 内建一个 input 并挂 smartSelect 实例（window.__ss 保存句柄）"""
    page.evaluate("""(o) => {
      document.getElementById('root').innerHTML = '<input id="ss-inp">';
      var el = document.getElementById('ss-inp');
      if (o.value) el.value = o.value;
      window.__ss = window.smartSelect(el, o.cfg);
    }""", {'cfg': cfg, 'value': value})


def test_smart_select_renders_card_and_chips(page):
    """基本渲染: 已选卡片(AI 推断) + 候选 chips(含停用/推荐新建) + 隐藏 input"""
    _mount_ss(page, BASE_SS_CFG)
    nm = page.evaluate("document.querySelector('.ss-nm').textContent")
    src = page.evaluate("document.querySelector('.ss-src').textContent")
    badge = page.evaluate("document.querySelector('.ss-card .ss-badge').textContent")
    chips = page.evaluate("[...document.querySelectorAll('.ss-chip')].map(x => x.textContent)")
    assert nm == '美团' and badge == 'AI 推断'
    assert src == 'AI 推断 · 识别到相关信息'
    assert any('微信' in c for c in chips)
    assert any('支付宝' in c and '停用' in c for c in chips)
    assert any('AI 推荐·新建' in c for c in chips)
    disp = page.evaluate("getComputedStyle(document.getElementById('ss-inp')).display")
    assert disp == 'none'


def test_smart_select_priority_inferred_over_history(page):
    """优先级: AI 推断 > 历史预填(input.value)"""
    _mount_ss(page, BASE_SS_CFG, value='微信')
    nm = page.evaluate("document.querySelector('.ss-nm').textContent")
    src = page.evaluate("document.querySelector('.ss-src').textContent")
    assert nm == '美团' and 'AI 推断' in src


def test_smart_select_priority_history_over_recommended(page):
    """优先级: 历史预填 > AI 推荐新建（无推断时）"""
    _mount_ss(page, {'options': [{'name': '生活'}, {'name': '旅行'}], 'recommended_new': '家庭'}, value='旅行')
    nm = page.evaluate("document.querySelector('.ss-nm').textContent")
    badge = page.evaluate("document.querySelector('.ss-card .ss-badge').textContent")
    assert nm == '旅行' and badge == '历史'


def test_smart_select_default_recommended_new(page):
    """无推断无历史 → 默认选中 AI 推荐新建"""
    _mount_ss(page, {'options': [{'name': '生活'}], 'recommended_new': '家庭'})
    nm = page.evaluate("document.querySelector('.ss-nm').textContent")
    badge = page.evaluate("document.querySelector('.ss-card .ss-badge').textContent")
    val = page.evaluate("document.getElementById('ss-inp').value")
    isnew = page.evaluate("document.getElementById('ss-inp').dataset.new")
    assert nm == '家庭' and badge == 'AI 推荐·新建'
    assert val == '家庭' and isnew == '1'


def test_smart_select_initial_explicit_wins(page):
    """显式 initial 优先于一切推导"""
    _mount_ss(page, dict(BASE_SS_CFG, initial={'name': '现金', 'source': 'existing'}))
    nm = page.evaluate("document.querySelector('.ss-nm').textContent")
    src = page.evaluate("document.getElementById('ss-inp').dataset.source")
    assert nm == '现金' and src == 'existing'


def test_smart_select_writeback_protocol(page):
    """回填协议: input.value + dataset.source + dataset.new + change 事件"""
    _mount_ss(page, BASE_SS_CFG)
    page.evaluate("window.__changes = 0; document.getElementById('ss-inp').addEventListener('change', () => window.__changes++);")
    page.locator('.ss-chip', has_text='微信').click()
    st = page.evaluate("""() => {
      const el = document.getElementById('ss-inp');
      return { v: el.value, src: el.dataset.source, isNew: el.dataset.new, changes: window.__changes };
    }""")
    assert st == {'v': '微信', 'src': 'existing', 'isNew': '0', 'changes': 1}


def test_smart_select_click_switches_card(page):
    """点击候选 chip → 卡片与选中态更新"""
    _mount_ss(page, BASE_SS_CFG)
    page.locator('.ss-chip', has_text='微信').click()
    nm = page.evaluate("document.querySelector('.ss-nm').textContent")
    sel = page.evaluate("[...document.querySelectorAll('.ss-chip.ss-chip-sel')].map(x => x.textContent)")
    assert nm == '微信' and any('微信' in s for s in sel)


def test_smart_select_disabled_chip_inert(page):
    """停用态: 划线置灰 + 不可点"""
    _mount_ss(page, BASE_SS_CFG)
    dis = page.locator('.ss-chip.ss-chip-dis')
    assert dis.count() == 1 and '支付宝' in dis.first.text_content()
    assert dis.first.is_disabled()
    page.evaluate("document.querySelector('.ss-chip.ss-chip-dis').click()")  # disabled button 点击是 no-op
    assert page.evaluate("document.getElementById('ss-inp').value") == '美团'


def test_smart_select_custom_new(page):
    """自定义新建: 加入候选区 chip + 选中 + 回填 source=custom/new=1"""
    _mount_ss(page, BASE_SS_CFG)
    page.fill('.ss-new input', '美团月付卡')
    page.click('.ss-new button')
    st = page.evaluate("""() => {
      const el = document.getElementById('ss-inp');
      const chip = [...document.querySelectorAll('.ss-chip')].find(x => x.textContent.includes('美团月付卡'));
      return { v: el.value, src: el.dataset.source, isNew: el.dataset.new,
               chip: !!chip, badge: chip ? chip.querySelector('.ss-badge').textContent : '' };
    }""")
    assert st['v'] == '美团月付卡' and st['src'] == 'custom' and st['isNew'] == '1'
    assert st['chip'] and st['badge'] == '自定义'


def test_smart_select_duplicate_new_selects_existing(page):
    """重名自动选中已有项（source=existing, new=0）"""
    _mount_ss(page, BASE_SS_CFG)
    page.fill('.ss-new input', '美团')
    page.press('.ss-new input', 'Enter')
    st = page.evaluate("""() => {
      const el = document.getElementById('ss-inp');
      return { v: el.value, src: el.dataset.source, isNew: el.dataset.new };
    }""")
    assert st == {'v': '美团', 'src': 'existing', 'isNew': '0'}


def test_smart_select_similar_hint(page):
    """相似提示: 输入与已有项部分匹配 → 内置提示"""
    _mount_ss(page, BASE_SS_CFG)
    page.fill('.ss-new input', '微')
    hint = page.evaluate("document.querySelector('.ss-hint').textContent")
    vis = page.evaluate("document.querySelector('.ss-hint').style.display")
    assert '微信' in hint and vis != 'none'


def test_smart_select_empty_button(page):
    """留空按钮: 卡片空态 + 回填空 + source=empty"""
    _mount_ss(page, BASE_SS_CFG)
    page.click('.ss-empty')
    st = page.evaluate("""() => {
      const el = document.getElementById('ss-inp');
      return { v: el.value, src: el.dataset.source, isNew: el.dataset.new,
               emptyCard: !!document.querySelector('.ss-card.ss-card-empty') };
    }""")
    assert st == {'v': '', 'src': 'empty', 'isNew': '0', 'emptyCard': True}


def test_smart_select_requires_input_element(page):
    """inputEl 必须是 <input> 元素"""
    err = page.evaluate("""() => { try { window.smartSelect(document.createElement('div'), {options:[{name:'a'}]}); return ''; } catch(e) { return e.message; } }""")
    assert 'inputEl 必须是' in err


@pytest.mark.parametrize('cfg,err_frag', [
    (None, 'config 必须是对象'),
    ({'options': 'x'}, 'options 必须是数组'),
    ({'options': [{'name': ''}]}, 'name'),
    ({'options': [{'name': 'a', 'disabled': 'x'}]}, 'disabled 必须是布尔'),
    ({'inferred': 5}, 'inferred 必须是字符串'),
    ({'recommended_new': {}}, 'recommended_new 必须是字符串'),
    ({'initial': {'name': 'a', 'source': 'bad'}}, 'source'),
    ({'initial': {'source': 'existing'}}, 'name'),
    ({'texts': 'x'}, 'texts 必须是对象'),
])
def test_smart_select_validation_throws(page, cfg, err_frag):
    """结构校验违规直接报错（对齐 Base v1.2「违规直接报错」）"""
    err = page.evaluate("""(cfg) => { try { window.smartSelect(document.createElement('input'), cfg); return ''; } catch(e) { return e.message; } }""", cfg)
    assert err and 'smartSelect 违规' in err and err_frag in err


def test_smart_select_empty_options_degrades_plain_input(page):
    """降级: 无选项/无推断/无推荐/无 initial → 普通输入（T4 决议）"""
    _mount_ss(page, {})
    vis = page.evaluate("getComputedStyle(document.getElementById('ss-inp')).display")
    cls = page.evaluate("document.getElementById('ss-inp').className")
    assert vis != 'none' and 'ss-plain' in cls
    page.fill('#ss-inp', '旅行')
    st = page.evaluate("""() => {
      const el = document.getElementById('ss-inp');
      return { src: el.dataset.source, isNew: el.dataset.new };
    }""")
    assert st == {'src': 'custom', 'isNew': '1'}


def test_smart_select_host_bare_class_no_collision(page):
    """封装纪律: 宿主同名裸类规则不命中组件（.plain 冲突 bug 回归守卫）"""
    page.evaluate("""() => {
      const st = document.createElement('style');
      st.id = 'hostcss';
      st.textContent = '.plain{width:100%!important;color:red!important} .ai{color:red!important} .sel{outline:5px solid red} .dis{opacity:0!important}';
      document.head.appendChild(st);
    }""")
    try:
        _mount_ss(page, BASE_SS_CFG)
        tokens = page.evaluate("""[...new Set([...document.querySelectorAll('.ss-root *')].flatMap(x => [...x.classList]))]""")
        assert all(t.startswith('ss-') for t in tokens), f'组件类名混入裸类: {tokens}'
        color = page.evaluate("getComputedStyle(document.querySelector('.ss-card .ss-badge-ai')).color")
        assert color != 'rgb(255, 0, 0)'  # 宿主 .plain 未命中徽章
    finally:
        page.evaluate("document.getElementById('hostcss').remove()")


def test_smart_select_esc_anti_xss(page):
    """全部动态文本 esc, 零注入面"""
    _mount_ss(page, {'options': [{'name': '<img src=x onerror=alert(1)>'}], 'inferred': '<img src=x onerror=alert(2)>'})
    img = page.evaluate("document.querySelector('.ss-root img') !== null")
    raw = page.evaluate("document.getElementById('root').innerHTML")
    assert img is False
    assert '&lt;img' in raw and '<img src' not in raw


def test_smart_select_multi_instance_independent(page):
    """一页 N 实例互不干扰"""
    page.evaluate("""() => {
      document.getElementById('root').innerHTML = '<input id="a"><input id="b">';
      window.smartSelect(document.getElementById('a'), {options:[{name:'甲'},{name:'乙'}], inferred:'甲'});
      window.smartSelect(document.getElementById('b'), {options:[{name:'丙'},{name:'丁'}], inferred:'丙'});
    }""")
    assert page.evaluate("document.querySelectorAll('.ss-root').length") == 2
    page.locator('.ss-root').first.locator('.ss-chip', has_text='乙').click()
    a = page.evaluate("document.getElementById('a').value")
    b = page.evaluate("document.getElementById('b').value")
    assert a == '乙' and b == '丙'


def test_smart_select_search_filter(page):
    """搜索过滤候选（按名称过滤, 不命中徽章文案; 非匹配 chip 不渲染 + 输入框内容保持）"""
    _mount_ss(page, BASE_SS_CFG)
    page.fill('.ss-search', '微信')
    names = _visible_chip_names(page)
    assert names == ['微信']
    # 搜索框内容跨 render 保持（过滤状态不丢）
    assert page.evaluate("document.querySelector('.ss-search').value") == '微信'


def test_smart_select_theme_override(page):
    """主题覆盖: CSS 变量落在 .ss-root（每实例独立）"""
    _mount_ss(page, dict(BASE_SS_CFG, theme={'brand': '#123456'}))
    var = page.evaluate("document.querySelector('.ss-root').style.getPropertyValue('--ss-brand')")
    assert var == '#123456'


def test_smart_select_get_state(page):
    """getState/getValue 反映当前选中"""
    _mount_ss(page, BASE_SS_CFG)
    assert page.evaluate("window.__ss.getState()") == {'name': '美团', 'mode': 'inferred'}
    assert page.evaluate("window.__ss.getValue()") == '美团'
    page.locator('.ss-chip', has_text='微信').click()
    assert page.evaluate("window.__ss.getState()") == {'name': '微信', 'mode': 'existing'}


# ── 候选区折叠（v1.12 · #312 实测反馈: 大量候选时 chips 全量平铺过长）────────────

MANY_OPTIONS = [{'name': '分类' + str(i)} for i in range(1, 13)]  # 12 个


def _visible_chip_names(page):
    return page.evaluate(
        "[...document.querySelectorAll('.ss-root .ss-chip[data-n]')].map(x => x.getAttribute('data-n'))")


def test_smart_select_collapse_default(page):
    """超 maxChips(默认 8) → 折叠: 只显前 8 个 + 「展开全部(12)」按钮"""
    _mount_ss(page, {'options': MANY_OPTIONS})
    names = _visible_chip_names(page)
    assert len(names) == 8 and names[0] == '分类1'
    more = page.evaluate("document.querySelector('.ss-more')?.textContent")
    assert more == '展开全部(12)'


def test_smart_select_expand_and_collapse(page):
    """展开全部 → 12 个可见 + 收起按钮; 点收起 → 回折叠"""
    _mount_ss(page, {'options': MANY_OPTIONS})
    page.click('.ss-more')
    names = _visible_chip_names(page)
    assert len(names) == 12
    assert page.evaluate("document.querySelector('.ss-more')?.textContent") == '收起'
    page.click('.ss-more')
    assert len(_visible_chip_names(page)) == 8


def test_smart_select_collapse_keeps_selected_visible(page):
    """折叠时选中项保可见: initial 选中第 10 个 → 出现在可见区"""
    _mount_ss(page, {'options': MANY_OPTIONS, 'initial': {'name': '分类10', 'source': 'existing'}})
    names = _visible_chip_names(page)
    assert '分类10' in names and len(names) == 8


def test_smart_select_collapse_selected_chip_highlighted(page):
    """折叠保可见的选中 chip 带选中态(ss-chip-sel)"""
    _mount_ss(page, {'options': MANY_OPTIONS, 'initial': {'name': '分类10', 'source': 'existing'}})
    sel = page.evaluate("[...document.querySelectorAll('.ss-chip.ss-chip-sel')].map(x => x.getAttribute('data-n'))")
    assert sel == ['分类10']


def test_smart_select_search_passes_collapse(page):
    """折叠态搜索 → 全量过滤（第 10 个也能搜出, 不受折叠限制）"""
    _mount_ss(page, {'options': MANY_OPTIONS})
    page.fill('.ss-search', '分类10')
    names = _visible_chip_names(page)
    assert names == ['分类10']


def test_smart_select_search_clear_returns_collapsed(page):
    """清空搜索 → 回到折叠态（前 8 个 + 展开按钮）"""
    _mount_ss(page, {'options': MANY_OPTIONS})
    page.fill('.ss-search', '分类10')
    page.fill('.ss-search', '')
    names = _visible_chip_names(page)
    assert len(names) == 8
    assert page.evaluate("document.querySelector('.ss-more')?.textContent") == '展开全部(12)'


def test_smart_select_expand_keeps_after_select(page):
    """展开态点选 chip 后保持展开（不自动收起, 便于连续改选）"""
    _mount_ss(page, {'options': MANY_OPTIONS})
    page.click('.ss-more')
    page.locator('.ss-chip', has_text='分类9').click()
    assert len(_visible_chip_names(page)) == 12


def test_smart_select_max_chips_configurable(page):
    """maxChips 可配: 3 → 只显 3 个; 0/非正整数/缺省行为各异"""
    _mount_ss(page, {'options': MANY_OPTIONS, 'maxChips': 3})
    assert len(_visible_chip_names(page)) == 3
    _mount_ss(page, {'options': MANY_OPTIONS, 'maxChips': 0})
    assert len(_visible_chip_names(page)) == 12
    assert page.evaluate("document.querySelector('.ss-more')") is None
