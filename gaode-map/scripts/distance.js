// distance.js — 距离测量(多起点 vs 多终点)
// 用法: node distance.js --origins=116.355,39.942|116.401,39.945 --destination=116.609,40.080 --type=1
// type: 1=驾车距离 2=步行距离 3=直线距离(默认 1)

const { loadKey, parseArgs, callGaode } = require('./lib');

async function main() {
  const args = parseArgs(process.argv);
  if (!args.origins || !args.destination) {
    console.error('用法: node distance.js --origins=<lng1,lat1|lng2,lat2|...> --destination=<lng,lat> [--type=1|2|3]');
    process.exit(1);
  }
  const key = loadKey(args);
  const params = {
    origins: args.origins,
    destination: args.destination,
    type: args.type || '1',
  };

  try {
    const data = await callGaode('/v3/distance', params, key);
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error(e.message);
    process.exit(2);
  }
}

main();