// poi-search.js — 关键字搜索 POI
// 用法: node poi-search.js --keywords=肯德基 --city=北京
//       node poi-search.js --keywords=咖啡 --city=上海 --types=050000

const { loadKey, parseArgs, callGaode } = require('./lib');

async function main() {
  const args = parseArgs(process.argv);
  if (!args.keywords) {
    console.error('用法: node poi-search.js --keywords=<关键字> [--city=<城市>] [--types=<分类码>] [--offset=<每页条数>] [--page=<页码>]');
    process.exit(1);
  }
  const key = loadKey(args);
  const params = { keywords: args.keywords };
  if (args.city) params.city = args.city;
  if (args.types) params.types = args.types;
  if (args.offset) params.offset = args.offset;
  if (args.page) params.page = args.page;

  try {
    const data = await callGaode('/v3/place/text', params, key);
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error(e.message);
    process.exit(2);
  }
}

main();