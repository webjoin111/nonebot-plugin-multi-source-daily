from nonebot import logger, get_plugin_config
from nonebot.adapters.onebot.v11 import Message

from ...config import Config, TemplateConfig, NewsLimits
from ...models import NewsData
from ...utils import get_today_date
from ..manager import api_manager
from .base import BaseNewsSource, register_news_source
from .mixins import ImageRenderMixin, TextFormatMixin, ConfigurableFormatMixin


class SixtySecondsNewsSource(
    BaseNewsSource, ImageRenderMixin, TextFormatMixin, ConfigurableFormatMixin
):
    """60秒日报源"""

    def __init__(self):
        """初始化60秒日报源"""
        super().__init__(
            name="60s",
            description="每日60秒读懂世界",
            default_format="image",
            formats=["image", "text"],
            aliases=["60秒", "早报", "每日60秒", "60s日报", "60秒日报"],
        )

    async def fetch_data(self, api_index: int = None) -> NewsData:
        """获取原始数据"""
        config = get_plugin_config(Config)

        logger.debug(
            f"60s日报获取数据，当前默认格式: {self.default_format}, 全局默认格式: {config.daily_news_default_format}"
        )

        if api_index is not None:
            return await api_manager.fetch_data(self.name, api_index=api_index)
        else:
            return await self.fetch_with_format_fallback(
                api_manager,
                self.default_format,
                config.daily_news_default_format,
                api_index,
            )

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        return await self.render_with_fallback(
            news_data,
            TemplateConfig.TEMPLATES["60s"],
            f"每日60秒 ({get_today_date()})",
            {"date": get_today_date()},
        )

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        return self.format_text_with_limit(
            news_data,
            f"每日60秒 ({get_today_date()})",
            max_items=NewsLimits.DEFAULT_TEXT_MAX_ITEMS,
            show_description=True,
        )


sixty_seconds_source = SixtySecondsNewsSource()
register_news_source(sixty_seconds_source)
