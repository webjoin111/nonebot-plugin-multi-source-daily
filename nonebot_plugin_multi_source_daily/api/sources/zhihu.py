from nonebot.adapters.onebot.v11 import Message

from ...config import TemplateConfig, NewsLimits
from ...models import NewsData
from ...utils import get_today_date
from ..manager import api_manager
from .base import BaseNewsSource, register_news_source
from .mixins import ImageRenderMixin, TextFormatMixin, NewsItemProcessorMixin


class ZhihuNewsSource(
    BaseNewsSource, ImageRenderMixin, TextFormatMixin, NewsItemProcessorMixin
):
    """知乎日报源"""

    def __init__(self):
        """初始化知乎日报源"""
        super().__init__(
            name="知乎日报",
            description="知乎日报热门文章",
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
            max_items=NewsLimits.ZHIHU_IMAGE_MAX_ITEMS,
            ensure_index=True,
            ensure_url=True,
        )

        return await self.render_with_fallback(
            news_data,
            TemplateConfig.TEMPLATES["知乎日报"],
            f"知乎日报 ({get_today_date()})",
            {"date": get_today_date()},
        )

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        return self.format_text_with_limit(
            news_data,
            f"知乎日报 ({get_today_date()})",
            max_items=NewsLimits.ZHIHU_TEXT_MAX_ITEMS,
            title_max_length=NewsLimits.TITLE_MAX_LENGTH,
            show_url=True,
            show_detail_hint=True,
        )


class ZhihuHotNewsSource(
    BaseNewsSource, ImageRenderMixin, TextFormatMixin, NewsItemProcessorMixin
):
    """知乎热榜源"""

    def __init__(self):
        """初始化知乎热榜源"""
        super().__init__(
            name="知乎热榜",
            description="知乎热榜热门话题",
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
            max_items=NewsLimits.ZHIHU_HOT_IMAGE_MAX_ITEMS,
            ensure_index=True,
            ensure_url=True,
        )

        return await self.render_with_fallback(
            news_data,
            TemplateConfig.TEMPLATES["知乎热榜"],
            f"知乎热榜 ({get_today_date()})",
            {"date": get_today_date()},
        )

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        return self.format_text_with_limit(
            news_data,
            f"知乎热榜 ({get_today_date()})",
            max_items=NewsLimits.ZHIHU_HOT_TEXT_MAX_ITEMS,
            title_max_length=NewsLimits.TITLE_MAX_LENGTH,
            show_url=True,
            show_detail_hint=True,
        )


zhihu_source = ZhihuNewsSource()
zhihu_hot_source = ZhihuHotNewsSource()
register_news_source(zhihu_source)
register_news_source(zhihu_hot_source)
