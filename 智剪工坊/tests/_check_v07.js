const fs = require('fs');
const h = fs.readFileSync('D:/2Study/StudyNotes/SKILLS/智剪工坊/intent.html', 'utf8');
const checks = [
  ['seq-section', h.includes('seq-section')],
  ['card-toggle', h.includes('card-toggle')],
  ['initSequencesUI', h.includes('function initSequencesUI')],
  ['toggleCard', h.includes('function toggleCard')],
  ['loadSequencesFromIntent', h.includes('function loadSequencesFromIntent')],
  ['onSeqNextChange', h.includes('function onSeqNextChange')],
  ['refreshAllSeqDropdowns', h.includes('function refreshAllSeqDropdowns')],
  ['no addSequence (old)', h.includes('function addSequence')],
  ['no sequences-list HTML', !h.includes('sequences-list')],
  ['no top-level seq section', !h.includes('<h2>视频序列')],
  ['version 0.7', h.includes("version: '0.7'")],
];
checks.forEach(([k, v]) => console.log((v ? '✓' : '✗'), k));
console.log('\nFile size:', h.length, 'bytes,', h.split('\n').length, 'lines');
