# luts/

电影级 LUT(Look-Up Table)调色预设。

## 常用免费 LUT 来源

| 来源 | 链接 | 特点 |
|---|---|---|
| fixthephoto | https://fixthephoto.com/free-luts.html | 100+ 免费 LUT |
| rocketstock | https://www.rocketstock.com/free-luts-for-premiere-pro/ | 专业级 |
| luts.io | https://luts.io/ | 综合资源 |
| smallhd | https://smallhd.com/community/luts | 电影风 |
| luts.beyondloomery | (GitHub) | 开源 |

## 推荐下载(起步三件套)

1. **Kodak 2383** —— 经典胶片色
2. **Teal & Orange** —— 电影标配
3. **Fuji F125** —— 温暖复古

## 推荐下载(进阶)

- **Vintage / Film** —— 复古风
- **Black & White** —— 黑白
- **Cinematic Blockbuster** —— 大片感
- **Wedding** —— 婚礼暖色

## 安装方法

下载后解压,把 `.cube` 文件复制到这里:

```bash
cp ~/Downloads/LUTs/cinematic.cube /智剪工坊/assets/luts/
```

## 调用方法

```bash
python ../scripts/color_lut.py --input in.mp4 --lut luts/cinematic.cube --out out.mp4
```

(待实现 `color_lut.py` 子技能)

## 常用 LUT 列表(待添加)

- [ ] cinematic.cube
- [ ] teal_orange.cube
- [ ] vintage.cube
- [ ] kodak_2383.cube
- [ ] fuji_f125.cube
- [ ] bw_classic.cube

## 当前状态

🚧 **空目录** —— 需要下载 LUT 后放入。