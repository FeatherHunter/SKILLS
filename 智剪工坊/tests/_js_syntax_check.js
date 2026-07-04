const fs = require('fs');
const path = 'D:\\2Study\\StudyNotes\\SKILLS\\智剪工坊\\intent.html';
const html = fs.readFileSync(path, 'utf8');
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) { console.log('No script tag found'); process.exit(0); }
try {
  new Function(match[1]);
  console.log('OK - no syntax errors');
} catch(e) {
  console.log('SYNTAX ERROR:', e.message);
  const lines = match[1].split('\n');
  const m = e.message.match(/line (\d+)/);
  if (m) {
    const ln = parseInt(m[1]);
    for (let i = Math.max(0,ln-4); i < Math.min(lines.length, ln+3); i++) {
      console.log((i+1 === ln ? '>>>' : '   ') + ' ' + (i+1) + ': ' + lines[i]);
    }
  } else {
    // print around the error position
    const pos = parseInt(e.message.match(/position (\d+)/)?.[1] || 0);
    const start = Math.max(0, pos - 100);
    const end = Math.min(match[1].length, pos + 100);
    console.log('Near position', pos, ':', match[1].slice(start, end));
  }
}
