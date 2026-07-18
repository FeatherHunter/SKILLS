// regeocode.js — 逆地理编码(经纬度 → 地址)
// 用法: node regeocode.js --location=116.355,39.942

const { loadKey, parseArgs, callGaode } = require('./lib');

async function main() {
  const args = parseArgs(process.argv);
  if (!args.location) {
    console.error('用法: node regeocode.js --location=<lng,lat> [--radius=<米>] [--extensions=base|all]');
    process.exit(1);
  }
  const key = loadKey(args);
  const params = {
    location: args.location,
    extensions: args.extensions || 'base',
  };
  if (args.radius) params.radius = args.radius;

  try {
    const data = await callGaode('/v3/geocode/regeo', params, key);
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error(e.message);
    process.exit(2);
  }
}

main();