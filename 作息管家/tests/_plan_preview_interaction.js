// 作息管家 plan_preview 交互测试脚本(2026-08-13 · #324 收尾 A 项)
// 用法: node _plan_preview_interaction.js <rendered_html_path>
// 用 DOM stub 执行渲染产物的内联脚本,模拟用户交互并断言;输出 JSON;断言失败 exit 1。
'use strict';
const fs = require('fs');

const htmlPath = process.argv[2];
const html = fs.readFileSync(htmlPath, 'utf8');

const payloadMatch = html.match(/<script id="payload" type="application\/json">([\s\S]*?)<\/script>/);
if (!payloadMatch) { console.log(JSON.stringify({ all_ok: false, reason: 'no payload script' })); process.exit(1); }
const payload = JSON.parse(payloadMatch[1]);

const scripts = [...html.matchAll(/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const main = scripts[scripts.length - 1].replace(/<!--[\s\S]*?-->/g, '');

function makeEl() {
  const el = {
    innerHTML: '', className: '', style: {}, title: '',
    parentElement: { className: '' },
    _handlers: {}, _children: [], _inserted: [],
    addEventListener(type, fn) { (this._handlers[type] = this._handlers[type] || []).push(fn); },
    dispatch(type, ev) { (this._handlers[type] || []).forEach(fn => fn(ev || {})); },
    getAttribute() { return null; },
    querySelectorAll(sel) {
      return sel === 'input[type=time]' ? this._children.filter(c => c.tagName === 'INPUT') : [];
    },
    insertAdjacentHTML(pos, str) {
      this._inserted.push(str);
      const re = /<input type="time" data-idx="(\d+)" data-field="([se])" value="([^"]*)"/g;
      let m;
      while ((m = re.exec(str))) {
        const inp = makeEl();
        inp.tagName = 'INPUT'; inp.type = 'time'; inp.value = m[3];
        inp._idx = Number(m[1]); inp._field = m[2];
        inp.getAttribute = function (k) {
          return k === 'data-idx' ? String(this._idx) : k === 'data-field' ? this._field : null;
        };
        this._children.push(inp);
      }
    },
  };
  // 模拟真实 DOM:textContent 赋值强制字符串化(模板 JS 会赋数字)
  let _text = '';
  Object.defineProperty(el, 'textContent', {
    get() { return _text; },
    set(v) { _text = String(v); },
  });
  return el;
}

const els = {};
const documentStub = { getElementById(id) { return els[id] || (els[id] = makeEl()); } };
els['payload'] = { textContent: JSON.stringify(payload) };
const copyCalls = [];
const windowStub = {
  innerWidth: 1280,
  copyText(t) { copyCalls.push(t); },
  actionBar() { return '<div class="hm-actions">复制数据 / 复制日志</div>'; },
};

new Function('document', 'window', main)(documentStub, windowStub);

const checks = [];
function check(name, ok, detail) { checks.push({ name, ok, detail: detail || '' }); }

check('标题=商量计划 · 2026-08-15', els['page-title'].textContent === '商量计划 · 2026-08-15', els['page-title'].textContent);
check('徽章与动作状态行不重复', els['status-badge'].textContent !== els['act-status'].textContent,
  `badge="${els['status-badge'].textContent}" act="${els['act-status'].textContent}"`);
check('候选数=2', els['stat-candidate'].textContent === '2', els['stat-candidate'].textContent);
check('冲突数=1', els['stat-conflicts'].textContent === '1', els['stat-conflicts'].textContent);

const conflictList = els['conflict-list'];
const inserted = conflictList._inserted.join('\n');
const timeInputs = conflictList.querySelectorAll('input[type=time]');
check('冲突卡渲染(本次候选/已锁定/重叠时段)',
  inserted.includes('本次候选') && inserted.includes('已锁定') && inserted.includes('重叠时段'), '');
check('泳道渲染(cand/lock/overlap bar)',
  inserted.includes('class="bar cand"') && inserted.includes('class="bar lock"') && inserted.includes('class="bar overlap"'), '');
check('时间输入=2', timeInputs.length === 2, String(timeInputs.length));

// 复制 1:未调整
els['copy-btn'].dispatch('click');
const p1 = copyCalls[copyCalls.length - 1] || '';
check('复制含①技能与唤醒词', p1.includes('① 技能与唤醒词: 作息管家 · 「商量计划」'), p1.slice(0, 80));
check('复制含②参数/③执行', p1.includes('② 参数') && p1.includes('③ 执行'), '');
check('复制无脚本调用', !p1.includes('schedule_cli.py'), '');
check('复制含重叠明细', p1.includes('重叠 09:00–09:30'), '');

// 调整冲突候选时段后复制 2
const sInput = timeInputs[0];
sInput.value = '08:30';
sInput.dispatch('change');
els['copy-btn'].dispatch('click');
const p2 = copyCalls[copyCalls.length - 1] || '';
check('调整后复制含新时段', p2.includes('"time_start": "08:30"'), '');
check('调整后复制标注已调整', p2.includes('候选时段已由用户调整') && p2.includes('写库前先与用户确认调整结果'), '');
check('调整提示出现', els['adjust-hint'].textContent.includes('已调整 1 段候选时段'), els['adjust-hint'].textContent);

const failed = checks.filter(c => !c.ok);
console.log(JSON.stringify({ all_ok: failed.length === 0, checks }, null, 2));
process.exit(failed.length === 0 ? 0 : 1);
