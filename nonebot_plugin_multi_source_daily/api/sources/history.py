from nonebot.adapters.onebot.v11 import Message

from ...config import TemplateConfig
from ...models import NewsData
from ...utils import get_today_date
from ..manager import api_manager
from .base import BaseNewsSource, register_news_source
from .mixins import ImageRenderMixin, TextFormatMixin, NewsItemProcessorMixin


class HistoryNewsSource(BaseNewsSource, ImageRenderMixin, TextFormatMixin, NewsItemProcessorMixin):
    """历史上的今天日报源"""

    def __init__(self):
        """初始化历史上的今天日报源"""
        super().__init__(
            name="历史上的今天",
            description="历史上的今天发生的大事",
            default_format="image",
            formats=["image", "text"],
            aliases=[
                "历史",
                "today",
            ],
        )

    async def fetch_data(self) -> NewsData:
        """获取原始数据"""
        return await api_manager.fetch_data(self.name)

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        # 处理新闻条目
        news_data = self.process_news_items(
            news_data,
            max_items=20,
            ensure_index=True,
            ensure_url=False
        )

        return await self.render_with_fallback(
            news_data,
            TemplateConfig.TEMPLATES["历史上的今天"],
            f"历史上的今天 ({get_today_date()})",
            {"date": get_today_date()}
        )

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        today = get_today_date().split("年")[1]
        return self.format_text_with_limit(
            news_data,
            f"历史上的今天 ({today})",
            max_items=20,
            title_max_length=60,
            show_description=False,
            show_url=False
        )


history_source = HistoryNewsSource()
register_news_source(history_source)
