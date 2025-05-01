"""新闻源处理器基类

定义新闻源处理器的基本接口和通用功能。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ...models import NewsData, NewsItem
from ...utils.screenshot import capture_webpage_screenshot


class BaseNewsHandler(ABC):
    """新闻源处理器基类"""

    def __init__(self, name: str, aliases: List[str] = None):
        """初始化新闻源处理器

        Args:
            name: 处理器名称
            aliases: 别名列表
        """
        self.name = name
        self.aliases = aliases or []
        self._register()

    def _register(self):
        """注册处理器到工厂"""
        NewsHandlerFactory.register_handler(self)

    @abstractmethod
    async def fetch_news_data(self) -> NewsData:
        """获取新闻数据

        Returns:
            新闻数据
        """
        pass

    @abstractmethod
    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息

        Args:
            news_data: 新闻数据

        Returns:
            图片格式的消息
        """
        pass

    @abstractmethod
    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息

        Args:
            news_data: 新闻数据

        Returns:
            文本格式的消息
        """
        pass

    async def get_news_item_by_index(self, index: int) -> Optional[NewsItem]:
        """根据索引获取新闻项

        Args:
            index: 新闻项索引

        Returns:
            新闻项或None
        """
        try:
            news_data = await self.fetch_news_data()
            
            # 先尝试精确匹配索引
            for item in news_data.items:
                if item.index == index:
                    return item
            
            # 如果没有精确匹配，尝试按位置获取
            if 1 <= index <= len(news_data.items):
                return news_data.items[index - 1]
            
            return None
        except Exception as e:
            logger.error(f"获取新闻项失败: {e}")
            return None

    async def capture_news_screenshot(self, url: str) -> Optional[bytes]:
        """获取新闻网页截图

        Args:
            url: 新闻URL

        Returns:
            截图数据或None
        """
        return await capture_webpage_screenshot(url, site_type=self.name)


class NewsHandlerFactory:
    """新闻源处理器工厂"""

    _handlers: Dict[str, BaseNewsHandler] = {}
    _aliases: Dict[str, str] = {}

    @classmethod
    def register_handler(cls, handler: BaseNewsHandler):
        """注册处理器

        Args:
            handler: 新闻源处理器
        """
        cls._handlers[handler.name.lower()] = handler
        
        # 注册别名
        for alias in handler.aliases:
            cls._aliases[alias.lower()] = handler.name.lower()

    @classmethod
    def get_handler(cls, name: str) -> Optional[BaseNewsHandler]:
        """获取处理器

        Args:
            name: 处理器名称或别名

        Returns:
            处理器或None
        """
        name = name.lower()
        
        # 先尝试直接获取
        if name in cls._handlers:
            return cls._handlers[name]
        
        # 尝试通过别名获取
        if name in cls._aliases:
            return cls._handlers[cls._aliases[name]]
        
        return None

    @classmethod
    def get_all_handlers(cls) -> Dict[str, BaseNewsHandler]:
        """获取所有处理器

        Returns:
            处理器字典
        """
        return cls._handlers.copy()
