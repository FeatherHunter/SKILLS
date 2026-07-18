---
name: gaode-map
description: |
  通过 ClawHub 商店安装并使用高德官方地图综合服务 Skill(POI 搜索/路径规划/旅游规划/周边搜索/热力图)。
  Use when user wants 高德/AMap 地图查询、地点搜索、附近搜索、路线规划、热力图可视化;中国境内地理服务。
  Do NOT use for 百度地图/腾讯地图/Google Maps;不用于需要海外服务或离线场景。
descriptions:
  zh-Hans: "通过 ClawHub 安装并使用高德官方地图综合服务 Skill"
displayNames:
  zh-Hans: "高德地图"
---

# 高德地图 Skill

通过 ClawHub 商店安装高德官方地图 LBS 服务。

## 安装路径

1. 打开 ClawHub Skill 页面:`https://clawhub.ai/lbs-amap/skills/amap-lbs-skill`
2. 复制页面上的安装命令(默认是 `openclaw skills install @lbs-amap/amap-lbs-skill`)
3. 首次使用需要高德 Web Service Key:`export AMAP_WEBSERVICE_KEY=your_key`
   - Key 申请:`https://lbs.amap.com/api/webservice/create-project-and-key`

## 触发场景

- 关键词:搜美食/找酒店/天安门在哪/西直门周边/规划路线/北京一日游/生成热力图
- 场景:POI 搜索/周边搜索/路径规划(步行/驾车/公交)/旅游规划/热力图可视化

## 失败处理

- openclaw 未装:先装 openclaw CLI(参考 ClawHub 文档)
- 缺 API Key:提示用户去高德开放平台申请
- 调用失败:检查 Key 是否正确 + 地址是否有效 + 调用频率

## 验证

```bash
node scripts/poi-search.js --keywords=肯德基 --city=北京
```

## 输出格式

- 简短搜索 → `https://www.amap.com/search?query={关键词}`(浏览器跳转)
- 复杂查询 → 调用高德 API 返回 JSON / 拼接可视化链接

## Windows (win32) platform notes

- `openclaw` CLI 需先在 PowerShell 安装(参考 ClawHub 文档);mavis CLI 不可用时会报 `MODULE_NOT_FOUND: daemon/cli.js`
- `setx AMAP_WEBSERVICE_KEY "your_key"` 永久设置环境变量;`$env:AMAP_WEBSERVICE_KEY="your_key"` 临时设置
- 验证命令在 PowerShell 下同样有效:`node scripts\poi-search.js --keywords=肯德基 --city=北京`
