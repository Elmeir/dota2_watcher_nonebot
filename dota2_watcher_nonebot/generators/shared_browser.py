"""共享浏览器实例管理模块。

供多个脚本在同一个进程内复用同一个 chromium 浏览器，避免重复启动。

关键约束：
    playwright 的浏览器实例绑定创建它的 event loop，因此只有在
    **同一个事件循环** 内多次调用才会复用同一浏览器；跨事件循环
    （如多次 asyncio.run）会自动重建，旧实例由 atexit 统一清理。

用法：
    import shared_browser

    async def main():
        browser = await shared_browser.get_browser()
        page = await browser.new_page()
        ...

    # 可选：手动关闭（程序退出时也会自动清理）
    await shared_browser.close_browser()

    # 或用上下文管理器自动清理
    async with shared_browser.BrowserSession():
        ...
"""

import asyncio
import atexit

from playwright.async_api import async_playwright

_playwright = None
_browser = None
_loop_id = None


async def get_browser():
    """获取（或创建）共享浏览器实例。

    同一事件循环内多次调用复用同一浏览器；跨循环自动重建。
    """
    global _playwright, _browser, _loop_id

    loop_id = id(asyncio.get_running_loop())
    if _browser is not None and _loop_id == loop_id and _browser.is_connected():
        return _browser

    # 跨事件循环：旧浏览器已失效，直接丢弃引用（旧循环关闭后由系统回收）
    if _browser is not None:
        _browser = None
        _playwright = None

    # start() 返回的是真正的 Playwright 实例（含 chromium 属性）
    if _playwright is None:
        _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(
        headless=True,
        args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
    )
    _loop_id = loop_id
    return _browser


async def close_browser():
    """关闭共享浏览器实例（可选，程序退出时会自动清理）。"""
    global _playwright, _browser, _loop_id

    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright is not None:
        try:
            await _playwright.stop()
        except Exception:
            pass
        _playwright = None
    _loop_id = None


class BrowserSession:
    """浏览器会话上下文管理器，退出时自动关闭共享浏览器。

    Usage:
        async with BrowserSession():
            await generate_image('Anti-Mage', '1')
            await generate_image('Kez', '1')
        # 退出时自动关闭浏览器
    """

    async def __aenter__(self):
        await get_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await close_browser()
        return False


def _cleanup_at_exit():
    """程序退出时的同步清理回调（尽力关闭浏览器，避免资源泄漏）。"""
    global _playwright, _browser

    if _browser is None and _playwright is None:
        return
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(close_browser())
        loop.close()
    except Exception:
        pass


# 注册程序退出清理
atexit.register(_cleanup_at_exit)
