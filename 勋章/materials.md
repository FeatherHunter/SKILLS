# SVG材质技法库

> 可直接使用的SVG代码模式。每个材质只描述视觉特征，不绑定任何事件类型。
> AI根据事件解构的结果自由选择、组合、修改这些材质。
> 调整渐变角度、色相、透明度即可产生完全不同的效果。

---

## 金属渐变

5色交替渐变模拟金属反光条带。改变色相可得到金、银、铜、玫瑰金等变体。

```xml
<defs>
  <linearGradient id="metal" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#F5E6A3"/>
    <stop offset="30%" stop-color="#C9A84C"/>
    <stop offset="50%" stop-color="#F5E6A3"/>
    <stop offset="70%" stop-color="#8B6914"/>
    <stop offset="100%" stop-color="#C9A84C"/>
  </linearGradient>
</defs>
```

变体思路：替换色相→银（#E8E8E8/#B0B0B0/#D8D8D8/#909090/#C0C0C0）、铜（#D4A574/#B87333/#CD7F32/#8B4513/#A0522D）、玫瑰金（#F5C6C6/#E8A0A0/#F5C6C6/#B76E6E/#D49090）。

---

## 玻璃/水晶

高透明度白色渐变 + 模糊光晕。轻盈、通透。

```xml
<defs>
  <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="rgba(255,255,255,0.9)"/>
    <stop offset="30%" stop-color="rgba(255,255,255,0.3)"/>
    <stop offset="60%" stop-color="rgba(200,220,255,0.2)"/>
    <stop offset="100%" stop-color="rgba(255,255,255,0.6)"/>
  </linearGradient>
  <filter id="glass-glow">
    <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
```

---

## 柔光投影

通用阴影，适用于任何需要立体感的元素。

```xml
<defs>
  <filter id="soft-shadow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur"/>
    <feOffset dx="0" dy="3" result="offset"/>
    <feFlood flood-color="#000" flood-opacity="0.3" result="color"/>
    <feComposite in="color" in2="offset" operator="in" result="shadow"/>
    <feMerge><feMergeNode in="shadow"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
```

变体：调整flood-opacity（0.1淡影→0.5重影）、dx/dy（偏移方向）、stdDeviation（模糊半径）。

---

## 径向辉光

从中心向外衰减的光晕。替换颜色即可得到任意色调的辉光。

```xml
<defs>
  <radialGradient id="glow" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#FFD700" stop-opacity="0.6"/>
    <stop offset="50%" stop-color="#FFD700" stop-opacity="0.2"/>
    <stop offset="100%" stop-color="#FFD700" stop-opacity="0"/>
  </radialGradient>
  <filter id="glow-blur">
    <feGaussianBlur in="SourceGraphic" stdDeviation="8"/>
  </filter>
</defs>
```

变体：蓝辉（#87CEEB/#4682B4/#191970）、紫辉（#DDA0DD/#9370DB/#4B0082）、绿辉（#90EE90/#3CB371/#006400）。

---

## 夜空/星云

深色多层渐变，模拟深邃星空。配合小圆点做星星。

```xml
<defs>
  <radialGradient id="night-sky" cx="50%" cy="40%" r="60%">
    <stop offset="0%" stop-color="#1a1a3e"/>
    <stop offset="50%" stop-color="#0d0d2b"/>
    <stop offset="100%" stop-color="#050510"/>
  </radialGradient>
  <filter id="star-glow">
    <feGaussianBlur in="SourceGraphic" stdDeviation="1.5"/>
  </filter>
</defs>
```

---

## 纸张纹理

噪点模拟纸张纤维。配合暖白底色。

```xml
<defs>
  <filter id="paper-texture">
    <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="5" result="noise"/>
    <feDiffuseLighting in="noise" lighting-color="#FDF8F0" surfaceScale="2">
      <feDistantLight azimuth="45" elevation="60"/>
    </feDiffuseLighting>
  </filter>
</defs>
```

---

## 木纹纹理

水平条纹模拟木纹方向。用multiply混合到底色上。

```xml
<defs>
  <filter id="wood-texture">
    <feTurbulence type="fractalNoise" baseFrequency="0.02 0.2" numOctaves="4" result="noise"/>
    <feColorMatrix type="saturate" values="0.1" in="noise" result="desaturated"/>
    <feBlend in="SourceGraphic" in2="desaturated" mode="multiply"/>
  </filter>
</defs>
```

变体：调整baseFrequency的第一个值控制纹路密度，第二个值控制纹路方向（0.2=水平，2=垂直）。

---

## 木板桌面（完整背景）

木纹底色渐变 + turbulence纹理滤镜组合，直接作为背景使用。

```xml
<defs>
  <linearGradient id="plank-base" x1="0" y1="0" x2="0.2" y2="1">
    <stop offset="0%" stop-color="#6B4226"/>
    <stop offset="30%" stop-color="#5A3520"/>
    <stop offset="60%" stop-color="#7A4E2E"/>
    <stop offset="100%" stop-color="#4A2E18"/>
  </linearGradient>
  <filter id="wood-grain">
    <feTurbulence type="fractalNoise" baseFrequency="0.015 0.15" numOctaves="5" result="noise"/>
    <feColorMatrix type="saturate" values="0.08" in="noise" result="desat"/>
    <feComponentTransfer in="desat" result="wood">
      <feFuncR type="linear" slope="0.6" intercept="0.2"/>
      <feFuncG type="linear" slope="0.4" intercept="0.12"/>
      <feFuncB type="linear" slope="0.2" intercept="0.05"/>
    </feComponentTransfer>
    <feBlend in="SourceGraphic" in2="wood" mode="multiply"/>
  </filter>
</defs>
<!-- 用法：<rect fill="url(#plank-base)" filter="url(#wood-grain)"/> -->
```

---

## 宝石/水晶多面体

多面体宝石不是单个形状+单个渐变。用多个polygon叠加，每个面用不同渐变模拟不同角度受光。

```xml
<defs>
  <linearGradient id="gem-top" x1="0.3" y1="0" x2="0.7" y2="0.8">
    <stop offset="0%" stop-color="rgba(220,210,255,0.85)"/>
    <stop offset="35%" stop-color="rgba(160,150,255,0.3)"/>
    <stop offset="100%" stop-color="rgba(100,80,200,0)"/>
  </linearGradient>
  <linearGradient id="gem-body" x1="0.3" y1="0" x2="0.7" y2="1">
    <stop offset="0%" stop-color="#8B7FFF"/>
    <stop offset="50%" stop-color="#5B4FCF"/>
    <stop offset="100%" stop-color="#3D2F9F"/>
  </linearGradient>
  <radialGradient id="gem-core" cx="38%" cy="32%" r="35%">
    <stop offset="0%" stop-color="rgba(200,190,255,0.5)"/>
    <stop offset="100%" stop-color="rgba(80,60,180,0)"/>
  </radialGradient>
</defs>
<!-- 用法：菱形宝石示例 -->
<!-- <polygon points="0,-50 30,0 0,50 -30,0" fill="url(#gem-body)"/>          主体 -->
<!-- <polygon points="0,-50 30,0 0,-10 -30,0" fill="url(#gem-top)" opacity="0.7"/> 上切面高光 -->
<!-- <polygon points="-30,0 0,-10 0,50" fill="rgba(40,30,100,0.35)"/>         左面暗 -->
<!-- <polygon points="30,0 0,-10 0,50" fill="rgba(60,50,130,0.2)"/>           右面稍亮 -->
<!-- <circle cx="-5" cy="-10" r="15" fill="url(#gem-core)"/>                  核心光 -->
```

要点：每个切面单独一个polygon，用不同透明度和色相模拟光线在不同角度的反射。高光在左上，暗面在右下。

---

## 火焰渐变

从下到上的暖色渐变。底部深红、顶部亮金半透明。

```xml
<defs>
  <linearGradient id="flame" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0%" stop-color="#FF4500"/>
    <stop offset="40%" stop-color="#FF6347"/>
    <stop offset="70%" stop-color="#FFA500"/>
    <stop offset="100%" stop-color="#FFD700" stop-opacity="0.8"/>
  </linearGradient>
  <filter id="flame-blur">
    <feGaussianBlur in="SourceGraphic" stdDeviation="3"/>
  </filter>
</defs>
```

---

## 大理石纹理

仿大理石纹路。噪点+漫反射光照，高雅冷峻。

```xml
<defs>
  <filter id="marble">
    <feTurbulence type="turbulence" baseFrequency="0.01 0.03" numOctaves="5" result="noise"/>
    <feColorMatrix type="saturate" values="0.05" in="noise" result="desat"/>
    <feDiffuseLighting in="desat" lighting-color="#F0EDE8" surfaceScale="3">
      <feDistantLight azimuth="135" elevation="55"/>
    </feDiffuseLighting>
  </filter>
</defs>
```

变体：调整baseFrequency可得到不同纹路密度。lighting-color可改为冷白（#E8EEF2）或暖米（#F5EFE0）。

---

## 液态水银

流动的液态金属感。高反射、有机曲线。

```xml
<defs>
  <linearGradient id="mercury" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#E0E0E0"/>
    <stop offset="20%" stop-color="#FFFFFF"/>
    <stop offset="40%" stop-color="#A0A0A0"/>
    <stop offset="60%" stop-color="#E0E0E0"/>
    <stop offset="80%" stop-color="#808080"/>
    <stop offset="100%" stop-color="#C0C0C0"/>
  </linearGradient>
  <filter id="mercury-glow">
    <feGaussianBlur in="SourceGraphic" stdDeviation="1" result="blur"/>
    <feSpecularLighting in="blur" surfaceScale="5" specularConstant="1" specularExponent="20" result="spec">
      <fePointLight x="200" y="100" z="200"/>
    </feSpecularLighting>
    <feComposite in="SourceGraphic" in2="spec" operator="arithmetic" k1="0" k2="1" k3="1" k4="0"/>
  </filter>
</defs>
```

---

## 霓虹发光

高饱和+强光晕。边缘发光效果，醒目锐利。

```xml
<defs>
  <filter id="neon-glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur1"/>
    <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur2"/>
    <feMerge>
      <feMergeNode in="blur1"/>
      <feMergeNode in="blur1"/>
      <feMergeNode in="blur2"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
</defs>
```

使用时描边不用填充，stroke用高饱和色（如#FF00FF、#00FFFF、#39FF14），配合深色背景。

---

## 织物/丝绸纹理

细腻的交叉纹理，模拟织物表面。

```xml
<defs>
  <filter id="fabric">
    <feTurbulence type="turbulence" baseFrequency="0.1 0.08" numOctaves="3" result="noise"/>
    <feColorMatrix type="saturate" values="0" in="noise" result="gray"/>
    <feBlend in="SourceGraphic" in2="gray" mode="soft-light"/>
  </filter>
</defs>
```

---

## 雾气/朦胧

半透明渐变叠加，营造朦胧、梦幻氛围。

```xml
<defs>
  <linearGradient id="fog" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0%" stop-color="#fff" stop-opacity="0.7"/>
    <stop offset="40%" stop-color="#fff" stop-opacity="0.3"/>
    <stop offset="100%" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <filter id="fog-blur">
    <feGaussianBlur in="SourceGraphic" stdDeviation="12"/>
  </filter>
</defs>
```

---

## 极光/光幕

多色渐变模拟极光的流动色彩。背景装饰用。

```xml
<defs>
  <linearGradient id="aurora" x1="0" y1="1" x2="1" y2="0">
    <stop offset="0%" stop-color="#00FF87"/>
    <stop offset="25%" stop-color="#60EFFF"/>
    <stop offset="50%" stop-color="#A855F7"/>
    <stop offset="75%" stop-color="#FF6EC7"/>
    <stop offset="100%" stop-color="#00FF87"/>
  </linearGradient>
  <filter id="aurora-blur">
    <feGaussianBlur in="SourceGraphic" stdDeviation="15"/>
  </filter>
</defs>
```

---

## 锈蚀/风化

粗糙的表面纹理，模拟老旧金属或石面。

```xml
<defs>
  <filter id="rust">
    <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="6" result="noise"/>
    <feColorMatrix type="matrix" in="noise"
      values="0.5 0 0 0 0.3
              0.3 0 0 0 0.15
              0.1 0 0 0 0.05
              0 0 0 0 1" result="rust-color"/>
    <feBlend in="SourceGraphic" in2="rust-color" mode="multiply"/>
  </filter>
</defs>
```

---

## 宝石切面

多面体反光效果，模拟宝石的棱角折射。

```xml
<defs>
  <linearGradient id="gem" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#E0F7FA"/>
    <stop offset="20%" stop-color="#00BCD4"/>
    <stop offset="35%" stop-color="#E0F7FA"/>
    <stop offset="50%" stop-color="#006064"/>
    <stop offset="65%" stop-color="#4DD0E1"/>
    <stop offset="80%" stop-color="#00838F"/>
    <stop offset="100%" stop-color="#B2EBF2"/>
  </linearGradient>
</defs>
```

变体：替换色相→红宝石（#FF1744/#B71C1C/#E57373）、祖母绿（#00C853/#1B5E20/#69F0AE）、蓝宝石（#2979FF/#0D47A1/#82B1FF）。

---

## 雨滴/水珠

透明圆点叠加模糊，模拟水滴凝结。

```xml
<defs>
  <filter id="droplet">
    <feGaussianBlur in="SourceGraphic" stdDeviation="0.5"/>
  </filter>
  <radialGradient id="droplet-shade" cx="35%" cy="35%" r="50%">
    <stop offset="0%" stop-color="#fff" stop-opacity="0.8"/>
    <stop offset="50%" stop-color="rgba(200,220,255,0.4)"/>
    <stop offset="100%" stop-color="rgba(100,150,200,0.2)"/>
  </radialGradient>
</defs>
```

---

## 沙粒/沙漠

细腻颗粒感，温暖干燥的表面。

```xml
<defs>
  <filter id="sand">
    <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" result="noise"/>
    <feColorMatrix type="saturate" values="0.2" in="noise" result="desat"/>
    <feBlend in="SourceGraphic" in2="desat" mode="overlay"/>
  </filter>
</defs>
```

---

## 蜂蜜/琥珀

浓稠的半透明暖色，有流动感和深度。

```xml
<defs>
  <linearGradient id="amber" x1="0" y1="0" x2="0.5" y2="1">
    <stop offset="0%" stop-color="#FFD54F" stop-opacity="0.9"/>
    <stop offset="40%" stop-color="#FF8F00" stop-opacity="0.7"/>
    <stop offset="70%" stop-color="#E65100" stop-opacity="0.8"/>
    <stop offset="100%" stop-color="#BF360C" stop-opacity="0.9"/>
  </linearGradient>
  <filter id="amber-glow">
    <feGaussianBlur in="SourceGraphic" stdDeviation="2"/>
  </filter>
</defs>
```

---

## 电弧/闪电

锐利的发光线条，能量感十足。用描边+多层模糊实现。

```xml
<defs>
  <filter id="electric" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur1"/>
    <feGaussianBlur in="SourceGraphic" stdDeviation="1" result="blur2"/>
    <feMerge>
      <feMergeNode in="blur1"/>
      <feMergeNode in="blur2"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
</defs>
```

使用时用描边画锯齿路径，stroke="#BBDDFF"或"#FFFFFF"，配合深蓝/黑色背景。

---

## 光线/光芒

从中心向外放射的光线。用重复的三角形+旋转实现。

```xml
<defs>
  <linearGradient id="ray-fade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#FFD700" stop-opacity="0.8"/>
    <stop offset="100%" stop-color="#FFD700" stop-opacity="0"/>
  </linearGradient>
</defs>
<!-- 用法：细长三角形从中心向外放射，group做缓慢旋转 -->
```

---

## 冰霜结晶

冰冷的半透明纹理，带细微裂纹。

```xml
<defs>
  <filter id="frost">
    <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="5" seed="2" result="noise"/>
    <feColorMatrix type="saturate" values="0" in="noise" result="gray"/>
    <feComponentTransfer in="gray" result="crack">
      <feFuncR type="discrete" tableValues="0.9 0.95 1 0.85 0.92"/>
      <feFuncG type="discrete" tableValues="0.93 0.97 1 0.88 0.95"/>
      <feFuncB type="discrete" tableValues="0.96 0.99 1 0.92 0.98"/>
    </feComponentTransfer>
    <feBlend in="SourceGraphic" in2="crack" mode="screen"/>
  </filter>
</defs>
```

---

## 渐变色场

多色大面积渐变，用于背景或装饰色块。色相由事件解构决定。

```xml
<defs>
  <linearGradient id="color-field" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#667eea"/>
    <stop offset="50%" stop-color="#764ba2"/>
    <stop offset="100%" stop-color="#f093fb"/>
  </linearGradient>
</defs>
```

变体：替换三个色相即可得到完全不同的氛围。暖场（#f093fb/#f5576c/#ff9a9e）、冷场（#667eea/#764ba2/#43e97b）、深场（#0c0c1d/#1a1a3e/#2d1b69）。

---

## 粒子/尘埃

用多个小圆点+不同透明度+缓慢漂移动画，营造漂浮微粒效果。

```xml
<defs>
  <filter id="particle-soft">
    <feGaussianBlur in="SourceGraphic" stdDeviation="0.8"/>
  </filter>
</defs>
<!-- 用法：多个小circle，r=1~3，opacity=0.2~0.6，各带不同的缓慢漂移动画 -->
```
