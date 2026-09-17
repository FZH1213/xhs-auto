"""
发布器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None
    published_at: Optional[datetime] = None
    message: Optional[str] = None


class BasePublisher(ABC):
    """发布器基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化发布器

        Args:
            config: 配置字典
        """
        self.config = config

    @abstractmethod
    async def login(self) -> bool:
        """
        登录

        Returns:
            bool: 登录是否成功
        """
        pass

    @abstractmethod
    async def publish(self, draft_data: Dict[str, Any]) -> PublishResult:
        """
        发布内容

        Args:
            draft_data: 草稿数据，包含标题、内容、图片、话题等

        Returns:
            PublishResult: 发布结果
        """
        pass

    @abstractmethod
    async def check_login_status(self) -> bool:
        """
        检查登录状态

        Returns:
            bool: 是否已登录
        """
        pass

    @abstractmethod
    async def logout(self) -> bool:
        """
        登出

        Returns:
            bool: 登出是否成功
        """
        pass

    @abstractmethod
    async def close(self):
        """
        关闭资源
        """
        pass