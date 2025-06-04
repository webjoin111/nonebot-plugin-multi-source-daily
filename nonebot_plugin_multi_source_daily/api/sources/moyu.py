from nonebot.adapters.onebot.v11 import Message

from ...config import TemplateConfig
from ...models import NewsData
from ..manager import api_manager
from .base import BaseNewsSource, register_news_source
from .mixins import ImageRenderMixin


class MoyuNewsSource(BaseNewsSource, ImageRenderMixin):
    """摸鱼人日历日报源"""

    def __init__(self):
        """初始化摸鱼人日历日报源"""
        super().__init__(
            name="摸鱼日历",
            description="摸鱼人日历",
            default_format="image",
            formats=["image"],
            aliases=["摸鱼", "moyu"],
        )

    async def fetch_data(self, api_index: int = None) -> NewsData:
        """获取原始数据"""
        return await api_manager.fetch_data(self.name, api_index=api_index)

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        return await self.render_with_fallback(
            news_data, TemplateConfig.TEMPLATES["摸鱼日历"], "摸鱼人日历", {}
        )

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        return Message("摸鱼人日历仅支持图片格式，请使用 '日报 摸鱼 -f image' 命令获取")


moyu_source = MoyuNewsSource()
register_news_source(moyu_source)
