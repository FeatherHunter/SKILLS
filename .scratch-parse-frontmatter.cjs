const fs = require('node:fs');
const { parse } = require('D:/0Tools/DSHDesktop/DSH Desktop/resources/app/node_modules/yaml');
const text = fs.readFileSync('D:/2Study/StudyNotes/SKILLS/npm-publish/SKILL.md', 'utf8');
const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
if (!m) { console.log('NO FRONTMATTER'); process.exit(0); }
try {
  const data = parse(m[1]);
  console.log(JSON.stringify({ ok: true, name: data.name, hasDesc: typeof data.description, descLen: (data.description || '').length, keys: Object.keys(data) }));
} catch (e) {
  console.log('PARSE ERROR: ' + e.message);
}