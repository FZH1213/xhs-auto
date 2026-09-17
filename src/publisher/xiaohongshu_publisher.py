"""
小红书发布器
实现自动发布内容到小红书平台
"""
import asyncio
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from .base_publisher import BasePublisher, PublishResult
from .browser_manager import BrowserManager
from .login_manager import LoginManager
from .exceptions import (
    PublishFailedError,
    LoginRequiredError,
    ValidationError,
    UploadError
)


class XiaohongshuPublisher(BasePublisher):
    """小红书发布器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化小红书发布器

        Args:
            config: 配置字典
        """
        super().__init__(config)
        self.browser_manager = BrowserManager(config)
        self.login_manager = LoginManager(config)
        self.page: Optional[Page] = None

    async def init(self):
        """
        初始化浏览器
        """
        self.page = await self.browser_manager.get_page()

    async def login(self) -> bool:
        """
        登录小红书

        Returns:
            bool: 登录是否成功
        """
        await self.init()
        return await self.login_manager.wait_for_login(self.page)

    async def publish(self, draft_data: Dict[str, Any]) -> PublishResult:
        """
        发布内容到小红书

        Args:
            draft_data: 草稿数据，包含：
                - title: 标题
                - content: 正文内容
                - images: 图片路径列表
                - topics: 话题标签列表

        Returns:
            PublishResult: 发布结果
        """
        try:
            # 确保已初始化
            if not self.page:
                await self.init()

            # 检查登录状态
            if not await self.check_login_status():
                raise LoginRequiredError("需要登录小红书账号")

            print()
            print("=" * 60)
            print("开始发布流程")
            print("=" * 60)

            # 验证数据
            print("验证发布数据...")
            self._validate_draft_data(draft_data)
            print("✓ 数据验证通过")

            # 访问发布页面
            print()
            await self._navigate_to_publish_page()

            # 上传图片
            print()
            print("准备上传图片...")
            await self._upload_images(draft_data.get('images', []))

            # 填写标题
            print()
            print("填写标题...")
            await self._fill_title(draft_data['title'])

            # 填写正文
            print()
            print("填写正文...")
            await self._fill_content(draft_data['content'])

            # 添加话题
            print()
            print("添加话题标签...")
            await self._add_topics(draft_data.get('topics', []))

            # 发布
            print()
            print("提交发布...")
            publish_url = await self._submit_publish()

            print()
            print("=" * 60)
            print("✓✓✓ 发布完成！")
            print("=" * 60)

            return PublishResult(
                success=True,
                url=publish_url,
                published_at=datetime.now(),
                message="发布成功"
            )

        except LoginRequiredError:
            print()
            print("✗ 需要登录")
            raise
        except ValidationError:
            print()
            print("✗ 数据验证失败")
            raise
        except Exception as e:
            print()
            print("=" * 60)
            print("✗✗✗ 发布失败")
            print("=" * 60)
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")

            return PublishResult(
                success=False,
                error=str(e),
                message="发布失败"
            )

    async def check_login_status(self) -> bool:
        """
        检查登录状态

        Returns:
            bool: 是否已登录
        """
        if not self.page:
            return False
        return await self.login_manager.check_login_status(self.page)

    async def logout(self) -> bool:
        """
        登出

        Returns:
            bool: 登出是否成功
        """
        if not self.page:
            return False
        return await self.login_manager.logout(self.page)

    async def close(self):
        """
        关闭资源
        """
        await self.browser_manager.close()

    def _validate_draft_data(self, draft_data: Dict[str, Any]):
        """
        验证草稿数据

        Args:
            draft_data: 草稿数据

        Raises:
            ValidationError: 数据验证失败
        """
        # 检查必填字段
        if not draft_data.get('title'):
            raise ValidationError("标题不能为空")

        if not draft_data.get('content'):
            raise ValidationError("内容不能为空")

        # 检查标题长度（小红书标题限制20字）
        if len(draft_data['title']) > 20:
            raise ValidationError(f"标题过长（{len(draft_data['title'])}字），最多20字")

        # 检查图片数量（最多9张）
        images = draft_data.get('images', [])
        if len(images) > 9:
            raise ValidationError(f"图片数量过多（{len(images)}张），最多9张")

        # 检查图片文件是否存在
        for img_path in images:
            if not os.path.exists(img_path):
                raise ValidationError(f"图片文件不存在: {img_path}")

    async def _navigate_to_publish_page(self):
        """
        访问发布页面
        """
        try:
            current_url = self.page.url

            # 如果已经在发布页面，直接使用
            if '/publish/' in current_url:
                print(f"✓ 当前已在发布页面: {current_url}")
                return

            print("正在访问发布页面...")
            print(f"当前URL: {current_url}")

            # 如果在登录页，提示用户手动登录
            if '/login' in current_url.lower():
                print()
                print("=" * 60)
                print("⚠️  检测到登录页面")
                print("=" * 60)
                print("请在浏览器窗口中手动完成登录：")
                print("1. 点击浏览器中的登录按钮")
                print("2. 使用小红书APP扫码登录")
                print("3. 登录成功后，在发布页面点击「开始发布」")
                print("=" * 60)

                # 等待用户操作
                print()
                print("等待用户登录...（最长等待5分钟）")

                start_time = asyncio.get_event_loop().time()
                timeout = 300  # 5分钟

                while asyncio.get_event_loop().time() - start_time < timeout:
                    current_url = self.page.url
                    if '/publish/' in current_url:
                        print("✓ 已进入发布页面")
                        return
                    if 'login' not in current_url.lower() and 'creator.xiaohongshu.com' in current_url:
                        # 不在登录页，可能在主页
                        print("检测到已离开登录页，尝试访问发布页...")
                        await self.page.goto(
                            "https://creator.xiaohongshu.com/publish/publish",
                            wait_until='domcontentloaded',
                            timeout=30000
                        )
                        await asyncio.sleep(3)
                        if '/publish/' in self.page.url:
                            print("✓ 成功进入发布页面")
                            return

                    await asyncio.sleep(2)

                raise PublishFailedError("登录超时，请重新尝试")

            # 尝试直接访问发布页
            print("尝试访问发布页面...")
            await self.page.goto(
                "https://creator.xiaohongshu.com/publish/publish",
                wait_until='domcontentloaded',
                timeout=30000
            )
            await asyncio.sleep(3)

            current_url = self.page.url
            print(f"访问后URL: {current_url}")

            if '/login' in current_url.lower():
                # 被重定向到登录页，需要用户手动登录
                print()
                print("=" * 60)
                print("⚠️  需要手动登录")
                print("=" * 60)
                print("小红书检测到自动化访问，请在浏览器中手动登录：")
                print("1. 在浏览器窗口中点击登录")
                print("2. 使用小红书APP扫码")
                print("3. 登录成功后系统会自动继续")
                print("=" * 60)

                # 等待登录成功
                start_time = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start_time < 300:
                    if '/publish/' in self.page.url:
                        print("✓ 登录成功，已进入发布页面")
                        # 保存登录状态
                        await self.browser_manager.save_state()
                        return
                    await asyncio.sleep(2)

                raise PublishFailedError("等待登录超时")

            if '/publish/' in current_url:
                print("✓ 成功进入发布页面")
                return

            raise PublishFailedError(f"未能进入发布页面，当前在: {current_url}")

        except PublishFailedError:
            raise
        except Exception as e:
            print(f"访问发布页面异常: {str(e)}")
            raise PublishFailedError(f"访问发布页面失败: {str(e)}")

    async def _upload_images(self, image_paths: List[str]):
        """
        上传图片

        Args:
            image_paths: 图片路径列表
        """
        if not image_paths:
            return

        try:
            # 查找文件上传输入框
            upload_input = await self.page.query_selector('input[type="file"][accept*="image"]')

            if not upload_input:
                # 尝试其他选择器
                upload_input = await self.page.query_selector('input[type="file"]')

            if not upload_input:
                raise UploadError("找不到图片上传按钮")

            # 上传图片
            await upload_input.set_input_files(image_paths)

            # 等待上传完成（观察上传成功标识）
            # 小红书上传成功后会显示缩略图
            await asyncio.sleep(3)  # 给上传一些时间

            # 等待上传完成标识（具体选择器需要根据实际页面调整）
            try:
                await self.page.wait_for_selector(
                    '.upload-item, .image-item, .note-image-item',
                    timeout=60000
                )
            except PlaywrightTimeoutError:
                # 上传可能比较慢，再等待一下
                await asyncio.sleep(5)

            print(f"成功上传 {len(image_paths)} 张图片")

        except Exception as e:
            raise UploadError(f"图片上传失败: {str(e)}")

    async def _fill_title(self, title: str):
        """
        填写标题

        Args:
            title: 标题文本
        """
        try:
            # 小红书的标题输入框可能是多种形式
            # 尝试多种选择器
            selectors = [
                'input[placeholder*="标题"]',
                'input[placeholder*="填写标题"]',
                '.title-input input',
                'input[class*="title"]'
            ]

            title_input = None
            for selector in selectors:
                title_input = await self.page.query_selector(selector)
                if title_input:
                    break

            if not title_input:
                # 如果找不到，尝试通过文本查找
                title_input = await self.page.query_selector('input[type="text"]')

            if not title_input:
                raise PublishFailedError("找不到标题输入框")

            # 清空并填写标题
            await title_input.fill(title)

            await asyncio.sleep(0.5)

            print(f"填写标题: {title}")

        except Exception as e:
            raise PublishFailedError(f"填写标题失败: {str(e)}")

    async def _fill_content(self, content: str):
        """
        填写正文内容

        Args:
            content: 正文文本
        """
        try:
            # 小红书的正文输入框通常是 textarea 或可编辑的 div
            selectors = [
                'textarea[placeholder*="正文"]',
                'textarea[placeholder*="填写正文"]',
                '.content-input textarea',
                'textarea[class*="content"]',
                'div[contenteditable="true"]'  # 有些版本使用可编辑 div
            ]

            content_input = None
            for selector in selectors:
                content_input = await self.page.query_selector(selector)
                if content_input:
                    break

            if not content_input:
                # 如果找不到，尝试查找任意 textarea
                content_input = await self.page.query_selector('textarea')

            if not content_input:
                raise PublishFailedError("找不到正文输入框")

            # 清空并填写内容
            await content_input.fill(content)

            await asyncio.sleep(0.5)

            print(f"填写正文: {content[:50]}...")

        except Exception as e:
            raise PublishFailedError(f"填写正文失败: {str(e)}")

    async def _add_topics(self, topics: List[str]):
        """
        添加话题标签

        Args:
            topics: 话题标签列表
        """
        if not topics:
            return

        for topic in topics:
            try:
                # 清理话题（移除 # 符号）
                topic = topic.strip().replace('#', '')
                if not topic:
                    continue

                # 点击添加话题按钮
                add_topic_btn = await self.page.query_selector('text=添加话题')
                if not add_topic_btn:
                    # 尝试其他选择器
                    add_topic_btn = await self.page.query_selector(
                        'button:has-text("话题"), .add-topic-btn'
                    )

                if add_topic_btn:
                    await add_topic_btn.click()
                    await asyncio.sleep(0.5)

                # 输入话题
                topic_input = await self.page.query_selector(
                    'input[placeholder*="话题"], input[placeholder*="搜索"]'
                )

                if not topic_input:
                    # 如果没有单独的输入框，可能已经激活了搜索
                    topic_input = await self.page.query_selector('input[type="text"]:visible')

                if topic_input:
                    await topic_input.fill(topic)
                    await asyncio.sleep(1)

                    # 等待搜索结果出现
                    try:
                        await self.page.wait_for_selector(
                            '.topic-item, .topic-option, li:has-text("' + topic + '")',
                            timeout=5000
                        )

                        # 选择第一个匹配的话题
                        first_topic = await self.page.query_selector(
                            '.topic-item:first-child, .topic-option:first-child, li:first-child'
                        )
                        if first_topic:
                            await first_topic.click()
                            await asyncio.sleep(0.3)

                    except PlaywrightTimeoutError:
                        # 没有搜索结果，按回车确认
                        await topic_input.press('Enter')

                print(f"添加话题: #{topic}")

            except Exception as e:
                print(f"添加话题 '{topic}' 失败: {str(e)}")
                # 继续添加下一个话题
                continue

    async def _submit_publish(self) -> str:
        """
        提交发布

        Returns:
            str: 发布后的笔记链接
        """
        try:
            # 点击发布按钮
            publish_btn = await self.page.query_selector('button:has-text("发布")')

            if not publish_btn:
                # 尝试其他选择器
                publish_btn = await self.page.query_selector(
                    '.publish-btn, button[type="submit"]'
                )

            if not publish_btn:
                raise PublishFailedError("找不到发布按钮")

            await publish_btn.click()

            # 等待发布完成
            # 可能会跳转到笔记详情页或显示成功提示
            await asyncio.sleep(3)

            # 尝试等待页面跳转
            try:
                await self.page.wait_for_url(
                    lambda url: 'note' in url or 'explore' in url,
                    timeout=10000
                )
            except PlaywrightTimeoutError:
                pass

            # 获取发布后的 URL
            current_url = self.page.url

            # 如果 URL 包含笔记 ID，说明发布成功
            if 'note' in current_url or 'explore' in current_url:
                print(f"发布成功: {current_url}")
                return current_url

            # 检查是否有成功提示
            success_msg = await self.page.query_selector(
                'text=发布成功, text=已发布, .success-message'
            )

            if success_msg:
                print("发布成功（等待跳转）")
                # 等待跳转
                await asyncio.sleep(2)
                return self.page.url

            # 默认返回当前 URL
            return current_url

        except Exception as e:
            raise PublishFailedError(f"提交发布失败: {str(e)}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()