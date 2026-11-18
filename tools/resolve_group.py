#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resolve_group.py — 把工作流选择的分组解析成 OpenWrt 构建目标列表

`openwrt_package` 的 SDK 编译参数 `PACKAGES` 需要的是**构建目标名**（包目录名），
不是最终生成出来的包名。本仓库只维护分组定义（tools/groups.json），真正的目标
列表从 openwrt_package 的 tools/list-packages.py 动态读取，避免两边脱节。

用法:
    python3 tools/resolve_group.py \
        --src <openwrt_package 根目录> \
        --groups tools/groups.json \
        --label "Aurora 主题"

输出（同时写入 $GITHUB_ENV，供后续步骤作为环境变量使用）:
    PACKAGES=luci-theme-aurora luci-app-aurora-config
    GROUP_KEY=aurora
    GROUP_LABEL=Aurora 主题
    GROUP_SLUG=theme-aurora
    GROUP_DROP_PKGS=sing-box-tiny      （互斥变体，打包前要丢掉）
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# 同一个构建目标编出来的互斥变体：sing-box 目标会同时产出 sing-box 和 sing-box-tiny
# （sing-box-tiny PROVIDES sing-box 且两者 conflicts），打进同一个 .run 必然装不上。
# 分组里可以用 "drop_pkgs": [...] 覆盖，写空数组表示不丢任何包。
DEFAULT_DROP_PKGS = ["sing-box-tiny"]


def known_targets(src):
    script = os.path.join(src, "tools", "list-packages.py")
    if not os.path.isfile(script):
        sys.exit(f"找不到 {script}，--src 需要指向 openwrt_package 仓库根目录")
    out = subprocess.check_output([sys.executable, script], text=True)
    return out.split()


def main():
    ap = argparse.ArgumentParser(description="Resolve a group label into OpenWrt build targets")
    ap.add_argument("--src", required=True, help="openwrt_package repository root")
    ap.add_argument("--groups", default=os.path.join(HERE, "groups.json"))
    ap.add_argument("--label", required=True, help="group label or key from workflow input")
    ap.add_argument("--github-env", default=os.environ.get("GITHUB_ENV", ""))
    args = ap.parse_args()

    with open(args.groups, encoding="utf-8") as f:
        entries = json.load(f)

    entry = next(
        (e for e in entries if e["label"] == args.label or e["key"] == args.label),
        None,
    )
    if entry is None:
        labels = "\n".join("  - " + e["label"] for e in entries)
        sys.exit(f"未知分组: {args.label}\n可选分组:\n{labels}")

    known = known_targets(args.src)
    if entry.get("targets"):
        targets = entry["targets"]
    else:
        excluded = set(entry.get("exclude", []))
        targets = [t for t in known if t not in excluded]

    unknown = [t for t in targets if t not in known]
    if unknown:
        sys.exit(
            "分组 %s 里的构建目标在 openwrt_package 中不存在: %s\n"
            "当前可用目标:\n  %s"
            % (entry["label"], " ".join(unknown), " ".join(known))
        )

    deduped = list(dict.fromkeys(targets))
    drop = entry.get("drop_pkgs", DEFAULT_DROP_PKGS)
    helpers = entry.get("helper_targets", [])
    env = {
        "PACKAGES": " ".join(deduped),
        "GROUP_KEY": entry["key"],
        "GROUP_LABEL": entry["label"],
        "GROUP_SLUG": entry["slug"],
        "GROUP_DROP_PKGS": " ".join(drop),
        # helper_targets 只是为了把 luci-base/host（po2lmo）建出来，产物会被丢掉，
        # 所以产物校验只针对真实目标
        "GROUP_CHECK_TARGETS": " ".join(t for t in deduped if t not in helpers),
    }

    for key, value in env.items():
        print(f"{key}={value}")
    if args.github_env:
        with open(args.github_env, "a", encoding="utf-8") as f:
            for key, value in env.items():
                f.write(f"{key}={value}\n")

    print(f"分组 {entry['label']}: {len(deduped)} 个构建目标", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
