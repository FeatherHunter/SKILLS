// around-search.js — 中心点周边搜索
// 用法: node around-search.js --location=116.355,39.942 --keywords=咖啡 --radius=1000

const { loadKey, parseArgs, callGaode } = require('./lib');

async function main() {
  const args = parseArgs(process.argv);
  if (!args.location || !args.keywords) {
    console.error('用法: node around-search.js --location=<经度,纬度> --keywords=<关键字> [--radius=<米,默认1000>] [--types=<分类码>]');
    process.exit(1);
  }
  const key = loadKey(args);
  const params = {
    location: args.location,
    keywords: args.keywords,
    radius: args.radius || '1000',
  };
  if (args.types) params.types = args.types;

  try {
    const data = await callGaode('/v3/place/around', params, key);
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error(e.message);
    process.exit(2);
  }
}

main();