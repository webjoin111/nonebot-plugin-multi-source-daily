from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ...models import NewsData
from ...utils import get_today_date, render_news_to_image
from ..manager import api_manager
from .base_handler import BaseNewsHandler


class ITHomeNewsHandler(BaseNewsHandler):
    """IT之家新闻处理器"""

    def __init__(self):
        """初始化IT之家新闻处理器"""
        super().__init__(
            name="ithome",
            aliases=["it之家", "IT之家", "it", "IT"],
        )

    async def fetch_news_data(self) -> NewsData:
        """获取新闻数据

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
        try:
            if len(news_data.items) > 15:
                logger.info(
                    f"IT之家日报条目过多，限制为15条 (原有{len(news_data.items)}条)"
                )
                news_data.items = news_data.items[:15]

            for i, item in enumerate(news_data.items):
                if not item.index:
                    item.index = i + 1
                if not item.url:
                    item.url = "#"

            pic = await render_news_to_image(
                news_data,
                "ithome.html",
                f"IT之家日报 ({get_today_date()})",
                {
                    "date": get_today_date(),
                },
            )

            if len(pic) > 1024 * 1024:
                logger.warning(
                    f"IT之家日报图片过大: {len(pic) / 1024 / 1024:.2f}MB，尝试减少条目"
                )
                news_data.items = news_data.items[:10]
                pic = await render_news_to_image(
                    news_data,
                    "ithome.html",
                    f"IT之家日报 ({get_today_date()})",
                    {
                        "date": get_today_date(),
                    },
                )

                if len(pic) > 1024 * 1024:
                    logger.warning(
                        f"IT之家日报图片仍然过大: {len(pic) / 1024 / 1024:.2f}MB，进一步减少条目"
                    )
                    news_data.items = news_data.items[:5]
                    pic = await render_news_to_image(
                        news_data,
                        "ithome.html",
                        f"IT之家日报 ({get_today_date()})",
                        {
                            "date": get_today_date(),
                        },
                    )

            return Message(MessageSegment.image(pic))
        except Exception as e:
            logger.error(f"IT之家日报图片生成失败: {e}")
            return await self.generate_text(news_data)

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息

        Args:
            news_data: 新闻数据

        Returns:
            文本格式的消息
        """
        max_items = 8
        if len(news_data.items) > max_items:
            logger.info(
                f"IT之家日报文本格式条目过多，限制为{max_items}条 (原有{len(news_data.items)}条)"
            )
            news_data.items = news_data.items[:max_items]

        message = Message(f"【IT之家日报 ({get_today_date()})】\n\n")

        for i, item in enumerate(news_data.items, 1):
            title = item.title
            if len(title) > 50:
                title = title[:47] + "..."

            message.append(f"{i}. {title}\n")

            if item.url:
                message.append(f"   链接: {item.url}\n")

            message.append("\n")

        message.append("提示: 回复数字可查看对应新闻的网页截图\n")
        message.append("例如: 回复 1 查看第一条新闻\n")

        return message


ithome_handler = ITHomeNewsHandler()
