from nonebot.adapters.onebot.v11 import Message

from ...config import TemplateConfig, NewsLimits
from ...models import NewsData
from ...utils import get_today_date
from ..manager import api_manager
from .base import BaseNewsSource, register_news_source
from .mixins import TextFormatMixin, ImageSizeOptimizationMixin


class ITHomeNewsSource(BaseNewsSource, TextFormatMixin, ImageSizeOptimizationMixin):
    """IT之家日报源"""

    def __init__(self):
        """初始化IT之家日报源"""
        super().__init__(
            name="IT之家",
            description="IT之家科技新闻日报",
            default_format="image",
            formats=["image", "text"],
            aliases=["it之家", "it", "IT"],
        )

    async def fetch_data(self, api_index: int = None) -> NewsData:
        """获取原始数据"""
        return await api_manager.fetch_data(self.name, api_index=api_index)

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        try:
            return await self.render_with_size_optimization(
                news_data,
                TemplateConfig.TEMPLATES["IT之家"],
                f"IT之家日报 ({get_today_date()})",
                {"date": get_today_date()},
                max_size_mb=1.0,
                size_reduction_steps=[15, 10, 5],
            )
        except Exception as e:
            from nonebot import logger

            logger.error(f"IT之家日报图片生成失败: {e}")
            return await self.generate_text(news_data)

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        return self.format_text_with_limit(
            news_data,
            f"IT之家日报 ({get_today_date()})",
            max_items=NewsLimits.ZHIHU_TEXT_MAX_ITEMS,
            title_max_length=NewsLimits.TITLE_MAX_LENGTH,
            show_url=True,
            show_detail_hint=True,
        )


ithome_source = ITHomeNewsSource()
register_news_source(ithome_source)
