// weather.js — 天气查询
// 用法: node weather.js --city=北京 --extensions=base
// extensions: base(实时天气,默认) / all(预报未来3天)

const { loadKey, parseArgs, callGaode } = require('./lib');

async function main() {
  const args = parseArgs(process.argv);
  if (!args.city) {
    console.error('用法: node weather.js --city=<城市名或adcode> [--extensions=base|all]');
    process.exit(1);
  }
  const key = loadKey(args);
  const params = {
    city: args.city,
    extensions: args.extensions || 'base',
  };

  try {
    const data = await callGaode('/v3/weather/weatherInfo', params, key);
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error(e.message);
    process.exit(2);
  }
}

main();