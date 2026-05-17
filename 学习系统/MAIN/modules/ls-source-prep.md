---
module: ls-source-prep
parent: ls-learning-flow
description: 源码准备指南——知识类型到权威实现的映射、下载命令、镜像替代方案
load_when: 阶段4步骤0（实施准备）时加载
depends: [ls-data-structure]
---

# 源码准备指南

> **强制约束：禁止删除 sources 目录下任何内容！**

---

## 源码目录结构

```
sources/
├── openjdk/
│   └── jdk-21/                          # Java 21 标准库源码 (与 Android libcore 对照学习)
├── kotlin/                              # Kotlin 完整官方生态（扁平化，不收敛到 kotlin/）
│   ├── kotlin/                          #   Kotlin 编译器 + 标准库
│   ├── kotlinx.coroutines/              #   协程库
│   ├── kotlinx-serialization/           #   官方序列化库 (JSON/Proto 等)
│   ├── kotlinx-datetime/               #   多平台日期时间库
│   ├── kotlinx-io/                     #   多平台 I/O 库
│   └── ktor/                           #   JetBrains 异步客户端/服务端框架
├── androidx/                            # Jetpack 全家桶 (Compose、Lifecycle、ViewModel、Room 等)
├── android/
│   └── android-15/                    # Android 15 (API 35) AOSP 平台源码
│       ├── art/                        #   Android Runtime (dex2oat/GC/JIT)
│       ├── frameworks/
│       │   ├── base/                   #   Java Framework 核心 (Activity/Service 等)
│       │   ├── native/                 #   Native Framework (SurfaceFlinger 等)
│       │   └── av/                     #   音视频框架 (AudioFlinger/MediaCodec)
│       ├── libcore/                    #   Android 定制 Java 核心库
│       ├── bionic/                     #   C 库 (libc/linker)
│       ├── system/core/                 #   系统核心守护进程 (init/servicemanager/adb)
│       ├── packages/apps/
│       │   ├── Settings/               #   系统设置应用
│       │   └── SystemUI -> frameworks/base/packages/SystemUI  # [符号链接]
│       ├── hardware/interfaces/        #   HAL 接口定义
│       └── external/                   #   AOSP 裁剪/定制版三方库
│           ├── skia/                   #   2D 图形渲染引擎
│           ├── conscrypt/              #   TLS/SSL 安全加密
│           ├── icu4c/                  #   Unicode + 国际化
│           ├── sqlite/                 #   SQLite 数据库引擎
│           ├── libpng/                 #   PNG 编解码
│           ├── libjpeg/                #   JPEG 编解码
│           └── okhttp/                 #   Android 内置 HTTP 栈 (AOSP 裁剪版)
├── android-thirdparty/                 # [按功能分类] Android 平台第三方知名库
│   ├── network/
│   │   ├── okhttp/                     #   Square 原版 OkHttp
│   │   └── retrofit/                    #   类型安全 HTTP 客户端
│   ├── image/
│   │   ├── glide/                      #   图片缓存与加载 (传统 View 体系首选)
│   │   └── coil/                       #   Kotlin 协程图片加载 (Compose 首选)
│   ├── di/
│   │   ├── hilt/                        #   Hilt (基于 Dagger 的 Android DI)
│   │   └── koin/                        #   Koin 轻量级 DI (运行时注入)
│   ├── database/
│   │   └── room -> ../../androidx/room #   [符号链接] Room 持久化库
│   ├── json/
│   │   ├── moshi/                       #   Moshi JSON 库
│   │   └── gson/                        #   Gson JSON 库
│   ├── event/
│   │   └── eventbus/                    #   EventBus 事件总线
│   ├── reactive/
│   │   ├── rxjava/                      #   RxJava 3
│   │   └── rxandroid/                    #   RxAndroid (Android 调度器)
│   ├── router/
│   │   └── arouter/                     #   ARouter (阿里路由框架)
│   ├── memory/
│   │   └── leakcanary/                  #   内存泄漏检测
│   └── animation/
│       └── lottie-android/              #   Lottie 动画渲染
├── algorithms-and-data-structures/     # 经典算法与数据结构实现集合
│   ├── TheAlgorithms-Java/             #   Java 版
│   └── TheAlgorithms-Kotlin/           #   Kotlin 版
└── android-tools/                      # 构建与编译工具源码
    ├── agp/                            #   Android Gradle Plugin (构建流程)
    ├── d8-r8/                          #   D8 Dexer + R8 Shrinker (编译与混淆)
    ├── ide-setup/                      #   预留：IDE 配置、项目模板等
    └── build-tools/                     #   预留：自定义脚本、构建工具指南等
```

> **符号链接说明**：
> - `SystemUI`：源码实际位于 `frameworks/base/packages/SystemUI`，在 `packages/apps/` 下建符号链接指向它，避免重复 clone
> - `room`：`androidx/room` 是 Room 的权威来源，`android-thirdparty/database/room` 符号链接指向它

---

## 知识类型 → 权威实现映射

**判断逻辑**：先执行 CLI：python3 learning.py knowledge get <id> 取 `category`；再用 `tags` 和 `subcategory` 细分。

| 知识类型 | 字段匹配 | 权威实现来源 | 目标存放路径 |
|---------|---------|------------|------------|
| **Java 语言/JVM 特性** | `language=java` | OpenJDK（HotSpot / JDK 类库） | `sources/openjdk/jdk-21/` |
| **Kotlin 语言/编译器** | `language=kotlin`，`framework=null`，`tags` 不含 `coroutine`/`serialization`/`datetime`/`io` | JetBrains/kotlin（编译器 + stdlib） | `sources/kotlin/kotlin/` |
| **Kotlin 协程** | `language=kotlin`，`tags` 含 `coroutine` | Kotlin/kotlinx.coroutines | `sources/kotlin/kotlinx.coroutines/` |
| **Kotlin 序列化** | `language=kotlin`，`tags` 含 `serialization` | Kotlin/kotlinx.serialization | `sources/kotlin/kotlinx-serialization/` |
| **Kotlin 日期时间** | `language=kotlin`，`tags` 含 `datetime`/`date`/`time` | Kotlin/kotlinx-datetime | `sources/kotlin/kotlinx-datetime/` |
| **Kotlin I/O** | `language=kotlin`，`tags` 含 `io`/`kotlin-io` | Kotlin/kotlinx-io | `sources/kotlin/kotlinx-io/` |
| **Ktor 网络框架** | `language=kotlin`，`framework=ktor` | Ktor | `sources/kotlin/ktor/` |
| **Android 系统框架（Java）** | `framework=android-framework`，涉及 Binder、AMS、WMS 等 | AOSP `platform/frameworks/base` | `sources/android/android-15/frameworks/base/` |
| **Android 系统框架（Native）** | `framework=android-framework`，涉及 SurfaceFlinger、InputFlinger 等 | AOSP `platform/frameworks/native` | `sources/android/android-15/frameworks/native/` |
| **Android 音视频框架** | `framework=android-framework`，涉及 MediaCodec、AudioFlinger 等 | AOSP `platform/frameworks/av` | `sources/android/android-15/frameworks/av/` |
| **Android ART/运行时** | `language=java` 或 `kotlin`，学习目标在 Android 设备上运行（volatile 实现、GC、JIT） | AOSP `platform/art` | `sources/android/android-15/art/` |
| **Android libcore** | Java 核心类库在 Android 上的定制实现（java.lang、java.util、java.io 等） | AOSP `platform/libcore` | `sources/android/android-15/libcore/` |
| **Android bionic** | Android C 库（libc、libm、linker 等底层） | AOSP `platform/bionic` | `sources/android/android-15/bionic/` |
| **Android 系统核心** | init、adb、logcat、servicemanager 等系统级底层 | AOSP `platform/system/core` | `sources/android/android-15/system/core/` |
| **Jetpack / Compose** | `framework` 含 `jetpack`/`compose` | AOSP `platform/frameworks/support` (androidx-main) | `sources/androidx/` |
| **Android 图形引擎** | View 体系、Canvas 绘制底层 | AOSP `platform/external/skia` | `sources/android/android-15/external/skia/` |
| **Android 网络库（平台内置）** | HttpURLConnection / HTTP 通信底层 | AOSP `platform/external/okhttp` | `sources/android/android-15/external/okhttp/` |
| **Android 安全库** | TLS/SSL 安全套接字实现 | AOSP `platform/external/conscrypt` | `sources/android/android-15/external/conscrypt/` |
| **OkHttp（Square 原版）** | `framework=okhttp`，需追源码 | Square/okhttp | `sources/android-thirdparty/network/okhttp/` |
| **Retrofit** | `framework=retrofit` | Square/retrofit | `sources/android-thirdparty/network/retrofit/` |
| **Glide** | `framework=glide` | bumptech/glide | `sources/android-thirdparty/image/glide/` |
| **Coil** | `framework=coil` | coil-kt/coil | `sources/android-thirdparty/image/coil/` |
| **Hilt / Dagger** | `framework=hilt` 或 `framework=dagger` | google/dagger | `sources/android-thirdparty/di/hilt/` |
| **Koin** | `framework=koin` | InsertKoinIO/koin | `sources/android-thirdparty/di/koin/` |
| **Moshi** | `framework=moshi` | square/moshi | `sources/android-thirdparty/json/moshi/` |
| **Gson** | `framework=gson` | google/gson | `sources/android-thirdparty/json/gson/` |
| **EventBus** | `framework=eventbus` | greenrobot/EventBus | `sources/android-thirdparty/event/eventbus/` |
| **RxJava / RxAndroid** | `framework=rxjava` 或 `framework=rxandroid` | ReactiveX/RxJava | `sources/android-thirdparty/reactive/rxjava/` |
| **ARouter** | `framework=arouter` | alibaba/ARouter | `sources/android-thirdparty/router/arouter/` |
| **LeakCanary** | `framework=leakcanary` | square/leakcanary | `sources/android-thirdparty/memory/leakcanary/` |
| **Lottie** | `framework=lottie` | airbnb/lottie-android | `sources/android-thirdparty/animation/lottie-android/` |
| **Room** | `framework=room` | androidx/room (在 androidx 仓库内) ⚠️ 有问题，待解决 | `sources/androidx/room/` → 符号链接 `sources/android-thirdparty/database/room` |
| **第三方库（非上述分类）** | `framework` 不为 null 且非 Android 框架、非 kotlinx 系列 | 该库 GitHub 仓库 | `sources/{lib}/` |
| **协议/标准** | `subcategory=协议` 或 `tags` 含 `protocol` | RFC / W3C / IEEE 规范 | `wiki/raw/articles/` |
| **数据结构类算法** | `category=数据结构`，实现存在于 JDK 或 Kotlin 标准库 | OpenJDK / JetBrains/kotlin | `sources/openjdk/jdk-21/` 或 `sources/kotlin/kotlin/` |
| **学科式算法** | `category=算法`，独立算法（如 Dijkstra、DP、A*） | 教材/论文权威实现 → **AI-User 协同确认** | `wiki/raw/articles/` 或 `sources/{算法库}/` |
| **设计模式（通用）** | `category=设计模式`，不限定框架 | GoF / refactoring.guru → **AI-User 协同确认** | `wiki/raw/articles/` |
| **设计模式（框架内）** | `category=设计模式`，`framework` 不为 null | 框架源码中找案例 | 复用框架仓库 |
| **构建工具/编译** | `subcategory=构建`/`编译` 或 `tags` 含 `gradle`/`dex`/`r8`/`d8` | AGP / R8 源码 | `sources/android-tools/agp/` 或 `sources/android-tools/d8-r8/` |

> **学科式算法与设计模式（通用）的处理规则**：
> - AI **不可**自行决定权威来源
> - AI 提供候选推荐（1-3 个），说明理由
> - 用户选定 → AI 执行下载 / 用户手动下载
> - 用户有自己信得过的来源 → 直接告知 AI，跳过推荐环节

---

## 实际验证的下载命令

> **硬规则**：每项给出精确可执行的命令，不模糊描述。
>
> **Windows 路径格式**：统一使用 `\\` 分隔符，适配 Git Bash / WSL / PowerShell。
>
> **分支 tag 从 `https://android.googlesource.com` 页面查找**，去掉 `android-` 前缀：
> `android-platform-15.0.0_r15` → `android15-platform-release`

---

### 语言生态核心

```bash
# OpenJDK 21 — Java 标准库源码
git clone https://github.com/openjdk/jdk.git --branch jdk-21.0.2-ga --single-branch D:\\2Study\\StudyNotes\\sources\\openjdk\\jdk-21

# Kotlin 编译器与标准库
git clone https://github.com/JetBrains/kotlin.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\kotlin\\kotlin

# kotlinx.coroutines — Kotlin 协程库
git clone https://github.com/Kotlin/kotlinx.coroutines.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\kotlin\\kotlinx.coroutines

# kotlinx.serialization — Kotlin 官方序列化库
git clone https://github.com/Kotlin/kotlinx.serialization.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\kotlin\\kotlinx-serialization

# kotlinx.datetime — Kotlin 多平台日期时间库
git clone https://github.com/Kotlin/kotlinx-datetime.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\kotlin\\kotlinx-datetime

# kotlinx-io — Kotlin 多平台 I/O 库
git clone https://github.com/Kotlin/kotlinx-io.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\kotlin\\kotlinx-io

# Ktor — JetBrains 异步客户端/服务端框架
git clone https://github.com/ktorio/ktor.git --branch main --single-branch D:\\2Study\\StudyNotes\\sources\\kotlin\\ktor
```

---

### Jetpack / Compose（独立于平台版本）

```bash
# frameworks/support — Jetpack 与 Compose 源码
git clone https://android.googlesource.com/platform/frameworks/support --branch androidx-main --single-branch D:\\2Study\\StudyNotes\\sources\\androidx
```

---

### Android 15 平台源码（AOSP）

```bash
# art — Android Runtime (dex2oat/GC/JIT)
git clone https://android.googlesource.com/platform/art --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\art

# frameworks/base — Java Framework 核心
git clone https://android.googlesource.com/platform/frameworks/base --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\frameworks\\base

# frameworks/native — Native Framework
git clone https://android.googlesource.com/platform/frameworks/native --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\frameworks\\native

# frameworks/av — 音视频框架
git clone https://android.googlesource.com/platform/frameworks/av --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\frameworks\\av

# libcore — Android 定制 Java 核心库
git clone https://android.googlesource.com/platform/libcore --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\libcore

# bionic — C 库
git clone https://android.googlesource.com/platform/bionic --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\bionic

# system/core — 系统核心守护进程
git clone https://android.googlesource.com/platform/system/core --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\system\\core

# packages/apps/Settings — 系统设置应用
git clone https://android.googlesource.com/platform/packages/apps/Settings --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\packages\\apps\\Settings

# hardware/interfaces — HAL 接口定义
git clone https://android.googlesource.com/platform/hardware/interfaces --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\hardware\\interfaces

# external/skia — 2D 图形引擎
git clone https://android.googlesource.com/platform/external/skia --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\external\\skia

# external/conscrypt — TLS/SSL 加密
git clone https://android.googlesource.com/platform/external/conscrypt --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\external\\conscrypt

# external/icu4c — 国际化
git clone https://android.googlesource.com/platform/external/icu4c --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\external\\icu4c

# external/sqlite — 数据库引擎
git clone https://android.googlesource.com/platform/external/sqlite --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\external\\sqlite

# external/libpng — PNG 编解码
git clone https://android.googlesource.com/platform/external/libpng --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\external\\libpng

# external/libjpeg — JPEG 编解码
git clone https://android.googlesource.com/platform/external/libjpeg --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\external\\libjpeg

# external/okhttp — Android 内置 HTTP 栈 (AOSP 裁剪版)
git clone https://android.googlesource.com/platform/external/okhttp --branch android15-platform-release --single-branch D:\\2Study\\StudyNotes\\sources\\android\\android-15\\external\\okhttp

# 创建 SystemUI 符号链接（避免重复 clone）
New-Item -ItemType SymbolicLink -Path "D:\\2Study\\StudyNotes\\sources\\android\\android-15\\packages\\apps\\SystemUI" -Target "D:\\2Study\\StudyNotes\\sources\\android\\android-15\\frameworks\\base\\packages\\SystemUI"
```

---

### Android 第三方知名库（android-thirdparty）

```bash
# ---------- 网络 ----------
# OkHttp (Square 原版)
git clone https://github.com/square/okhttp.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\network\\okhttp

# Retrofit — 类型安全 HTTP 客户端 (默认分支已改为 trunk)
git clone https://github.com/square/retrofit.git --branch trunk --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\network\\retrofit

# ---------- 图片加载 ----------
# Glide
git clone https://github.com/bumptech/glide.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\image\\glide

# Coil
git clone https://github.com/coil-kt/coil.git --branch main --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\image\\coil

# ---------- 依赖注入 ----------
# Dagger / Hilt
git clone https://github.com/google/dagger.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\di\\hilt

# Koin
git clone https://github.com/InsertKoinIO/koin.git --branch main --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\di\\koin

# ---------- JSON 解析 ----------
# Moshi
git clone https://github.com/square/moshi.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\json\\moshi

# Gson
git clone https://github.com/google/gson.git --branch main --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\json\\gson

# ---------- 事件通信 ----------
# EventBus
git clone https://github.com/greenrobot/EventBus.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\event\\eventbus

# ---------- 响应式编程 ----------
# RxJava 3
git clone https://github.com/ReactiveX/RxJava.git --branch 3.x --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\reactive\\rxjava

# RxAndroid
git clone https://github.com/ReactiveX/RxAndroid.git --branch 3.x --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\reactive\\rxandroid

# ---------- 路由 ----------
# ARouter
git clone https://github.com/alibaba/ARouter.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\router\\arouter

# ---------- 内存检测 ----------
# LeakCanary
git clone https://github.com/square/leakcanary.git --branch main --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\memory\\leakcanary

# ---------- 动画 ----------
# Lottie
git clone https://github.com/airbnb/lottie-android.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\animation\\lottie-android

# 创建 Room 符号链接（权威来源在 androidx 仓库）⚠️ 有问题，待解决
# New-Item -ItemType SymbolicLink -Path "D:\\2Study\\StudyNotes\\sources\\android-thirdparty\\database\\room" -Target "D:\\2Study\\StudyNotes\\sources\\androidx\\room"
```

---

### 算法与数据结构

```bash
# TheAlgorithms - Java 版
git clone https://github.com/TheAlgorithms/Java.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\algorithms-and-data-structures\\TheAlgorithms-Java

# TheAlgorithms - Kotlin 版
git clone https://github.com/TheAlgorithms/Kotlin.git --branch master --single-branch D:\\2Study\\StudyNotes\\sources\\algorithms-and-data-structures\\TheAlgorithms-Kotlin
```

---

### 构建与编译工具链

```bash
# Android Gradle Plugin 源码
git clone https://android.googlesource.com/platform/tools/base --branch main --single-branch D:\\2Study\\StudyNotes\\sources\\android-tools\\agp

# D8/R8 源码 (Dex 编译 + 混淆)
git clone https://r8.googlesource.com/r8 --branch main --single-branch D:\\2Study\\StudyNotes\\sources\\android-tools\\d8-r8
```

---

## AOSP 国内镜像

AOSP 的 `android.googlesource.com` 在国内无法直连，使用以下镜像替换 URL 中的 `{mirror}`：

| 镜像 | URL 前缀 |
|------|---------|
| 清华 TUNA（推荐） | `https://mirrors.tuna.tsinghua.edu.cn/git/AOSP` |
| 中科大 USTC | `https://mirrors.ustc.edu.cn/aosp` |

**替换示例**：
```
# 原命令
git clone https://android.googlesource.com/platform/art --branch android15-platform-release ...

# 替换为
git clone https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/platform/art --branch android15-platform-release ...
```

---

## git 不可用时的替代方案

镜像和 GitHub 都连不上时，浏览器直接下载 tar.gz，解压到 sources/ 即可。与 `git clone` 内容完全一致，体积更小。

```
# 浏览器打开以下 URL 直接下载（无需 git）：
https://android.googlesource.com/platform/art/+archive/refs/tags/android-platform-15.0.0_r15.tar.gz
https://android.googlesource.com/platform/frameworks/base/+archive/refs/tags/android-platform-15.0.0_r15.tar.gz
```

---

## 按需下载策略

Android 源码由 200+ 独立模块组成。**不要下载全量 AOSP（~60GB）**，按学习目标单独下载对应模块。

| 学习目标 | AOSP 模块 | 大概体积 |
|---------|-----------|---------|
| volatile/GC/JIT 在手机上的实现 | `platform/art` | ~80MB |
| Activity/Service/Binder 等 Java 系统服务 | `platform/frameworks/base` | ~2GB |
| SurfaceFlinger/InputFlinger 等 C++ 底层 | `platform/frameworks/native` | ~500MB |
| MediaCodec/AudioFlinger 音视频 | `platform/frameworks/av` | ~300MB |
| java.lang/java.util 等 Android 定制类库 | `platform/libcore` | ~200MB |
| libc/linker 等底层 C 库 | `platform/bionic` | ~100MB |
| init/adb/logcat 等系统底层 | `platform/system/core` | ~300MB |
| View 体系/Canvas 绘制底层 | `platform/external/skia` | ~200MB |
| HTTP 通信底层 | `platform/external/okhttp` | ~50MB |
| Jetpack/Lifecycle/Compose UI | `platform/frameworks/support` (androidx-main) | ~5GB |
| 系统设置应用如何调用系统服务 | `platform/packages/apps/Settings` | ~300MB |
| 状态栏/通知面板 UI 实现 | SystemUI（`frameworks/base/packages/SystemUI`） | ~200MB |
| 构建系统 / Gradle Plugin | `platform/tools/base` | ~1GB |
| Dex 编译与 R8 混淆 | `r8.googlesource.com/r8` | ~500MB |
