// route-planning.js — 路径规划(驾车/步行/公交/骑行)
// 用法: node route-planning.js --origin=116.397,39.909 --destination=116.609,40.080 --mode=driving
// mode: driving(默认) / walking / transit / bicycling

const { loadKey, parseArgs, callGaode } = require('./lib');

const PATH_BY_MODE = {
  driving: '/v3/direction/driving',
  walking: '/v3/direction/walking',
  transit: '/v3/direction/transit/integrated',
  bicycling: '/v4/direction/bicycling',
};

async function main() {
  const args = parseArgs(process.argv);
  if (!args.origin || !args.destination) {
    console.error('用法: node route-planning.js --origin=<lng,lat> --destination=<lng,lat> --mode=<driving|walking|transit|bicycling>');
    process.exit(1);
  }
  const mode = args.mode || 'driving';
  const path = PATH_BY_MODE[mode];
  if (!path) {
    console.error(`不支持的 mode: ${mode},可选: ${Object.keys(PATH_BY_MODE).join(', ')}`);
    process.exit(1);
  }

  const key = loadKey(args);
  const params = { origin: args.origin, destination: args.destination };
  if (mode === 'transit' && args.city) params.city = args.city;
  if (mode === 'transit' && args.strategy) params.strategy = args.strategy;
  if (args.extensions) params.extensions = args.extensions;

  try {
    const data = await callGaode(path, params, key);
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error(e.message);
    process.exit(2);
  }
}

main();