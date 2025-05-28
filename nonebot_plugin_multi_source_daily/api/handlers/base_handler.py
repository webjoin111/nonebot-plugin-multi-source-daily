from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message

from ...models import NewsData, NewsItem
from ...utils.screenshot import capture_webpage_screenshot


class BaseNewsHandler(ABC):
    """新闻源处理器基类"""

    def __init__(self, name: str, aliases: List[str] = None):
        """初始化新闻源处理器"""
        self.name = name
        self.aliases = aliases or []
        self._register()

    def _register(self):
        """注册处理器到工厂"""
        NewsHandlerFactory.register_handler(self)

    @abstractmethod
    async def fetch_news_data(self) -> NewsData:
        """获取新闻数据"""
        pass

    @abstractmethod
    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        pass

    @abstractmethod
    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        pass

    async def get_news_item_by_index(self, index: int) -> Optional[NewsItem]:
        """根据索引获取新闻项"""
        try:
            news_data = await self.fetch_news_data()

            for item in news_data.items:
                if item.index == index:
                    return item

            if 1 <= index <= len(news_data.items):
                return news_data.items[index - 1]

            return None
        except Exception as e:
            logger.error(f"获取新闻项失败: {e}")
            return None

    async def capture_news_screenshot(self, url: str) -> Optional[bytes]:
        """获取新闻网页截图"""
        return await capture_webpage_screenshot(url, site_type=self.name)


class NewsHandlerFactory:
    """新闻源处理器工厂"""

    _handlers: Dict[str, BaseNewsHandler] = {}
    _aliases: Dict[str, str] = {}

    @classmethod
    def register_handler(cls, handler: BaseNewsHandler):
        """注册处理器"""
        handler_name_lower = handler.name.lower()
        cls._handlers[handler_name_lower] = handler

        for alias in handler.aliases:
            alias_lower = alias.lower()
            cls._aliases[alias_lower] = handler_name_lower

        if handler.name.lower() == "ithome":
            special_aliases = ["it", "IT"]
            for special_alias in special_aliases:
                cls._aliases[special_alias] = handler_name_lower

        if handler.name == "知乎日报":
            pass

    @classmethod
    def get_handler(cls, name: str) -> Optional[BaseNewsHandler]:
        """获取处理器"""
        if name.upper() == "IT":
            return cls._handlers.get("ithome")

        if name == "知乎日报":
            return cls._handlers.get("知乎日报")

        name_lower = name.lower()

        if name_lower in cls._handlers:
            return cls._handlers[name_lower]

        if name_lower in cls._aliases:
            return cls._handlers[cls._aliases[name_lower]]

        if name_lower == "it":
            return cls._handlers.get("ithome")

        if name_lower == "知乎日报":
            return cls._handlers.get("知乎日报")

        return None

    @classmethod
    def get_all_handlers(cls) -> Dict[str, BaseNewsHandler]:
        """获取所有处理器"""
        return cls._handlers.copy()
