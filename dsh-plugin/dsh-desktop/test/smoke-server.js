'use strict';

// 冒烟/托盘测试用的假 DSH 服务：监听 DSH_DESKTOP_PORT（默认 3080），返回带
// __DSH_BOOT__ 指纹的页面。桌面版只认这个指纹（见 main.js checkDsh），
// 之前返回纯文本导致测试连不上；用于验证「拉起 → 就绪 → 关窗隐藏 → 清理」等生命周期，不碰真实 DSH。

const http = require('http');

const port = Number(process.env.DSH_DESKTOP_PORT || 3080);

const page = `<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>fake DSH</title></head>
<body style="background:#0a0a0a;color:#d4d4d4;font-family:sans-serif">
<script>window.__DSH_BOOT__ = true;</script>
<h1>fake DSH（测试服务）</h1>
<p>由 dsh-desktop/test/smoke-server.js 提供，仅供自动化验证。</p>
</body></html>`;

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/html' });
  res.end(page);
});

server.listen(port, '127.0.0.1', () => {
  console.log('SMOKE_SERVER_READY on ' + port);
});

function shutdown() {
  server.close(() => process.exit(0));
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
