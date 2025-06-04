from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ..models import NewsData, NewsItem
from ..utils import get_today_date, render_news_to_image
from ..utils.screenshot import capture_webpage_screenshot
from .manager import api_manager


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

    def _process_news_items(self, news_data: NewsData, max_items: int = None) -> NewsData:
        """处理新闻条目的通用逻辑"""
        if max_items and len(news_data.items) > max_items:
            logger.info(f"{self.name}条目过多，限制为{max_items}条 (原有{len(news_data.items)}条)")
            news_data.items = news_data.items[:max_items]

        for i, item in enumerate(news_data.items):
            if not item.index:
                item.index = i + 1
            if not item.url:
                item.url = "#"

        return news_data

    async def _generate_standard_image(
        self, news_data: NewsData, template_name: str, max_items: int = 15, fallback_to_text: bool = True
    ) -> Message:
        """生成标准图片格式的消息"""
        try:
            news_data = self._process_news_items(news_data, max_items)

            pic = await render_news_to_image(
                news_data,
                template_name,
                f"{self.name} ({get_today_date()})",
                {"date": get_today_date()},
            )

            if len(pic) > 1024 * 1024:
                logger.warning(f"{self.name}图片过大: {len(pic) / 1024 / 1024:.2f}MB，尝试减少条目")
                news_data = self._process_news_items(news_data, max_items // 2)
                pic = await render_news_to_image(
                    news_data,
                    template_name,
                    f"{self.name} ({get_today_date()})",
                    {"date": get_today_date()},
                )

            return Message(MessageSegment.image(pic))
        except Exception as e:
            logger.error(f"{self.name}图片生成失败: {e}")
            if fallback_to_text:
                return await self.generate_text(news_data)
            raise

    async def _generate_standard_text(
        self, news_data: NewsData, max_items: int = 8, title_max_length: int = 50
    ) -> Message:
        """生成标准文本格式的消息"""
        if len(news_data.items) > max_items:
            logger.info(f"{self.name}文本格式条目过多，限制为{max_items}条 (原有{len(news_data.items)}条)")
            news_data.items = news_data.items[:max_items]

        message = Message(f"【{self.name} ({get_today_date()})】\n\n")

        for i, item in enumerate(news_data.items, 1):
            title = item.title
            if len(title) > title_max_length:
                title = title[: title_max_length - 3] + "..."

            message.append(f"{i}. {title}\n")

            if item.url:
                message.append(f"   链接: {item.url}\n")

            message.append("\n")

        message.append("提示: 回复数字可查看对应新闻的网页截图\n")
        message.append("例如: 回复 1 查看第一条新闻\n")

        return message


class NewsHandlerFactory:
    """新闻源处理器工厂"""

    _handlers: Dict[str, BaseNewsHandler] = {}
    _aliases: Dict[str, str] = {}

    @classmethod
    def register_handler(cls, handler: BaseNewsHandler):
        """注册处理器"""
        cls._handlers[handler.name] = handler

        for alias in handler.aliases:
            cls._aliases[alias] = handler.name

    @classmethod
    def get_handler(cls, name: str) -> Optional[BaseNewsHandler]:
        """获取处理器"""
        if name in cls._handlers:
            return cls._handlers[name]

        if name in cls._aliases:
            return cls._handlers[cls._aliases[name]]

        return None

    @classmethod
    def get_all_handlers(cls) -> Dict[str, BaseNewsHandler]:
        """获取所有处理器"""
        return cls._handlers.copy()


class ITHomeNewsHandler(BaseNewsHandler):
    """IT之家新闻处理器"""

    def __init__(self):
        """初始化IT之家新闻处理器"""
        super().__init__(
            name="IT之家",
            aliases=["ithome", "it之家", "it", "IT"],
        )

    async def fetch_news_data(self) -> NewsData:
        """获取新闻数据"""
        return await api_manager.fetch_data(self.name)

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        return await self._generate_standard_image(news_data, "ithome.html")

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        return await self._generate_standard_text(news_data)


class ZhihuNewsHandler(BaseNewsHandler):
    """知乎日报处理器"""

    def __init__(self):
        """初始化知乎日报处理器"""
        super().__init__(
            name="知乎日报",
            aliases=[],
        )

    async def fetch_news_data(self) -> NewsData:
        """获取新闻数据"""
        return await api_manager.fetch_data(self.name)

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        return await self._generate_standard_image(news_data, "zhihu.html")

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        return await self._generate_standard_text(news_data)


try:
    from ..config import config
    from ..utils.weibo import get_weibo_detail

    class WeiboHotNewsHandler(BaseNewsHandler):
        """微博热搜处理器"""

        def __init__(self):
            super().__init__(
                name="微博热搜",
                aliases=["weibo", "微博", "热搜"],
            )

        async def fetch_news_data(self) -> NewsData:
            return await api_manager.fetch_data(self.name)

        async def generate_image(self, news_data: NewsData) -> Message:
            return await self._generate_standard_image(news_data, "weibo_hot.html")

        async def generate_text(self, news_data: NewsData) -> Message:
            return await self._generate_standard_text(news_data)

        async def get_news_item_by_index(self, index: int) -> NewsItem | None:
            try:
                news_data = await self.fetch_news_data()
                if not news_data.items or index < 1 or index > len(news_data.items):
                    return None
                return news_data.items[index - 1]
            except Exception as e:
                logger.error(f"获取微博热搜条目失败: {e}")
                return None

        async def get_news_detail(self, news_item: NewsItem) -> str | None:
            if not news_item.url:
                return "该热搜条目没有可访问的链接"

            if not config.weibo_cookie.strip():
                return "微博详情功能需要配置Cookie，请联系管理员配置 WEIBO_COOKIE 环境变量"

            try:
                detail_content = await get_weibo_detail(news_item.url)
                if detail_content:
                    return detail_content
                else:
                    return "获取微博详情失败，可能是Cookie已失效或链接无效"
            except Exception as e:
                logger.error(f"获取微博详情时发生错误: {e}")
                return f"获取微博详情时发生错误: {str(e)}"

        async def capture_news_screenshot(self, url: str) -> Optional[bytes]:
            """获取微博新闻网页截图"""
            try:
                from ..utils.screenshot import capture_weibo_screenshot, WeiboScreenshotError

                try:
                    return await capture_weibo_screenshot(url, raise_on_error=True)
                except WeiboScreenshotError as e:
                    logger.warning(f"微博截图失败: {e}")
                    if "Cookie" in str(e):
                        logger.error("微博Cookie配置问题，无法进行微博截图")
                        return None
                    logger.info("尝试使用通用截图功能")
                    return await super().capture_news_screenshot(url)
            except ImportError:
                logger.warning("微博截图模块不可用，回退到通用截图")
                return await super().capture_news_screenshot(url)

        def supports_detail(self) -> bool:
            return True

    weibo_hot_handler = WeiboHotNewsHandler()
    _weibo_available = True
except ImportError as e:
    logger.warning(f"微博处理器初始化失败: {e}")
    weibo_hot_handler = None
    _weibo_available = False


ithome_handler = ITHomeNewsHandler()
zhihu_handler = ZhihuNewsHandler()

__all__ = [
    "BaseNewsHandler",
    "NewsHandlerFactory",
    "get_news_handler",
    "get_all_handlers",
    "ithome_handler",
    "zhihu_handler",
]

if _weibo_available:
    __all__.append("weibo_hot_handler")


def get_news_handler(name: str):
    """获取新闻处理器"""
    if name.upper() == "IT":
        return ithome_handler

    if name == "知乎日报":
        return zhihu_handler

    if name == "微博热搜" and _weibo_available:
        return weibo_hot_handler

    handler = NewsHandlerFactory.get_handler(name)
    if handler:
        return handler

    handler = NewsHandlerFactory.get_handler(name.lower())
    if handler:
        return handler

    handler = NewsHandlerFactory.get_handler(name.capitalize())
    if handler:
        return handler

    return None


def get_all_handlers():
    """获取所有处理器"""
    return NewsHandlerFactory.get_all_handlers()
