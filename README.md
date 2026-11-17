# Package_Manager

把 [openwrt_package](https://github.com/MinimaxFlora/openwrt_package) 里的插件编译成
**apk**，再用 [makeself](https://github.com/megastep/makeself) 打包成自解压的 `.run`
安装器，方便在 iStoreOS / OpenWrt 25.12+ 这类 apk 系统上直接刷入。

- 只产出 apk，不产出 ipk
- 编译使用 openwrt_package 同款 SDK 工作流（`MinimaxFlora/gh-action-sdk`）
- **Release 里只有 `.run`**，每个分组一个，里面已经包含该分组需要的全部 apk

## 工作原理

```
Package_Manager workflow
  1. 读取选择的分组 -> 从 openwrt_package 动态解析出构建目标列表
  2. 拉取 openwrt_package 作为 SDK 的 feed，编译出 .apk
  3. 收集本次分组的所有 .apk，并校验每个构建目标都真的产出了包
  4. makeself 打包成 <分组>-<架构>-<版本>.run（附 .sha256 和 manifest）
  5. 只把 .run 按架构发布到本仓库 Release（tag: apk-<架构>）
```

设备上执行 `.run` 时，makeself 会把内容解压到临时目录并运行内置的 `install.sh`，
最终效果等同于：

```sh
apk add --allow-untrusted ./*.apk
```

因为包是本地 SDK 构建、没有签名，所以必须带 `--allow-untrusted`。

## 目录结构

```
.github/workflows/build-apk-run.yml   编译 + 打包 + 发布工作流
tools/groups.json                     插件分组定义（分组 -> 构建目标）
tools/resolve_group.py                把分组解析成 openwrt_package 的构建目标
tools/check-artifacts.py              校验所选目标是否都产出了 apk（SDK 开了 IGNORE_ERRORS，靠这步兜底）
tools/build_run.py                    用 makeself 把 apk 打包成 .run
tools/install.sh.in                   .run 内嵌的安装脚本模板
```

## 使用方法

1. 打开仓库的 **Actions** 页面，选择 **Build APK Run Installers**。
2. 点击 **Run workflow**，选择插件分组、目标架构。
   - 版本留空会使用 `downloads.openwrt.org` 上最新的 apk 稳定版（25.12.x）。
   - 只选一个分组时，只会编译该分组需要的插件，速度快很多。
3. 构建完成后，进入 **Releases**，下载 `apk-<架构>` 里对应的 `.run`
   （同名字的 `.sha256` 用来校验下载完整性）。
4. 把 `.run` 上传到路由器（scp、iStoreOS 文件管理、U 盘等均可），用 root 执行：

```sh
sh theme-aurora-x86_64-25.12.6.run
```

需要单个 apk 而不是整包安装时，直接从 `.run` 里解出来即可（同样需要 root）：

```sh
sh theme-aurora-x86_64-25.12.6.run --target /tmp/theme-aurora --noexec
ls /tmp/theme-aurora/*.apk
```

## 分组列表

分组定义在 `tools/groups.json`，工作流下拉选项与之完全对应（`label` 必须和下拉里的
字符串一模一样，否则 `resolve_group.py` 会报未知分组）。`.run` 文件名用 `slug`。
`resolve_group.py` 还会把每个目标对着 openwrt_package 的 `tools/list-packages.py`
校验一遍，写错名字会直接报错、不会带着错误目标跑到 SDK 阶段。

| 分组 | 文件名前缀 | 编译目标 |
| :-- | :-- | :-- |
| Argon 主题 | `theme-argon` | luci-theme-argon, luci-app-argon-config |
| Vantage 主题 | `theme-vantage` | luci-theme-vantage, luci-app-vantage |
| Aurora 主题 | `theme-aurora` | luci-theme-aurora, luci-app-aurora-config |
| Design 主题 | `theme-design` | luci-theme-design |
| Shadcn 主题 | `theme-shadcn` | luci-theme-shadcn |
| Fluent 主题 | `theme-fluent` | luci-theme-fluent, luci-mod-fluentdashboard |
| Fluent Lite 主题 | `theme-fluent-lite` | luci-theme-fluent-lite |
| Mosdns DNS 转换器 | `mosdns` | mosdns, luci-app-mosdns, v2ray-geodata, geo2txt |
| OpenClash 代理插件 | `openclash` | luci-app-openclash |
| HomeProxy 代理插件 | `homeproxy` | luci-app-homeproxy |
| PassWall 代理插件 | `passwall` | luci-app-passwall, chinadns-ng, dns2socks, ipt2socks, microsocks, tcping, xray-core, xray-plugin, sing-box, hysteria, naiveproxy, geoview, shadowsocks-rust, shadowsocksr-libev, shadow-tls, simple-obfs, v2ray-geodata, v2ray-plugin |
| PassWall2 代理插件 | `passwall2` | luci-app-passwall2, chinadns-ng, tcping, xray-core, xray-plugin, sing-box, geoview, shadowsocks-rust, shadowsocksr-libev, simple-obfs, v2ray-geodata, v2ray-plugin |
| Nikki 代理插件（nikki + mihomo 内核） | `nikki` | nikki, mihomo-meta, luci-app-nikki |
| DiskMan 磁盘管理工具 | `diskman` | luci-app-diskman |
| MentoHUST 认证 | `mentohust` | luci-app-mentohust, mentohust |
| Quickfile 文件管理 | `quickfile` | luci-app-quickfile, quickfile |
| RamFree 内存清理 | `ramfree` | luci-app-ramfree |
| Bandix-Plus 网络流量监控 | `bandix-plus` | luci-app-bandix-plus, bandix-plus |
| OpenList 网盘聚合工具 | `openlist` | luci-app-openlist2, openlist2 |
| AirConnect 音频服务 | `airconnect` | luci-app-airconnect, airconnect |
| Autocore 硬件信息 | `autocore` | autocore |
| Socat 端口转发 | `socat` | luci-app-socat |
| AdGuardHome 广告拦截 | `adguardhome` | luci-app-adguardhome |
| Geo 数据工具 | `geo-tools` | geoview, geo2txt |

`openwrt_package` 新增插件后，在 `tools/groups.json` 里加一条分组（`key` / `label` /
`slug` / `targets`），并在工作流下拉选项里加同名 `label` 即可。

## 本地打包

已经有一批 apk 时，可以单独生成 `.run`：

```sh
git clone --depth 1 https://github.com/megastep/makeself.git /tmp/makeself

python3 tools/build_run.py \
  --apk-dir ./apk \
  --out-dir ./out \
  --slug theme-aurora \
  --label "Aurora 主题" \
  --arch x86_64 \
  --version 25.12.6 \
  --makeself /tmp/makeself/makeself.sh
```

默认只在 `out/` 里生成 `.run` + `.sha256` + `.manifest.txt`；想让原始 apk 也留一份，
再加 `--copy-apks`。

检查分组会解析出哪些构建目标：

```sh
git clone --depth 1 https://github.com/MinimaxFlora/openwrt_package /tmp/openwrt_package
python3 tools/resolve_group.py --src /tmp/openwrt_package --label "Aurora 主题"
```

校验产物（CI 里同款）：

```sh
python3 tools/check-artifacts.py \
  --lock /tmp/openwrt_package/packages.lock.json \
  --apk-dir ./release \
  --targets "luci-theme-aurora luci-app-aurora-config"
```

## 注意事项

- `.run` 需要 root 权限，脚本里用了 makeself 的 `--needroot`。
- 目标系统需要 `apk`；OpenWrt 24.10 及更早版本使用 opkg，请改用 ipk。
- Fluent 主题与 Fluent Lite 主题互斥，只能选其中一个分组安装。
- 分组里的 LuCI 包通常是 `noarch`，可以跨架构安装；带二进制的插件必须匹配架构。
- `sing-box` 构建目标会同时编出 `sing-box` 和 `sing-box-tiny`（后者 `PROVIDES sing-box`、两者 conflicts），打包时只保留 `sing-box`，`sing-box-tiny` 会被自动丢掉。
- 安装时会从固件现有软件源补齐外部依赖（如 `luci-base`），请确保设备能访问软件源。
- 代理插件分组已经把该插件自己需要的内核/依赖（xray、sing-box、hysteria 等）一起打进去了，不用另外再装内核。
- PassWall、PassWall2、Nikki、HomeProxy、OpenClash 之间会抢端口和配置，一台设备只选一个。
- 多个代理/主题分组同时装到一台设备上可能在运行期互相抢占端口，按分组单独刷入更稳。
- SDK 侧开了 `IGNORE_ERRORS`，单个包编译失败不会当场中断；工作流的 `check-artifacts.py` 兜底，所选分组只要有一个构建目标没产出 apk 就判定失败。
- 构建产物未签名，安装时统一使用 `--allow-untrusted`。
- Release 的 tag 是 `apk-<架构>`，多次运行会往同一个 Release 里累加不同分组/版本的 `.run`，下载时以文件名里的分组/版本为准。
