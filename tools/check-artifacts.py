#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-artifacts.py — 校验所选构建目标是否都产出了 apk

SDK 编译这一步设了 IGNORE_ERRORS，单个包编译失败时整轮仍然是绿的，所以需要
这一步兜底：拿 openwrt_package 的 packages.lock.json（构建目标 -> 包名）对照
release/ 里真实存在的 .apk 文件名。

    python3 tools/check-artifacts.py \
        --lock ./packages.lock.json \
        --apk-dir release \
        --targets "luci-theme-aurora luci-app-aurora-config"

退出码:
    0 全部目标都有产物
    1 有目标没产出（调用方决定是否容忍）
    2 用法或数据问题（lock 缺失、目标名不在 lock 里）
"""
import argparse
import json
import os
import sys


def load_lock(lock_path):
    """返回 {构建目标: [包名…]}；包名缺失时以目标名为准。"""
    with open(lock_path, encoding="utf-8") as f:
        data = json.load(f)
    packages = data.get("packages", data)
    if not isinstance(packages, dict):
        raise ValueError(f"{lock_path} 结构无法识别，应为 {{'packages': {{目标: …}}}}")
    out = {}
    for target, info in packages.items():
        names = info.get("packages") if isinstance(info, dict) else None
        out[target] = [n for n in (names or []) if n] or [target]
    return out


def main():
    ap = argparse.ArgumentParser(description="Check that build targets produced apk files")
    ap.add_argument("--lock", default="packages.lock.json", help="openwrt_package 的 packages.lock.json")
    ap.add_argument("--apk-dir", default="release", help="收集出来的 .apk 目录")
    ap.add_argument("--targets", required=True,
                    help="空格或逗号分隔的构建目标列表（就是 resolve_group.py 输出的 PACKAGES）")
    ap.add_argument("--allow-missing", action="store_true",
                    help="有目标没产出时只警告、不返回非 0（全部插件模式用）")
    args = ap.parse_args()

    if not os.path.isfile(args.lock):
        print(f"ERROR: 找不到 {args.lock}", file=sys.stderr)
        return 2
    if not os.path.isdir(args.apk_dir):
        print(f"ERROR: 找不到目录 {args.apk_dir}", file=sys.stderr)
        return 2

    targets = [t for t in args.targets.replace(",", " ").split() if t]
    if not targets:
        print("ERROR: --targets 为空", file=sys.stderr)
        return 2

    try:
        mapping = load_lock(args.lock)
    except (OSError, ValueError) as exc:
        print(f"ERROR: 读取 {args.lock} 失败: {exc}", file=sys.stderr)
        return 2

    files = sorted(f for f in os.listdir(args.apk_dir) if f.endswith(".apk"))
    if not files:
        print(f"ERROR: {args.apk_dir} 里没有 .apk", file=sys.stderr)
        return 1

    unknown = [t for t in targets if t not in mapping]
    if unknown:
        print("ERROR: 这些目标不在 packages.lock.json 里: %s" % " ".join(unknown), file=sys.stderr)
        return 2

    missing = []
    for target in targets:
        names = mapping[target]
        # 文件名形如 <包名>-<版本>-r<rel>.apk，所以用“包名-”前缀匹配，避免
        # luci-app-passwall 误命中 luci-app-passwall2 这种同前缀的包
        hit = [n for n in names
               if any(f.startswith(n + "-") or f == n + ".apk" for f in files)]
        if not hit:
            missing.append(f"{target} (期望: {', '.join(names)})")

    print(f"目标 {len(targets)} 个，apk {len(files)} 个，缺产物 {len(missing)} 个")
    if not missing:
        return 0

    for line in missing:
        print(f"  MISSING {line}")
    print("::warning::以下构建目标没有产出 apk: %s" % "; ".join(missing))
    return 0 if args.allow_missing else 1


if __name__ == "__main__":
    sys.exit(main())
