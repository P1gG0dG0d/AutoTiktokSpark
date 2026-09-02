# -*- coding: utf-8 -*-
"""
抖音自动续火花脚本
==================
原理：用 Playwright 控制一个真实 Chrome 浏览器，访问抖音网页版，
自动给指定好友的私信会话发送一条固定消息，保住"火花"。

用法：
  huohua.py --login     首次登录：打开浏览器弹出二维码，等你手机扫码
  huohua.py --now       立即发送一条（跳过随机等待，用于测试）
  huohua.py             正式模式：随机等待 0~N 分钟后发送（定时任务用这个）

日志：logs/ 目录；截图证据：screenshots/ 目录
"""

import json
import os
import random
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# ---------- 基础路径 ----------
BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BASE_DIR / ".playwright-browsers"))

LOG_DIR = BASE_DIR / "logs"
SHOT_DIR = BASE_DIR / "screenshots"
PROFILE_DIR = BASE_DIR / "browser_profile"   # 浏览器登录状态保存在这里
LOG_DIR.mkdir(exist_ok=True)
SHOT_DIR.mkdir(exist_ok=True)

CONFIG_PATH = BASE_DIR / "config.json"
STATUS_PATH = BASE_DIR / "latest_status.json"
LOCK_PATH = BASE_DIR / ".running.lock"

DOUYIN_HOME = "https://www.douyin.com"


def goto_home(page) -> None:
    """访问抖音首页，网络抖动自动重试。"""
    last = None
    for i in range(3):
        try:
            page.goto(DOUYIN_HOME, wait_until="domcontentloaded", timeout=60000)
            return
        except Exception as e:
            last = e
            log(f"访问抖音失败（第 {i+1} 次）：{e}")
            time.sleep(5 * (i + 1))
    raise last


# ---------- 配置 ----------
def load_config() -> dict:
    default = {
        "friend_name": "好友昵称",
        "message": "续火花啦~",
        "random_delay_minutes": 55,
        "browser": "edge",
        "headless": False,
        "max_attempts": 3,
        "typing_delay_ms": 120,
    }
    # 基础配置（随项目分发，放示例值；真实值放 config.local.json）
    if CONFIG_PATH.exists():
        try:
            default.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[配置] config.json 读取失败，使用默认配置：{e}", flush=True)
    # 本地私密配置覆盖（config.local.json 已 gitignore，不会上传到 GitHub）
    local_path = BASE_DIR / "config.local.json"
    if local_path.exists():
        try:
            default.update(json.loads(local_path.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[配置] config.local.json 读取失败（忽略）：{e}", flush=True)
    return default


CFG = load_config()


# ---------- 日志 ----------
def log(msg: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    month_file = LOG_DIR / f"huohua_{datetime.now():%Y%m}.log"
    try:
        with open(month_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def write_status(result: str, detail: str = "", shot: str = "") -> None:
    data = {
        "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "result": result,      # SUCCESS / FAILED / NEED_LOGIN
        "detail": detail,
        "screenshot": shot,
    }
    try:
        STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def shot(page, name: str) -> str:
    """保存调试/证据截图，返回文件名。"""
    fname = f"{datetime.now():%Y%m%d_%H%M%S}_{name}.png"
    try:
        page.screenshot(path=str(SHOT_DIR / fname), full_page=False)
        return fname
    except Exception as e:
        log(f"截图失败（{name}）：{e}")
        return ""


def dump_page(page, name: str) -> None:
    """把当前页面 HTML 存到 logs/，便于远程诊断页面结构问题。"""
    try:
        f = LOG_DIR / f"page_{datetime.now():%Y%m%d_%H%M%S}_{name}.html"
        f.write_text(page.content(), encoding="utf-8")
        log(f"页面快照已保存: {f.name}")
    except Exception as e:
        log(f"页面快照失败（{name}）：{e}")


# ---------- 防重复运行 ----------
def acquire_lock() -> bool:
    if LOCK_PATH.exists():
        try:
            pid = int(LOCK_PATH.read_text().strip())
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                log(f"已有另一个实例在运行（PID {pid}），本次退出")
                return False
        except Exception:
            pass
    LOCK_PATH.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass


# ---------- 浏览器 ----------
def make_browser():
    """启动浏览器：优先用系统自带的 Edge，失败则退回项目内置的 Chromium。"""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    prefs = dict(
        user_data_dir=str(PROFILE_DIR),
        headless=CFG.get("headless", False),
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        viewport={"width": 1380, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    pref = CFG.get("browser", "edge")
    order = ["msedge", None] if pref == "edge" else [None, "msedge"]
    last_err = None
    for channel in order:
        try:
            kw = dict(prefs)
            if channel:
                kw["channel"] = channel
            ctx = pw.chromium.launch_persistent_context(**kw)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_default_timeout(15000)
            log(f"浏览器已启动（{'系统Edge' if channel else '内置Chromium'}）")
            return pw, ctx, page
        except Exception as e:
            last_err = e
            log(f"浏览器启动失败（{channel or '内置Chromium'}）：{e}")
    raise last_err


def login_panel_visible(page) -> bool:
    """抖音的强制登录弹窗是否挡在页面上。"""
    try:
        return page.locator('[id^="login-full-panel"]').first.is_visible()
    except Exception:
        return False


def is_logged_in(page) -> bool:
    """综合判断登录状态：页面头像元素为准，cookie 为辅，登录面板优先否决。"""
    if login_panel_visible(page):
        return False
    try:
        if page.locator('[data-e2e="live-avatar"]').first.is_visible():
            return True
    except Exception:
        pass
    try:
        cookies = page.context.cookies("https://www.douyin.com")
        names = {c["name"] for c in cookies}
        return bool({"sessionid", "sessionid_ss"} & names)
    except Exception:
        return False


def wait_home_ready(page, timeout: int = 20) -> None:
    """等待首页水合完成（导航文字出现）。"""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except Exception:
        pass
    for marker in ['text=精选', 'text=推荐', '[data-e2e="douyin-navigation"]']:
        try:
            page.wait_for_selector(marker, timeout=timeout * 1000 // 3)
            break
        except Exception:
            continue


def human_pause(a=0.8, b=2.0) -> None:
    time.sleep(random.uniform(a, b))


def try_close_popups(page) -> None:
    """尽力关闭各种弹窗。"""
    selectors = [
        'dy-account-close',                       # 登录弹窗关闭按钮
        '[aria-label="关闭"]',
        'div[class*="close"]',
    ]
    for sel in selectors:
        try:
            for el in page.locator(sel).all()[:3]:
                if el.is_visible():
                    el.click(timeout=2000)
                    human_pause(0.3, 0.8)
        except Exception:
            continue


# ---------- 核心流程 ----------
def open_message_panel(page) -> bool:
    """打开消息/私信面板（2026-09 实测：抖音右上角 im-entry 按钮）。"""
    # 主策略：抖音官方测试标记 im-entry（带"消息"文字和红点角标）
    try:
        entry = page.locator('[data-e2e="im-entry"]').first
        entry.wait_for(state="visible", timeout=15000)
        entry.click()
        human_pause(1.0, 2.0)
        # 等会话面板出现
        page.wait_for_selector(
            '[data-e2e="conversation-item"], .componentsLeftPanelwrapper',
            timeout=10000)
        shot(page, "clicked_im_entry")
        return True
    except Exception as e:
        log(f"im-entry 点击失败: {e}")
    # 备用策略
    for sel in ['a[href*="message"]', '[aria-label*="消息"]',
                'p:text-is("消息")', 'span:text-is("消息")']:
        try:
            loc = page.locator(sel).first
            if loc.is_visible():
                loc.click(timeout=3000)
                human_pause()
                return True
        except Exception:
            continue
    return False


def open_conversation(page, friend_name: str) -> bool:
    """在私信面板里定位并打开指定好友的会话（conversation-item 结构）。"""
    # 主策略：会话列表中按名字找（目标好友一般排在列表最前面）
    try:
        item = page.locator('[data-e2e="conversation-item"]',
                            has_text=friend_name).first
        item.wait_for(state="visible", timeout=8000)
        item.click(timeout=4000)
        human_pause(1.0, 2.0)
        shot(page, "opened_conversation")
        return True
    except Exception as e:
        log(f"会话列表直选失败: {e}")
    # 备用策略：用面板顶部搜索框搜索
    try:
        box = page.locator(
            '.searchSearchInputinput_box input, input[placeholder*="搜索"]'
        ).first
        if not box.is_visible():
            return False
        box.click()
        box.fill(friend_name)
        human_pause(0.8, 1.5)
        page.keyboard.press("Enter")
        human_pause(1.5, 2.5)
        shot(page, "searched_friend")
        item = page.locator('[data-e2e="conversation-item"]',
                            has_text=friend_name).first
        item.click(timeout=5000)
        human_pause(1.0, 2.0)
        shot(page, "opened_conversation")
        return True
    except Exception as e:
        log(f"搜索会话失败: {e}")
    return False


def send_message(page, message: str) -> bool:
    """在聊天窗口输入并发送消息，并验证已发出。"""
    # 等聊天输入区出现（点进会话后才有）
    try:
        page.wait_for_selector('div[contenteditable="true"]', timeout=8000)
    except Exception:
        pass
    input_box = None
    input_sels = [
        'div[contenteditable="true"]',
        'textarea[placeholder*="发送"]',
        'textarea',
    ]
    for sel in input_sels:
        try:
            box = page.locator(sel).first
            if box.is_visible():
                input_box = box
                break
        except Exception:
            continue
    if input_box is None:
        log("没找到聊天输入框")
        shot(page, "no_input_box")
        return False

    input_box.click()
    human_pause(0.3, 0.8)
    input_box.type(message, delay=CFG.get("typing_delay_ms", 120))
    human_pause(0.5, 1.0)

    # 先尝试回车发送
    page.keyboard.press("Enter")
    human_pause(1.0, 1.8)

    if verify_sent(page, message):
        return True

    # 回车没发出去就点"发送"按钮
    try:
        for sel in ['button:text-is("发送")', '[class*="send"]', 'button:has-text("发送")']:
            btn = page.locator(sel).first
            if btn.is_visible():
                btn.click(timeout=3000)
                human_pause(1.0, 1.8)
                break
    except Exception:
        pass
    return verify_sent(page, message)


def verify_sent(page, message: str) -> bool:
    """检查聊天记录里是否出现了刚发出去的消息。"""
    try:
        bubble = page.get_by_text(message, exact=True).last
        if bubble.is_visible():
            return True
    except Exception:
        pass
    return False


def run_once() -> bool:
    """完整跑一次：开浏览器→检查登录→发消息→存证。"""
    pw = ctx = page = None
    try:
        log("启动浏览器...")
        pw, ctx, page = make_browser()
        goto_home(page)
        wait_home_ready(page)
        try_close_popups(page)

        if not is_logged_in(page):
            shot(page, "need_login")
            dump_page(page, "need_login")
            write_status("NEED_LOGIN", "登录已过期，请运行 huohua.py --login 重新扫码")
            log("!! 登录已过期：请运行  huohua.py --login  重新扫码登录")
            return False

        log("登录状态正常")
        if not open_message_panel(page):
            log("打不开消息面板")
            shot(page, "open_panel_failed")
            dump_page(page, "open_panel_failed")
            return False

        friend = CFG["friend_name"]
        log(f"查找好友会话：{friend}")
        if not open_conversation(page, friend):
            log(f"没找到「{friend}」的会话")
            shot(page, "conversation_not_found")
            dump_page(page, "conversation_not_found")
            return False

        msg = CFG["message"]
        log(f"输入并发送消息：{msg}")
        if not send_message(page, msg):
            shot(page, "send_failed")
            dump_page(page, "send_failed")
            return False

        fname = shot(page, "sent_ok")
        log(f"✔ 发送成功！证据截图：{fname}")
        write_status("SUCCESS", f"已向「{friend}」发送：{msg}", fname)
        return True

    except Exception as e:
        log(f"发生异常：{e}")
        try:
            traceback.print_exc()
        except Exception:
            pass
        try:
            if page:
                shot(page, "exception")
                dump_page(page, "exception")
        except Exception:
            pass
        return False
    finally:
        try:
            if ctx:
                ctx.close()
            if pw:
                pw.stop()
        except Exception:
            pass


def probe_flow() -> None:
    """侦察模式：登录后收集首页所有可见交互元素，供远程分析真实选择器。"""
    pw, ctx, page = make_browser()
    try:
        log("侦察：打开抖音首页...")
        goto_home(page)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        # 等待页面水合完成（侧边栏文字出现）
        for marker in ['text=首页', 'text=推荐', 'text=精选']:
            try:
                page.wait_for_selector(marker, timeout=8000)
                break
            except Exception:
                continue
        time.sleep(3)
        dump_page(page, "probe_home")
        shot(page, "probe_home")
        elems = page.evaluate(
            """() => {
                const out = [];
                const sel = 'a,button,[role="button"],[aria-label],[class*="nav"],[class*="message"],[class*="im-"],[class*="chat"],[class*="LoginContainer"],[class*="avatar"]';
                for (const el of document.querySelectorAll(sel)) {
                    const r = el.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) {
                        out.push({
                            tag: el.tagName,
                            text: (el.innerText || '').replace(/\\s+/g, ' ').slice(0, 40),
                            aria: el.getAttribute('aria-label') || '',
                            title: el.getAttribute('title') || '',
                            cls: String(el.className).slice(0, 100),
                            id: el.id || '',
                        });
                    }
                }
                return out.slice(0, 400);
            }"""
        )
        (LOG_DIR / "probe_elements.json").write_text(
            json.dumps(elems, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"侦察完成：收集到 {len(elems)} 个可见交互元素 → logs/probe_elements.json")
        write_status("PROBE_DONE", f"收集到 {len(elems)} 个元素")
    finally:
        try:
            ctx.close()
            pw.stop()
        except Exception:
            pass


def probe_im_flow() -> None:
    """IM侦察：点击消息按钮后，盘点所有页面/内嵌框架，找到会话列表真身。"""
    pw, ctx, page = make_browser()
    try:
        log("IM侦察：打开抖音首页...")
        goto_home(page)
        wait_home_ready(page)
        time.sleep(2)
        if login_panel_visible(page) or not is_logged_in(page):
            shot(page, "probe_im_need_login")
            dump_page(page, "probe_im_need_login")
            log("IM侦察中止：登录面板弹出/未登录，需要重新扫码")
            write_status("NEED_LOGIN", "侦察时发现登录失效")
            return
        log("IM侦察：点击消息按钮...")
        page.locator('[data-e2e="im-entry"]').first.click(timeout=10000)
        time.sleep(5)
        shot(page, "probe_im_after_click")

        report = []
        for i, p in enumerate(ctx.pages):
            try:
                info = {"page_index": i, "url": p.url, "title": "", "frames": []}
                try:
                    info["title"] = p.title()[:60]
                except Exception:
                    pass
                for f in p.frames:
                    finfo = {"frame_url": f.url[:120], "name": f.name}
                    try:
                        loc = f.locator('[data-e2e="conversation-item"]')
                        cnt = loc.count()
                        vis, texts = 0, []
                        for el in loc.all()[:12]:
                            try:
                                txt = el.inner_text()[:50].replace("\n", "/")
                                texts.append(txt)
                                if el.is_visible():
                                    vis += 1
                            except Exception:
                                pass
                        finfo.update(conversation_items=cnt,
                                     visible_items=vis, texts=texts)
                        # 聊天输入框探测
                        finfo["contenteditable"] = f.locator(
                            'div[contenteditable="true"]').count()
                    except Exception as e:
                        finfo["error"] = str(e)[:120]
                    info["frames"].append(finfo)
                report.append(info)
            except Exception as e:
                report.append({"page_index": i, "error": str(e)[:120]})
        (LOG_DIR / "probe_im.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        dump_page(page, "probe_im_main")
        log(f"IM侦察完成：共 {len(ctx.pages)} 个页面 → logs/probe_im.json")
        write_status("PROBE_IM_DONE", f"pages={len(ctx.pages)}")
    finally:
        try:
            ctx.close()
            pw.stop()
        except Exception:
            pass


def main() -> None:
    args = sys.argv[1:]

    if "--login" in args:
        login_flow()
        return

    if "--probe" in args:
        probe_flow()
        return

    if "--probe-im" in args:
        probe_im_flow()
        return

    if not acquire_lock():
        sys.exit(0)

    try:
        # 随机延迟（正式模式才有；--now 跳过）
        if "--now" not in args:
            minutes = int(CFG.get("random_delay_minutes", 55))
            if minutes > 0:
                wait = random.uniform(0, minutes * 60)
                log(f"随机等待 {wait/60:.1f} 分钟后开始发送（模拟真人）...")
                # 分段睡眠，避免进程被杀时锁文件残留过久
                end = time.time() + wait
                while time.time() < end:
                    time.sleep(min(30, end - time.time()))

        ok = False
        attempts = int(CFG.get("max_attempts", 3))
        for i in range(1, attempts + 1):
            log(f"===== 第 {i}/{attempts} 次尝试 =====")
            ok = run_once()
            if ok:
                break
            if i < attempts:
                cooldown = 90 * i
                log(f"等待 {cooldown} 秒后重试...")
                time.sleep(cooldown)

        if ok:
            log("今日任务完成 ✅")
            sys.exit(0)
        else:
            log("今日任务失败 ❌（详见截图与日志）")
            write_status("FAILED", "多次尝试后仍失败，请查看 screenshots/ 与 logs/")
            sys.exit(1)
    finally:
        release_lock()


def login_flow() -> None:
    """首次登录：打开浏览器等待扫码。"""
    pw, ctx, page = make_browser()
    try:
        goto_home(page)
        human_pause(1.5, 2.5)
        log("浏览器已打开抖音首页。")
        log("如未登录，请在浏览器窗口中点击右上角【登录】，用手机抖音扫码。")
        log("最多等待 5 分钟，检测到登录成功会自动退出...")
        deadline = time.time() + 300
        last_reload = time.time()
        while time.time() < deadline:
            if is_logged_in(page):
                shot(page, "login_success")
                log("✔ 登录成功！登录状态已保存到 browser_profile/，以后不用再扫码。")
                write_status("LOGGED_IN", "扫码登录成功")
                return
            if time.time() - last_reload > 30:
                try:
                    page.reload(wait_until="domcontentloaded")
                    log("（自动刷新页面以确认登录状态...）")
                except Exception:
                    pass
                last_reload = time.time()
            time.sleep(3)
        shot(page, "login_timeout")
        log("超时未检测到登录。请重跑一次 --login。")
        write_status("NEED_LOGIN", "登录流程超时")
    finally:
        try:
            ctx.close()
            pw.stop()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import io
        buf = io.StringIO()
        traceback.print_exc(file=buf)
        crash = LOG_DIR / "crash.log"
        try:
            with open(crash, "a", encoding="utf-8") as f:
                f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
                f.write(buf.getvalue())
        except Exception:
            pass
        print("程序出错，详情已记录到 logs/crash.log", flush=True)
        print(buf.getvalue(), flush=True)
        try:
            if sys.stdin and sys.stdin.isatty():
                input("按回车键退出...")
        except Exception:
            pass
