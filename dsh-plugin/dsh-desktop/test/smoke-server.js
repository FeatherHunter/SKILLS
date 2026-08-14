'use strict';

// 冒烟测试用的假 DSH 服务：监听 DSH_DESKTOP_PORT（默认 3080），返回 200。
// 用于验证「拉起 → 就绪 → 关窗 → 进程树被杀」的完整生命周期，不碰真实 DSH。

const http = require('http');

const port = Number(process.env.DSH_DESKTOP_PORT || 3080);

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/plain' });
  res.end('smoke ok');
});

server.listen(port, '127.0.0.1', () => {
  console.log('SMOKE_SERVER_READY on ' + port);
});

function shutdown() {
  server.close(() => process.exit(0));
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
