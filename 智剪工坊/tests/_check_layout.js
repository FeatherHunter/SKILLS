const fs = require('fs');
const h = fs.readFileSync('D:/2Study/StudyNotes/SKILLS/智剪工坊/intent.html', 'utf8');
const m = h.match(/<script>([\s\S]*?)<\/script>/);
try { new Function(m[1]); console.log('JS OK'); } catch (e) { console.log('ERR:', e.message.slice(0, 300)); }
const checks = [
  ['seq-trans-block CSS display:none + .show rule', h.includes('.seq-trans-block.show { display: flex; }') && h.includes('.seq-trans-block {\n      margin-top: 10px;\n      display: none;')],
  ['classList toggle show', h.includes("classList.toggle('show'")],
  ['flex 1 1 0', h.includes('flex: 1 1 0;')],
  ['flex 0 0 56px', h.includes('flex: 0 0 56px;')],
  ['min-width: 0', h.includes('min-width: 0;')],
  ['no inline style=display:none', !h.includes('style="display:none"')],
];
checks.forEach(([k, v]) => console.log(v ? 'OK' : 'XX', k));
