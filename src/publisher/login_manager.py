"""
登录管理器
负责登录状态检查、等待用户扫码登录
"""
import asyncio
import time
from typing import Dict, Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from .exceptions import LoginRequiredError, LoginTimeoutError


class LoginManager:
    """登录管理器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化登录管理器

        Args:
            config: 配置字典，包含以下字段：
                - login.max_wait_time: 等待登录的最长时间（秒）
        """
        self.config = config
        self.max_wait_time = config.get('login', {}).get('max_wait_time', 300)
        self.home_url = "https://creator.xiaohongshu.com"
        self.login_url = "https://creator.xiaohongshu.com/login"
        self.publish_url = "https://creator.xiaohongshu.com/publish/publish"

    async def check_login_status(self, page: Page) -> bool:
        """
        检查登录状态

        Args:
            page: 浏览器页面对象

        Returns:
            bool: 是否已登录
        """
        try:
            # 获取当前URL
            current_url = page.url

            # 如果在登录页面，返回False
            if 'login' in current_url.lower():
                return False

            # 如果已经在创作者中心，检查是否有登录按钮
            if 'creator.xiaohongshu.com' in current_url:
                # 检查是否存在登录按钮（未登录）
                try:
                    login_button = await page.query_selector('button:has-text("登录"), a:has-text("登录")')
                    if login_button and await login_button.is_visible():
                        return False
                except Exception:
                    pass

                # 检查是否存在用户头像或其他已登录标识
                try:
                    # 已登录用户通常会显示头像或用户名
                    avatar = await page.query_selector('.avatar, .user-avatar, [class*="avatar"]')
                    if avatar:
                        return True
                except Exception:
                    pass

            # 如果已经访问了发布页面，说明已登录
            if '/publish/' in current_url:
                return True

            # 默认返回False
            return False

        except Exception as e:
            print(f"检查登录状态出错: {str(e)}")
            return False

    async def wait_for_login(self, page: Page, timeout: int = None) -> bool:
        """
        等待用户扫码登录

        Args:
            page: 浏览器页面对象
            timeout: 超时时间（秒），默认使用配置的 max_wait_time

        Returns:
            bool: 登录是否成功

        Raises:
            LoginTimeoutError: 登录超时
        """
        if timeout is None:
            timeout = self.max_wait_time

        print(f"请在浏览器中扫码登录小红书...")
        print(f"等待时间：{timeout}秒")

        # 确保在创作者中心首页（不强制跳转）
        try:
            current_url = page.url
            if 'creator.xiaohongshu.com' not in current_url:
                await page.goto(self.home_url, wait_until='domcontentloaded', timeout=15000)
        except Exception as e:
            print(f"访问创作者中心失败: {str(e)}")

        start_time = time.time()
        check_interval = 3  # 每3秒检查一次

        while time.time() - start_time < timeout:
            try:
                # 检查登录状态
                is_logged_in = await self.check_login_status(page)

                if is_logged_in:
                    print("✓ 登录成功！")
                    return True

                # 显示剩余时间
                remaining = int(timeout - (time.time() - start_time))
                if remaining % 30 == 0:  # 每30秒提示一次
                    print(f"等待登录... 剩余 {remaining} 秒")

            except Exception as e:
                print(f"检查登录状态失败: {str(e)}")

            await asyncio.sleep(check_interval)

        # 超时
        raise LoginTimeoutError(f"登录超时（{timeout}秒）")

    async def trigger_login(self, page: Page) -> bool:
        """
        触发登录流程（如果检测到未登录）

        Args:
            page: 浏览器页面对象

        Returns:
            bool: 是否触发了登录
        """
        try:
            # 检查是否已登录
            if await self.check_login_status(page):
                return False

            # 访问创作者中心首页，让它自动显示登录选项
            print("访问创作者中心首页...")
            await page.goto(self.home_url, wait_until='domcontentloaded', timeout=15000)

            # 等待页面加载
            await asyncio.sleep(2)

            # 尝试找到并点击登录按钮
            try:
                login_button = await page.query_selector('button:has-text("登录"), a:has-text("登录")')
                if login_button:
                    await login_button.click()
                    print("已点击登录按钮")
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"点击登录按钮失败: {str(e)}")

            return True

        except Exception as e:
            print(f"触发登录失败: {str(e)}")
            return False

    async def ensure_logged_in(self, page: Page, auto_wait: bool = True) -> bool:
        """
        确保已登录，如果未登录则等待用户登录

        Args:
            page: 浏览器页面对象
            auto_wait: 是否自动等待用户登录

        Returns:
            bool: 是否已登录

        Raises:
            LoginRequiredError: 未登录且不自动等待
            LoginTimeoutError: 等待登录超时
        """
        # 检查登录状态
        if await self.check_login_status(page):
            return True

        # 未登录
        if auto_wait:
            return await self.wait_for_login(page)
        else:
            raise LoginRequiredError("需要登录小红书账号")

    async def logout(self, page: Page) -> bool:
        """
        登出（清除登录状态）

        Args:
            page: 浏览器页面对象

        Returns:
            bool: 是否成功登出
        """
        try:
            # 清除 cookies
            await page.context.clear_cookies()

            # 清除 localStorage 和 sessionStorage
            await page.evaluate('window.localStorage.clear()')
            await page.evaluate('window.sessionStorage.clear()')

            print("已退出登录")
            return True

        except Exception as e:
            print(f"登出失败: {str(e)}")
            return False