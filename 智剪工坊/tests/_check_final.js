const fs = require('fs');
const h = fs.readFileSync('D:/2Study/StudyNotes/SKILLS/智剪工坊/intent.html', 'utf8');
const m = h.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.log('No script'); process.exit(1); }
try { new Function(m[1]); console.log('JS Syntax: OK'); } catch (e) { console.log('ERROR:', e.message.slice(0, 300)); }
const checks = [
  ['seq-section before ops-group', h.indexOf('seq-section') < h.indexOf('class="ops-group"')],
  ['label text 顺序', h.includes('>顺序</') || h.includes('>顺序<')],
  ['placeholder 接哪段', h.includes('接哪段视频')],
  ['thumb maxW=120', h.includes('const maxW = 120, maxH = 68')],
  ['initialVal in refresh', h.includes('dataset.initialVal')],
  ['CSS video-thumb 120', h.includes('max-width: 120px')],
  ['CSS media 100', h.includes('max-width: 100px')],
];
checks.forEach(([k, v]) => console.log(v ? '✓' : '✗', k));
console.log('Size:', h.length, 'bytes /', h.split('\n').length, 'lines');
