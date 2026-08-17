// 从 boot 页提取 waystation client bundle URL 并检查内容
const http = require('http')
function get(url, cb) {
  http.get(url, res => {
    let d = ''
    res.on('data', c => d += c)
    res.on('end', () => cb(d))
  }).on('error', e => cb('ERR:' + e.message))
}
get('http://127.0.0.1:59519/', html => {
  const m = html.match(/window\.__DSH_BOOT__ = (\{[\s\S]*?\})<\/script>/)
  if (!m) { console.log('no boot found'); return }
  let boot
  try { boot = JSON.parse(m[1]) } catch (e) { console.log('boot parse err', e.message); return }
  const ws = (boot.entries || []).find(e => e.id && e.id.indexOf('dsh-waystation') >= 0)
  console.log('waystation entry:', JSON.stringify(ws))
  if (!ws || !ws.url) return
  get('http://127.0.0.1:59519' + ws.url, code => {
    if (code.startsWith('ERR:')) { console.log('fetch err:', code); return }
    console.log('bundle len:', code.length)
    console.log('has dsws-spin:', code.includes('dsws-spin'))
    console.log('has scheduleActionProbe:', code.includes('scheduleActionProbe'))
    console.log('has rowFlash:', code.includes('rowFlash'))
    console.log('has diffRemoved:', code.includes('diffRemoved'))
    console.log('has v1.5 marker PROBE_MS:', code.includes('PROBE_MS'))
  })
})