from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ...models import NewsData
from ...utils import get_today_date, render_news_to_image
from ..manager import api_manager
from .base import BaseNewsSource, register_news_source


class HistoryNewsSource(BaseNewsSource):
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
                "历史事件",
                "历史上今天",
                "today",
                "history",
                "历史上的今",
            ],
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
            "history.html",
            f"历史上的今天 ({get_today_date()})",
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
        from nonebot import logger

        # 限制条目数量，避免消息过长
        max_items = 10
        if len(news_data.items) > max_items:
            logger.info(f"历史上的今天文本格式条目过多，限制为{max_items}条 (原有{len(news_data.items)}条)")
            news_data.items = news_data.items[:max_items]

        today = get_today_date().split("年")[1]  # 只取月日
        message = Message(f"【历史上的今天 ({today})】\n\n")

        for i, item in enumerate(news_data.items, 1):
            # 限制标题长度
            title = item.title
            if len(title) > 60:
                title = title[:57] + "..."

            message.append(f"{i}. {title}\n\n")

        return message


# 注册历史上的今天日报源
history_source = HistoryNewsSource()
register_news_source(history_source)
