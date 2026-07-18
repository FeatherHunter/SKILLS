// lib.js — 高德 Web Service API 共享客户端
// 用法: const { callGaode, parseArgs } = require('./lib');

const https = require('https');
const { URL } = require('url');

// 高德业务错误码 → 通俗翻译(节选最常见的)
const ERROR_CODES = {
  '10000': 'INVALID_USER_KEY — Key 不存在或被删除,请去 lbs.amap.com 申请',
  '10001': 'INVALID_USER_KEY — 同上',
  '10002': 'SERVICE_NOT_AVAILABLE — 该 Key 未开通对应平台,申请时勾选「Web Service JS API」',
  '10003': 'SERVICE_OFFLINE — 接口停维护,稍后重试',
  '10004': 'USER_IP_RECORDED_ERROR — 服务器 IP 不在白名单,申请 Key 时 IP 留空或加白',
  '10005': 'USER_KEY_RECORDED_ERROR — Key 未启用,去 lbs.amap.com 启用',
  '10006': 'USER_IP_NOT_RECORDED_WHITE_LIST — 同 10004',
  '10007': 'USER_IP_IN_BLACK_LIST — IP 在黑名单',
  '10008': 'ILLEGAL_REQUEST_URL — 非法 URL',
  '10009': 'ILLEGAL_REQUEST_METHOD — 非法请求方式',
  '10010': 'USER_DAILY_QUERY_OVER_LIMIT — 单日调用量超限,升级到企业版',
  '10011': 'USER_QPS_HAS_EXCEEDED_THE_LIMIT — QPS 超限,降低调用频率',
  '10012': 'USER_ABNORMAL_OPERATION — 操作异常,检查请求参数',
  '10013': 'INVALID_PARAMETER — 参数非法',
  '10014': 'CUQPS_HAS_EXCEEDED_THE_LIMIT — QPS 超限',
  '10015': 'INVALID_USER_SIGN — 签名错误',
  '10016': 'SERVICE_RIDING — 服务维护中',
  '10017': 'USER_ABNORMAL_OPERATION_KEY — Key 异常',
  '10018': 'USER_ABNORMAL_OPERATION_IP — IP 异常',
  '10019': 'USER_ABNORMAL_OPERATION_SIGNATURE — 签名异常',
  '10020': 'USER_ABNORMAL_OPERATION_QPS — QPS 异常',
  '10021': 'USER_ABNORMAL_OPERATION_QUERY_LIMIT — 配额异常',
  '10022': 'INVALID_USER_DOMAIN — 域名非法',
  '10023': 'INVALID_PLATFORM_SIGNATURE — 平台签名非法',
  '10024': 'INVALID_USER_CITY — 城市非法',
  '10025': 'INVALID_PRODUCT — 产品非法',
  '10026': 'INVALID_COMPANY — 公司非法',
  '10027': 'INVALID_UDID — 设备 ID 非法',
  '10028': 'INVALID_USER — 用户非法',
  '10029': 'INVALID_SIGNATURE — 签名非法',
  '10030': 'INVALID_TIMESTAMP — 时间戳非法',
  '10031': 'INVALID_USER_KEY_TYPE — Key 类型非法',
  '10032': 'INVALID_USER_DEVICE — 设备非法',
  '10033': 'INVALID_GPS_COORDINATES — GPS 坐标非法',
  '20000': 'NO_RESPONSE_DATA — 无返回数据',
  '20001': 'ENGINE_RESPONSE_DATA_ERROR — 数据错误',
  '20002': 'ENGINE_RESPONSE_DATA_TIMEOUT — 数据超时',
  '20003': 'ENGINE_INTERNAL_ERROR — 引擎错误',
  '20800': 'OUT_OF_SERVICE — 超出服务范围',
  '20801': 'NO_ROADS_NEARBY — 附近无道路',
  '20802': 'ROUTE_FAIL — 路径规划失败',
  '20803': 'OVER_SEARCH_RANGE — 超出搜索范围',
  '20804': 'ENGINE_INTERNAL_ERROR — 引擎错误',
  '20900': 'INVALID_CITY — 城市非法',
  '20901': 'MISSING_CITY — 缺少城市',
  '20902': 'INVALID_CITYID — 城市 ID 非法',
  '20903': 'INVALID_ROAD — 道路非法',
  '20904': 'INVALID_POLYGON — 多边形非法',
};

// 加载 Key:命令行 --key > 环境变量 AMAP_WEBSERVICE_KEY
function loadKey(args) {
  if (args.key) return args.key;
  const k = process.env.AMAP_WEBSERVICE_KEY;
  if (!k) {
    throw new Error('Key not set. Run: setx AMAP_WEBSERVICE_KEY "your_key" 或用 --key 参数临时指定');
  }
  return k;
}

// 把 --a=1 --b=2 解析成 { a:'1', b:'2' }
function parseArgs(argv) {
  const out = {};
  for (const a of argv.slice(2)) {
    const m = a.match(/^--([^=]+)=(.+)$/);
    if (m) out[m[1]] = m[2];
  }
  return out;
}

// 调用高德 REST API
// path: '/v3/place/text'
// params: { keywords, city, ... }
function callGaode(path, params, key) {
  const qs = new URLSearchParams({ ...params, key, output: 'JSON' }).toString();
  const url = `https://restapi.amap.com${path}?${qs}`;
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let buf = '';
      res.on('data', (c) => (buf += c));
      res.on('end', () => {
        try {
          const j = JSON.parse(buf);
          if (j.status === '1') {
            resolve(j);
          } else {
            const msg = ERROR_CODES[j.infocode] || `${j.info} (${j.infocode})`;
            const err = new Error(`高德业务错误: ${msg}`);
            err.code = j.infocode;
            reject(err);
          }
        } catch (e) {
          reject(new Error(`响应解析失败: ${e.message} | raw=${buf.slice(0, 200)}`));
        }
      });
    }).on('error', reject);
  });
}

// 错误码翻译(供外部 require)
function translateError(infocode) {
  return ERROR_CODES[infocode] || `未知错误码 ${infocode}`;
}

module.exports = { loadKey, parseArgs, callGaode, translateError };