#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_run.py — 把一组 .apk 打包成 makeself 自解压 .run 安装器

生成的 .run 在目标设备上以 root 执行后，会解压到临时目录并运行内置的
install.sh，最终等价于：

    apk add --allow-untrusted ./*.apk

用法:
    python3 tools/build_run.py \
        --apk-dir release \
        --out-dir out \
        --slug theme-aurora \
        --label "Aurora 主题" \
        --arch x86_64 \
        --version 25.12.6 \
        --makeself /path/to/makeself.sh
"""
import argparse
import datetime
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "install.sh.in")


def sha256sum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_install_script(label, arch, version, build_time):
    with open(TEMPLATE, encoding="utf-8") as f:
        text = f.read()
    # 模板里标签放在单引号中，去掉单引号即可避免注入/截断
    safe_label = label.replace("'", "")
    return (
        text.replace("@@LABEL@@", safe_label)
        .replace("@@ARCH@@", arch)
        .replace("@@VERSION@@", version)
        .replace("@@BUILD_TIME@@", build_time)
    )


def resolve_makeself(value):
    if os.sep in value or "/" in value:
        return value
    found = shutil.which(value)
    return found or value


def makeself_argv(makeself):
    """makeself.sh 在没有执行位（Windows/解压出来的文件）时用 sh 拉起。"""
    if os.name != "posix" or not os.access(makeself, os.X_OK):
        return ["sh", makeself]
    return [makeself]


def main():
    ap = argparse.ArgumentParser(description="Bundle .apk files into a makeself .run installer")
    ap.add_argument("--apk-dir", required=True, help="包含 .apk 的目录")
    ap.add_argument("--out-dir", required=True, help="输出 .run 的目录")
    ap.add_argument("--slug", required=True, help="用于文件名的短英文标识")
    ap.add_argument("--label", required=True, help="分组中文名，写入安装脚本")
    ap.add_argument("--arch", required=True, help="目标架构，例如 x86_64")
    ap.add_argument("--version", required=True, help="OpenWrt 版本，例如 25.12.6")
    ap.add_argument("--makeself", default="makeself", help="makeself 可执行文件路径")
    ap.add_argument("--complevel", default="", help="gzip 压缩级别（1-9，留空使用 makeself 默认值）")
    ap.add_argument("--copy-apks", action="store_true",
                    help="额外把原始 .apk 复制到 <out-dir>/apk（默认不复制，Release 里只放 .run）")
    args = ap.parse_args()

    apks = sorted(glob.glob(os.path.join(args.apk_dir, "*.apk")))
    if not apks:
        print(f"ERROR: 在 {args.apk_dir} 里没有找到 .apk 文件", file=sys.stderr)
        return 1

    makeself = resolve_makeself(args.makeself)
    if not os.path.isfile(makeself):
        print(f"ERROR: 找不到 makeself: {makeself}", file=sys.stderr)
        return 1
    if os.name == "posix" and not os.access(makeself, os.X_OK):
        print(f"ERROR: makeself 不可执行: {makeself}", file=sys.stderr)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    out_name = f"{args.slug}-{args.arch}-{args.version}.run"
    out_path = os.path.abspath(os.path.join(args.out_dir, out_name))
    build_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    staging = tempfile.mkdtemp(prefix="makeself-staging-")
    try:
        for path in apks:
            shutil.copy2(path, os.path.join(staging, os.path.basename(path)))

        install = os.path.join(staging, "install.sh")
        with open(install, "w", encoding="utf-8") as f:
            f.write(render_install_script(args.label, args.arch, args.version, build_time))
        os.chmod(install, 0o755)

        lines = [
            f"label: {args.label}",
            f"arch: {args.arch}",
            f"openwrt: {args.version}",
            f"built: {build_time}",
            "packages:",
        ]
        for path in apks:
            lines.append(f"  {os.path.basename(path)}  sha256:{sha256sum(path)}")
        manifest_text = "\n".join(lines) + "\n"

        manifest = os.path.join(staging, "MANIFEST.txt")
        with open(manifest, "w", encoding="utf-8") as f:
            f.write(manifest_text)
        with open(os.path.join(args.out_dir, out_name + ".manifest.txt"), "w", encoding="utf-8") as f:
            f.write(manifest_text)

        cmd = makeself_argv(makeself) + [
            "--needroot",
            "--nox11",
            "--sha256",
            "--gzip",
            "--quiet",
        ]
        if args.complevel:
            cmd += ["--complevel", args.complevel]
        cmd += [
            staging,
            out_path,
            f"{args.label} ({args.arch}, OpenWrt {args.version})",
            "./install.sh",
        ]

        print("+ " + " ".join(cmd))
        subprocess.run(cmd, check=True)

        digest = sha256sum(out_path)
        with open(out_path + ".sha256", "w", encoding="utf-8") as f:
            f.write(f"{digest}  {out_name}\n")

        if args.copy_apks:
            apk_out = os.path.join(args.out_dir, "apk")
            os.makedirs(apk_out, exist_ok=True)
            for path in apks:
                shutil.copy2(path, os.path.join(apk_out, os.path.basename(path)))

        size_mib = os.path.getsize(out_path) / 1024 / 1024
        print(f"生成: {out_path} ({size_mib:.2f} MiB, sha256 {digest})")
        print("包含 %d 个 apk: %s" % (len(apks), ", ".join(os.path.basename(p) for p in apks)))
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
