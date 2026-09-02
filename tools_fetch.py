# -*- coding: utf-8 -*-
"""用 Python 直接从国内镜像下载 pip 安装包（绕开 pip 被 403 的问题）。"""
import re
import sys
import pathlib
import urllib.request
import zipfile
from urllib.parse import urljoin

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
MIRRORS = [
    "https://mirrors.aliyun.com/pypi/simple",
    "https://mirrors.cloud.tencent.com/pypi/simple",
    "https://mirrors.ustc.edu.cn/pypi/web/simple",
    "https://pypi.tuna.tsinghua.edu.cn/simple",
]
WHEELS = pathlib.Path("wheels")
WHEELS.mkdir(exist_ok=True)


def fetch(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def ver_key(ver: str):
    return tuple(int(x) for x in re.findall(r"\d+", ver))


def pick_wheel(pkg: str, want_ver: str | None = None, max_ver: str | None = None):
    """在镜像上找适合本机(CPython3.14/Win64)的最新 wheel。"""
    for base in MIRRORS:
        try:
            html = fetch(f"{base}/{pkg}/").decode("utf-8", "ignore")
        except Exception as e:
            print(f"  镜像不可用 {base}: {e}")
            continue
        best = None
        for href in re.findall(r'href="([^"]+)"', html):
            url = urljoin(f"{base}/{pkg}/", href).split("#")[0]
            if not url.endswith(".whl"):
                continue
            fn = url.split("/")[-1]
            parts = fn.split("-")
            if len(parts) < 3 or parts[0] != pkg.replace("-", "_"):
                continue
            ver = parts[1]
            py, abi, plat = parts[-3], parts[-2], parts[-1][:-4]
            if re.search(r"(a|b|rc|dev)\d*$", ver):  # 跳过测试版
                continue
            if py not in ("py3", "cp314") or abi not in ("none", "abi3", "cp314"):
                continue
            if plat not in ("any", "win_amd64"):
                continue
            if want_ver and ver != want_ver:
                continue
            if max_ver and ver_key(ver) >= ver_key(max_ver):
                continue
            if best is None or ver_key(ver) > ver_key(best[1]):
                best = (url, ver, fn)
        if best:
            print(f"  选定: {best[2]}  (来源 {base})")
            return best
    return None


def download(url: str, dest: pathlib.Path):
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  已存在，跳过: {dest.name}")
        return
    print(f"  下载中: {url}")
    data = fetch(url, timeout=600)
    dest.write_bytes(data)
    print(f"  完成: {dest.name} ({len(data)/1048576:.1f} MB)")


def pinned_deps(wheel_path: pathlib.Path):
    """读取 wheel 内 METADATA 里精确锁定的依赖版本。"""
    pins = {}
    with zipfile.ZipFile(wheel_path) as z:
        meta = next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))
        for line in z.read(meta).decode("utf-8", "ignore").splitlines():
            m = re.match(r"Requires-Dist:\s*([\w.-]+)\s*==\s*([\w.]+)", line)
            if m and "extra" not in line:
                pins[m.group(1)] = m.group(2)
    return pins


def main():
    todo = [("playwright", None, None)]
    # playwright 1.62 的依赖范围: pyee<14,>=13 ; greenlet<4,>=3.1.1
    todo.append(("pyee", None, "14"))
    todo.append(("greenlet", None, "4"))
    todo.append(("typing_extensions", None, None))
    done = []
    while todo:
        pkg, ver, maxver = todo.pop(0)
        if pkg in done:
            continue
        print(f"[{pkg}]" + (f" 需要版本 {ver}" if ver else "") + (f" 上限 {maxver}" if maxver else ""))
        found = pick_wheel(pkg, ver, maxver)
        if not found:
            print(f"  !! 没找到合适版本", flush=True)
            if ver:
                sys.exit(f"依赖 {pkg}=={ver} 找不到兼容 wheel")
            continue
        url, _v, fn = found
        dest = WHEELS / fn
        download(url, dest)
        done.append(pkg)
        if pkg == "playwright":
            for dep, dver in pinned_deps(dest).items():
                if dep not in done:
                    todo.append((dep, dver))
    print("全部下载完成:", [p.name for p in WHEELS.glob('*.whl')])


if __name__ == "__main__":
    main()
