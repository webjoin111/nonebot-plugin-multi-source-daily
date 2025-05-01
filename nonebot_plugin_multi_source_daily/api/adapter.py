from nonebot import logger
from nonebot.adapters.onebot.v11 import Message

from ..models import NewsData
from .handlers import get_all_handlers, get_news_handler
from .sources.base import BaseNewsSource


class NewsSourceAdapter(BaseNewsSource):
    """新闻源适配器，将新的处理器架构适配到旧的API接口"""

    def __init__(self, handler_name: str):
        """初始化适配器"""
        self.handler = get_news_handler(handler_name)
        if not self.handler:
            raise ValueError(f"未找到处理器: {handler_name}")

        super().__init__(
            name=self.handler.name,
            description=f"{self.handler.name}新闻源",
            default_format="image",
            formats=["image", "text"],
            aliases=self.handler.aliases,
        )

    async def fetch_data(self) -> NewsData:
        """获取原始数据"""
        return await self.handler.fetch_news_data()

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        return await self.handler.generate_image(news_data)

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        return await self.handler.generate_text(news_data)


_adapters: dict[str, NewsSourceAdapter] = {}


def get_adapter(name: str) -> NewsSourceAdapter | None:
    """获取适配器"""
    if name.lower() in _adapters:
        return _adapters[name.lower()]

    try:
        adapter = NewsSourceAdapter(name)
        _adapters[name.lower()] = adapter
        return adapter
    except Exception as e:
        logger.error(f"创建适配器失败: {e}")
        return None


def get_all_adapters() -> list[NewsSourceAdapter]:
    """获取所有适配器"""
    for name in get_all_handlers().keys():
        if name.lower() not in _adapters:
            try:
                _adapters[name.lower()] = NewsSourceAdapter(name)
            except Exception as e:
                logger.error(f"创建适配器失败: {e}")

    return list(_adapters.values())
