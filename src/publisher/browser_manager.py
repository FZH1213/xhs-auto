"""
浏览器管理器
负责浏览器生命周期管理、状态持久化、反爬虫策略
"""
import os
import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from .exceptions import BrowserInitError


class BrowserManager:
    """浏览器管理器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化浏览器管理器

        Args:
            config: 配置字典，包含以下字段：
                - browser.storage_path: 浏览器状态存储路径
                - browser.headless: 是否使用无头模式
                - browser.timeout: 操作超时时间（毫秒）
        """
        self.config = config
        self.storage_path = config.get('browser', {}).get(
            'storage_path', './data/browser_state'
        )
        self.headless = config.get('browser', {}).get('headless', False)
        self.timeout = config.get('browser', {}).get('timeout', 30000)

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._keep_open = True  # 保持浏览器打开的标志

    async def init_browser(self) -> Page:
        """
        初始化浏览器

        Returns:
            Page: 浏览器页面对象
        """
        try:
            # 确保存储目录存在
            print(f"[1/6] 创建存储目录: {self.storage_path}")
            os.makedirs(self.storage_path, exist_ok=True)
            print("✓ 存储目录创建成功")

            print(f"[2/6] 启动 Playwright（headless={self.headless}）...")
            # 启动 Playwright
            self.playwright = await async_playwright().start()
            print("✓ Playwright 启动成功")

            print("[3/6] 创建浏览器上下文...")
            # 创建持久化浏览器上下文
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.storage_path,
                headless=self.headless,
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ],
                ignore_default_args=['--enable-automation']
            )
            print("✓ 浏览器上下文创建成功")

            print("[4/6] 创建/获取页面...")
            # 获取或创建页面
            if self.context.pages:
                self.page = self.context.pages[0]
                print("✓ 使用现有页面")
            else:
                self.page = await self.context.new_page()
                print("✓ 创建新页面成功")

            print("[5/6] 设置页面超时...")
            # 设置默认超时时间
            self.page.set_default_timeout(self.timeout)
            print(f"✓ 超时设置成功: {self.timeout}ms")

            print("[6/6] 应用反爬虫策略...")
            # 应用反爬虫策略
            await self._apply_stealth_mode()
            print("✓ 反爬虫策略应用成功")

            # 设置浏览器保持打开
            self._keep_open = True

            print()
            print("=" * 60)
            print("✓✓✓ 浏览器初始化完成！")
            print("=" * 60)
            print()

            return self.page

        except Exception as e:
            print()
            print("=" * 60)
            print(f"✗✗✗ 浏览器初始化失败！")
            print("=" * 60)
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            print()
            import traceback
            print("详细错误堆栈:")
            traceback.print_exc()
            print("=" * 60)
            print()
            # 注意：不在这里关闭浏览器，让它保持打开状态以便调试
            # await self.close()
            raise BrowserInitError(f"浏览器初始化失败: {str(e)}")

    async def _apply_stealth_mode(self):
        """
        应用反爬虫策略，隐藏自动化特征
        """
        try:
            # 修改 navigator.webdriver 属性
            await self.page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """)

            # 修改 plugins 属性
            await self.page.evaluate("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                })
            """)

            # 修改 languages 属性
            await self.page.evaluate("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                })
            """)

            # 隐藏 Chrome 自动化标志
            await self.page.evaluate("""
                Object.defineProperty(navigator, 'chrome', {
                    get: () => true
                })
            """)

            # 修改 permissions（添加安全检查）
            await self.page.evaluate("""
                if (window.navigator && window.navigator.permissions && window.navigator.permissions.query) {
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                }
            """)

        except Exception as e:
            # 如果反爬虫策略应用失败，记录警告但不中断
            print(f"⚠️  反爬虫策略部分应用失败（不影响使用）: {str(e)}")
            # 继续执行，不抛出异常

    async def get_page(self) -> Page:
        """
        获取浏览器页面

        Returns:
            Page: 浏览器页面对象
        """
        if not self.page:
            await self.init_browser()
        return self.page

    async def save_state(self):
        """
        保存浏览器状态（cookies、localStorage等）
        注意：使用 launch_persistent_context 时会自动保存
        """
        if self.context:
            await self.context.storage_state()

    async def clear_state(self):
        """
        清除浏览器状态（退出登录时使用）
        """
        if self.page:
            await self.page.context.clear_cookies()
            await self.page.evaluate('window.localStorage.clear()')
            await self.page.evaluate('window.sessionStorage.clear()')

    async def close(self, force: bool = False):
        """
        关闭浏览器和释放资源

        Args:
            force: 是否强制关闭（默认False，浏览器会保持打开）
        """
        # 如果不是强制关闭且设置了保持打开，则不关闭
        if not force and self._keep_open:
            print("浏览器保持打开状态（如需关闭，请使用 force=True）")
            return

        try:
            print("正在关闭浏览器...")
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            print("✓ 浏览器已关闭")
        except Exception as e:
            print(f"关闭浏览器时出错: {str(e)}")
        finally:
            self.browser = None
            self.context = None
            self.page = None
            self.playwright = None

    async def take_screenshot(self, path: str):
        """
        截图（用于调试）

        Args:
            path: 截图保存路径
        """
        if self.page:
            await self.page.screenshot(path=path)

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()