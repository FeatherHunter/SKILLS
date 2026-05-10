# chatgpt-image2 - 图片生成技能

## 简介

基于 AI Hub API 的 GPT-Image-2 模型，支持基础生图和参考图生成（垫图）。

## 配置

- **API 地址**：https://api.xbai.top/v1
- **API Key**：sk-C2fSyNPHTzeqIzu1TrIHWyxA8GOq0acjerGOdsNDyz6gORxr
- **模型**：gpt-image-2（参考图生成）、nano-banana-2（基础生图）

## 支持功能

1. **基础生图**：根据提示词生成图片
2. **参考图生成**：使用 /v1/images/edits 接口，上传 1-2 张参考图，通过提示词让 GPT-Image-2 生成新图片

## 工具调用

使用 `image_generate` 工具时配置：

```
model: gpt-image-2
prompt: <描述>
size: <尺寸>
quality: standard | hd
outputFormat: url | b64_json
```

## 尺寸选项

| 尺寸 | 说明 |
|------|------|
| 256x256 | 小图 |
| 512x512 | 中图 |
| 1024x1024 | 常用方图 |
| 1024x1792 | 竖图 |
| 1792x1024 | 横图 |

## 参考图生成（垫图）

使用 image_generate 的 image 参数上传 1-2 张参考图，提示词中用"图1""图2"指代。

示例提示词：
- "图1 的模特穿上图2 的外套"
- "保留图1的场景，换成图2的天空"
- "图1 的猫咪戴上图2 的帽子"

## 快速开始

### 基础生图示例

```python
from openai import OpenAI
import requests
from pathlib import Path

client = OpenAI(
    api_key="sk-C2fSyNPHTzeqIzu1TrIHWyxA8GOq0acjerGOdsNDyz6gORxr",
    base_url="https://api.xbai.top/v1"
)

response = client.images.generate(
    model="gpt-image-2",
    prompt="一只可爱的橘猫在阳光下打盹，水彩画风格",
    n=1,
    size="1024x1024",
    quality="standard",
    response_format="url"
)

image_url = response.data[0].url
print(f"图片地址：{image_url}")
```

### 参考图生成示例

```python
import requests
from pathlib import Path

url = "https://api.xbai.top/v1/images/edits"

with open("image1.jpg", "rb") as f1, open("image2.jpg", "rb") as f2:
    response = requests.post(
        url,
        headers={"Authorization": "Bearer sk-C2fSyNPHTzeqIzu1TrIHWyxA8GOq0acjerGOdsNDyz6gORxr"},
        files=[
            ("image", ("image1.jpg", f1, "image/jpeg")),
            ("image", ("image2.jpg", f2, "image/jpeg"))
        ],
        data={
            "model": "gpt-image-2",
            "prompt": "图1 的模特穿上图2 的外套"
        }
    )

result = response.json()
image_url = result["data"][0]["url"]
print(f"图片地址：{image_url}")

# 下载保存
img_data = requests.get(image_url).content
Path("output.png").write_bytes(img_data)
```

## curl 示例

### 基础生图

```bash
curl https://api.xbai.top/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-C2fSyNPHTzeqIzu1TrIHWyxA8GOq0acjerGOdsNDyz6gORxr" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "一只可爱的橘猫在阳光下打盹，水彩画风格",
    "n": 1,
    "size": "1024x1024",
    "quality": "standard",
    "response_format": "url"
  }'
```

### 参考图生成

```bash
curl --request POST \
  --url https://api.xbai.top/v1/images/edits \
  --header "Authorization: Bearer sk-C2fSyNPHTzeqIzu1TrIHWyxA8GOq0acjerGOdsNDyz6gORxr" \
  --form "image=@image1.jpg" \
  --form "image=@image2.jpg" \
  --form "model=gpt-image-2" \
  --form "prompt=图1 的模特穿上图2 的外套"
```

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

或 Base64 格式（response_format="b64_json"）：

```json
{
  "data": [
    {
      "b64_json": "<base64编码的图片数据>"
    }
  ]
}
```

## 适用场景

- 产品图片生成
- 模特/服装试穿效果
- 场景合成
- 艺术风格转换
- 动漫/游戏角色设计

## 相关文档

- AI Hub API 文档：https://docs.codexzh.com/ai-hub-api/image-tutorial
- 模型列表：https://docs.codexzh.com/ai-hub-api/models-list