from nonebot.adapters.onebot.v11 import Message

from ...config import TemplateConfig, NewsLimits
from ...models import NewsData
from ...utils import get_today_date
from ..manager import api_manager
from .base import BaseNewsSource, register_news_source
from .mixins import ImageRenderMixin, TextFormatMixin, NewsItemProcessorMixin


class WeiboHotNewsSource(
    BaseNewsSource, ImageRenderMixin, TextFormatMixin, NewsItemProcessorMixin
):
    """微博热搜源"""

    def __init__(self):
        """初始化微博热搜源"""
        super().__init__(
            name="微博热搜",
            description="微博热搜榜热门话题",
            default_format="image",
            formats=["image", "text"],
        )

    async def fetch_data(self, api_index: int = None) -> NewsData:
        """获取原始数据"""
        return await api_manager.fetch_data(self.name, api_index=api_index)

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        news_data = self.process_news_items(
            news_data,
            max_items=NewsLimits.WEIBO_HOT_IMAGE_MAX_ITEMS,
            ensure_index=True,
            ensure_url=True,
        )

        return await self.render_with_fallback(
            news_data,
            TemplateConfig.TEMPLATES["微博热搜"],
            f"微博热搜 ({get_today_date()})",
            {"date": get_today_date()},
        )

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        return self.format_text_with_limit(
            news_data,
            f"微博热搜 ({get_today_date()})",
            max_items=NewsLimits.WEIBO_HOT_TEXT_MAX_ITEMS,
            title_max_length=NewsLimits.TITLE_MAX_LENGTH,
            show_url=True,
            show_detail_hint=True,
        )


weibo_hot_source = WeiboHotNewsSource()
register_news_source(weibo_hot_source)
