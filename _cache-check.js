const fs = require('fs')
const dir = process.env.APPDATA + '\\DSH Desktop\\.dsh-waystation-cache'
const files = fs.readdirSync(dir).filter(f => f.endsWith('.json'))
files.forEach(f => {
  try {
    const j = JSON.parse(fs.readFileSync(dir + '\\' + f, 'utf8'))
    console.log(f, '→ ok=' + j.ok, 'maps=' + (j.maps ? j.maps.length : '?'), 'issues=' + (j.issues ? j.issues.length : '?'), 'generatedMs=' + j.generatedMs, 'fallback=' + j.fallback, 'cwd=' + (j.cwd || '-'))
    if (j.maps && j.maps.length) console.log('   first map:', j.maps[0].number, j.maps[0].title.slice(0, 40))
  } catch (e) { console.log(f, '→ parse error:', String(e).slice(0, 80)) }
})