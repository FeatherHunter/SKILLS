# chatgpt-image2 - 图片生成技能

## 简介

基于 AI Hub API 的 **GPT-Image-2** 模型，`nano-banana-2` 作为备用模型。

## 配置

- **API 地址**：`https://api.xbai.top/v1`
- **API Key**：`sk-C2fSyNPHTzeqIzu1TrIHWyxA8GOq0acjerGOdsNDyz6gORxr`
- **主模型**：`gpt-image-2`（高质量生图）
- **备用模型**：`nano-banana-2`（快速生图）

## ⚠️ 重要：接口调用方式

**必须使用 `/v1/images/generations` 接口生成图片，不要用 `/v1/images/edits`！**

GPT-Image-2 的 `/v1/images/edits`（垫图/参考图）接口响应极慢（经常超时），而生图接口稳定且速度快。

## 工具调用方式

### 方式一：Python requests（推荐）

```python
import requests

resp = requests.post(
    'https://api.xbai.top/v1/images/generations',
    headers={'Authorization': 'Bearer sk-C2fSyNPHTzeqIzu1TrIHWyxA8GOq0acjerGOdsNDyz6gORxr'},
    json={
        'model': 'gpt-image-2',
        'prompt': '你的图片描述',
        'n': 1,
        'size': '1024x1024',
        'quality': 'standard',
        'response_format': 'url'
    },
    timeout=180
)

url = resp.json()['data'][0]['url']
# 下载图片
img_data = requests.get(url).content
with open('output.png', 'wb') as f:
    f.write(img_data)
```

### 方式二：curl

```bash
curl -s --max-time 180 --request POST \
  --url https://api.xbai.top/v1/images/generations \
  --header "Authorization: Bearer sk-C2fSyNPHTzeqIzu1TrIHWyxA8GOq0acjerGOdsNDyz6gORxr" \
  --header "Content-Type: application/json" \
  --data '{
    "model": "gpt-image-2",
    "prompt": "你的图片描述",
    "n": 1,
    "size": "1024x1024",
    "quality": "standard",
    "response_format": "url"
  }'
```

### 方式三：OpenAI Python 库

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-C2fSyNPHTzeqIzu1TrIHWyxA8GOq0acjerGOdsNDyz6gORxr",
    base_url="https://api.xbai.top/v1"
)

response = client.images.generate(
    model="gpt-image-2",
    prompt="你的图片描述",
    n=1,
    size="1024x1024",
    quality="standard",
    response_format="url"
)

image_url = response.data[0].url
```

## 尺寸选项

| 尺寸 | 说明 |
|------|------|
| `256x256` | 小图 |
| `512x512` | 中图 |
| `1024x1024` | 常用方图 |
| `1024x1792` | 竖图 |
| `1792x1024` | 横图 |

## 支持的参数

| 参数 | 类型 | 说明 | 可选值 |
|------|------|------|--------|
| model | string | 生图模型 | `gpt-image-2`（默认）、`nano-banana-2` |
| prompt | string | 图片描述 | 最长 4000 字符 |
| n | int | 生成数量 | 1-4，默认 1 |
| size | string | 图片尺寸 | 见上方尺寸选项 |
| quality | string | 图片质量 | `standard`（默认）、`hd` |
| response_format | string | 返回格式 | `url`（默认）、`b64_json` |

## 返回格式

```json
{
  "created": 1234567890,
  "data": [
    {
      "url": "https://example.com/generated-image.png"
    }
  ]
}
```

## 适用场景

- 数据可视化（折线图、柱状图等）
- 产品图片生成
- 艺术风格转换
- 动漫/游戏角色设计

## ⚠️ 注意事项

1. **不要用 `/v1/images/edits`** - 该接口响应极慢，容易超时
2. **超时时间设置 120-180 秒** - GPT-Image-2 生成需要时间
3. **下载图片后及时保存** - 返回的 URL 有时效性

## 相关文档

- AI Hub API 文档：https://docs.codexzh.com/ai-hub-api/image-tutorial
- 模型列表：https://docs.codexzh.com/ai-hub-api/models-list