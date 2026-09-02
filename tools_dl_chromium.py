# -*- coding: utf-8 -*-
"""直接下载 Chromium 浏览器内核并放置到 Playwright 期望的位置（绕开其子进程下载器）。"""
import os
import pathlib
import sys
import time
import zipfile
import urllib.request

BASE = pathlib.Path(".").resolve()
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BASE / ".playwright-browsers")

URL = "https://cdn.npmmirror.com/binaries/playwright/builds/cft/151.0.7922.34/win64/chrome-win64.zip"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
ZIP_PATH = BASE / ".tmp" / "chrome-win64.zip"


def download():
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 100_000_000:
        print(f"已有完整压缩包: {ZIP_PATH.stat().st_size/1048576:.0f} MB, 跳过下载")
        return
    print("开始下载 Chromium ...")
    req = urllib.request.Request(URL, headers=UA)
    total = None
    with urllib.request.urlopen(req, timeout=60) as resp, open(ZIP_PATH, "wb") as f:
        total = int(resp.headers.get("Content-Length", 0))
        got, last = 0, 0.0
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if time.time() - last > 3:
                pct = f"{got/total*100:.0f}%" if total else f"{got/1048576:.0f}MB"
                print(f"  进度: {pct} ({got/1048576:.0f}/{total/1048576:.0f} MB)", flush=True)
                last = time.time()
    print(f"下载完成: {ZIP_PATH.stat().st_size/1048576:.0f} MB")


def expected_path() -> pathlib.Path:
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    try:
        return pathlib.Path(pw.chromium.executable_path)
    finally:
        pw.stop()


def main():
    download()
    exe = expected_path()
    print(f"Playwright 期望的浏览器位置: {exe}")
    browser_dir = exe.parent.parent          # .../chromium-1234
    browser_dir.mkdir(parents=True, exist_ok=True)
    print("解压中（文件多，需要一两分钟）...")
    with zipfile.ZipFile(ZIP_PATH) as z:
        z.extractall(browser_dir)
    # 放置安装完成标记
    for marker in (browser_dir / "INSTALLATION_COMPLETE", exe.parent / "INSTALLATION_COMPLETE"):
        try:
            marker.write_text("", encoding="utf-8")
        except Exception as e:
            print(f"标记写入失败({marker}): {e}")
    print(f"解压完成 → {exe}")
    print("chrome.exe 存在:" , exe.exists())
    print("OK")


if __name__ == "__main__":
    sys.exit(main())
