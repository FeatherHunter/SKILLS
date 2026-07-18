// geocode.js — 地理编码(地址 → 经纬度)
// 用法: node geocode.js --address=北京市海淀区中关村南大街5号 --city=北京

const { loadKey, parseArgs, callGaode } = require('./lib');

async function main() {
  const args = parseArgs(process.argv);
  if (!args.address) {
    console.error('用法: node geocode.js --address=<地址> [--city=<城市>]');
    process.exit(1);
  }
  const key = loadKey(args);
  const params = { address: args.address };
  if (args.city) params.city = args.city;

  try {
    const data = await callGaode('/v3/geocode/geo', params, key);
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error(e.message);
    process.exit(2);
  }
}

main();