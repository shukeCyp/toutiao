"""
BrowserManager - Playwright Chrome 浏览器管理器
封装 Playwright 的浏览器操作
"""

import base64
from playwright.async_api import async_playwright
from logger import get_logger

log = get_logger('browser')


class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    @property
    def is_connected(self):
        """检查浏览器是否已连接"""
        return self._browser is not None and self._browser.is_connected()

    async def launch(self, headless=False, chrome_path='', user_data_dir='./browser_data'):
        """
        启动 Chrome 浏览器
        使用 persistent context 保留登录状态和 cookies
        """
        log.info(f'BrowserManager 启动 (headless={headless}, data_dir={user_data_dir})')
        if self.is_connected:
            await self.close()

        self._playwright = await async_playwright().start()

        launch_args = {
            'user_data_dir': user_data_dir,
            'headless': headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--no-default-browser-check',
            ],
            'viewport': {'width': 1280, 'height': 800},
        }

        # 如果指定了 Chrome 路径
        if chrome_path:
            launch_args['executable_path'] = chrome_path

        # 使用 persistent context 启动（自带 cookies / localstorage 持久化）
        self._context = await self._playwright.chromium.launch_persistent_context(**launch_args)

        # 获取或创建页面
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

    async def close(self):
        """关闭浏览器并释放资源"""
        log.info('BrowserManager 关闭浏览器')
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

    async def navigate(self, url, timeout=30000):
        """导航到指定 URL"""
        self._ensure_page()
        log.debug(f'导航到: {url}')
        await self._page.goto(url, timeout=timeout, wait_until='domcontentloaded')

    async def get_title(self):
        """获取当前页面标题"""
        self._ensure_page()
        return await self._page.title()

    async def get_url(self):
        """获取当前页面 URL"""
        self._ensure_page()
        return self._page.url

    async def screenshot(self, full_page=False):
        """截取页面截图，返回 base64 编码"""
        self._ensure_page()
        screenshot_bytes = await self._page.screenshot(full_page=full_page)
        return base64.b64encode(screenshot_bytes).decode('utf-8')

    async def evaluate(self, expression):
        """在页面中执行 JavaScript 表达式"""
        self._ensure_page()
        return await self._page.evaluate(expression)

    async def click(self, selector, timeout=5000):
        """点击页面元素"""
        self._ensure_page()
        await self._page.click(selector, timeout=timeout)

    async def fill(self, selector, value, timeout=5000):
        """填充表单字段"""
        self._ensure_page()
        await self._page.fill(selector, value, timeout=timeout)

    async def wait_for_selector(self, selector, timeout=5000):
        """等待元素出现"""
        self._ensure_page()
        return await self._page.wait_for_selector(selector, timeout=timeout)

    async def get_cookies(self):
        """获取当前所有 cookies"""
        if self._context:
            return await self._context.cookies()
        return []

    async def get_page(self):
        """获取当前页面对象，供外部使用高级功能"""
        self._ensure_page()
        return self._page

    def _ensure_page(self):
        """确保页面可用"""
        if not self._page:
            raise RuntimeError('浏览器未启动，请先调用 launch_browser')
