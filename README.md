# Package_Manager

把 [openwrt_package](https://github.com/MinimaxFlora/openwrt_package) 里的插件编译成
**apk**，再用 [makeself](https://github.com/megastep/makeself) 打包成自解压的 `.run`
安装器，方便在 iStoreOS / OpenWrt 25.12+ 这类 apk 系统上直接刷入。

- 只产出 apk，不产出 ipk
- 编译使用 openwrt_package 同款 SDK 工作流（`MinimaxFlora/gh-action-sdk`）
- 编译产物和 `.run` 都发布在本仓库的 GitHub Release
- 每个分组一个 `.run`，里面已经包含该分组需要的全部 apk

## 工作原理

```
Package_Manager workflow
  1. 读取选择的分组 -> 从 openwrt_package 动态解析出构建目标列表
  2. 拉取 openwrt_package 作为 SDK 的 feed，编译出 .apk
  3. 收集本次分组的所有 .apk
  4. makeself 打包成 <分组>-<架构>-<版本>.run
  5. 按架构发布到本仓库 Release（tag: apk-<架构>）
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
tools/build_run.py                    用 makeself 把 apk 打包成 .run
tools/install.sh.in                   .run 内嵌的安装脚本模板
```

## 使用方法

1. 打开仓库的 **Actions** 页面，选择 **Build APK Run Installers**。
2. 点击 **Run workflow**，选择插件分组、目标架构。
   - 版本留空会使用 `downloads.openwrt.org` 上最新的 apk 稳定版（25.12.x）。
   - 只选一个分组时，只会编译该分组需要的插件，速度快很多。
3. 构建完成后，进入 **Releases**，下载 `apk-<架构>` 里的 `.run`。
   Release 里同时保留了本次构建的原始 `.apk`，需要单个包时可以直接下载。
4. 把 `.run` 上传到路由器（scp、iStoreOS 文件管理、U 盘等均可），用 root 执行：

```sh
sh theme-aurora-x86_64-25.12.6.run
```

也可以直接用里面的 apk：

```sh
apk add --allow-untrusted luci-theme-aurora-*.apk
```

## 分组列表

分组定义在 `tools/groups.json`，工作流的下拉选项与之对应。

| 分组 | 编译目标 |
| :--- | :--- |
| 全部插件 | openwrt_package 当前全部构建目标 |
| Argon 主题 | luci-theme-argon, luci-app-argon-config |
| Vantage 主题 | luci-theme-vantage, luci-app-vantage |
| Aurora 主题 | luci-theme-aurora, luci-app-aurora-config |
| Design 主题 | luci-theme-design |
| Shadcn 主题 | luci-theme-shadcn |
| Fluent 主题 | luci-theme-fluent, luci-mod-fluentdashboard |
| Fluent Lite 主题 | luci-theme-fluent-lite |
| Mosdns DNS 转换器 | mosdns, luci-app-mosdns, v2ray-geodata, geo2txt |
| OpenClash 代理插件 | luci-app-openclash |
| HomeProxy 代理插件 | luci-app-homeproxy |
| PassWall 代理插件 | luci-app-passwall, chinadns-ng, dns2socks, microsocks, tcping |
| PassWall2 代理插件 | luci-app-passwall2, tcping, geoview, v2ray-geodata |
| Nikki 代理插件 | nikki, mihomo-meta, luci-app-nikki |
| HelloWorld 代理内核组件 | chinadns-ng, dns2socks, ipt2socks, microsocks, tcping, xray-core, xray-plugin, sing-box, hysteria, naiveproxy, shadowsocks-rust, shadowsocksr-libev, shadow-tls, simple-obfs, v2ray-geodata, v2ray-plugin |
| DiskMan 磁盘管理工具 | luci-app-diskman |
| MentoHUST 认证 | luci-app-mentohust, mentohust |
| Quickfile 文件管理 | luci-app-quickfile, quickfile |
| RamFree 内存清理 | luci-app-ramfree |
| Bandix-Plus 网络流量监控 | luci-app-bandix-plus, bandix-plus |
| OpenList 网盘聚合工具 | luci-app-openlist2, openlist2 |
| AirConnect 音频服务 | luci-app-airconnect, airconnect |
| Autocore 硬件信息 | autocore |
| Socat 端口转发 | luci-app-socat |
| AdGuardHome 广告拦截 | luci-app-adguardhome |
| Geo 数据工具 | geoview, geo2txt |

`openwrt_package` 新增插件后，只要 `tools/list-packages.py` 能扫到，选择“全部插件”就会自动带上。
如果要单独分组，在 `tools/groups.json` 里加一条，并在工作流下拉选项里加同名选项即可。

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

检查分组会解析出哪些构建目标：

```sh
git clone --depth 1 https://github.com/MinimaxFlora/openwrt_package /tmp/openwrt_package
python3 tools/resolve_group.py --src /tmp/openwrt_package --label "Aurora 主题"
```

## 注意事项

- `.run` 需要 root 权限，脚本里用了 makeself 的 `--needroot`。
- 目标系统需要 `apk`；OpenWrt 24.10 及更早版本使用 opkg，请改用 ipk。
- Fluent 主题与 Fluent Lite 主题互斥，`全部插件` 默认不包含 Fluent Lite，需要它时单独选择该分组。
- 分组里的 LuCI 包通常是 `noarch`，可以跨架构安装；带二进制的插件必须匹配架构。
- 安装时会从固件现有软件源补齐外部依赖（如 `luci-base`），请确保设备能访问软件源。
- 代理插件分组只包含 LuCI 界面和仓库内的依赖；代理内核（xray、sing-box、hysteria 等）请另外安装 `HelloWorld 代理内核组件`，或使用固件软件源里的版本。
- `全部插件` 会生成一个安装所有 apk 的 `.run`，多个代理/主题同时安装可能在运行期互相抢占端口。日常刷入建议按分组单独构建。
- 构建产物未签名，安装时统一使用 `--allow-untrusted`。
