from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ...models import NewsData
from ...utils import get_today_date, render_news_to_image
from ..manager import api_manager
from .base import BaseNewsSource, register_news_source


class SixtySecondsNewsSource(BaseNewsSource):
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

    async def fetch_data(self) -> NewsData:
        """获取原始数据

        Returns:
            新闻数据
        """
        return await api_manager.fetch_data(self.name)

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息

        Args:
            news_data: 新闻数据

        Returns:
            图片格式的消息
        """
        # 渲染模板
        pic = await render_news_to_image(
            news_data,
            "sixty_seconds.html",
            f"每日60秒 ({get_today_date()})",
            {
                "date": get_today_date(),
            },
        )

        return Message(MessageSegment.image(pic))

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息

        Args:
            news_data: 新闻数据

        Returns:
            文本格式的消息
        """
        message = Message(f"【每日60秒 ({get_today_date()})】\n\n")

        for i, item in enumerate(news_data.items, 1):
            message.append(f"{i}. {item.title}\n")
            if item.description:
                message.append(f"   {item.description}\n")
            message.append("\n")

        return message


# 注册60秒日报源
sixty_seconds_source = SixtySecondsNewsSource()
register_news_source(sixty_seconds_source)
