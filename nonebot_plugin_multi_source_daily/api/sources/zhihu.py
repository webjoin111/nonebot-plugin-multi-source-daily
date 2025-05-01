from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ...models import NewsData
from ...utils import get_today_date, render_news_to_image
from ..manager import api_manager
from .base import BaseNewsSource, register_news_source


class ZhihuNewsSource(BaseNewsSource):
    """知乎日报源"""

    def __init__(self):
        """初始化知乎日报源"""
        super().__init__(
            name="知乎",
            description="知乎日报热门文章",
            default_format="image",
            formats=["image", "text"],
            aliases=["知乎日报", "知乎热榜", "zhihu"],
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
        from nonebot import logger

        # 限制条目数量为15条
        if len(news_data.items) > 15:
            logger.info(
                f"知乎日报条目过多，限制为15条 (原有{len(news_data.items)}条)"
            )
            news_data.items = news_data.items[:15]

        # 确保每个条目都有索引
        for i, item in enumerate(news_data.items):
            if not item.index:
                item.index = i + 1
            if not item.url:
                item.url = "#"

        # 渲染模板
        pic = await render_news_to_image(
            news_data,
            "zhihu.html",
            f"知乎日报 ({get_today_date()})",
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
        max_items = 8
        if len(news_data.items) > max_items:
            logger.info(f"知乎日报文本格式条目过多，限制为{max_items}条 (原有{len(news_data.items)}条)")
            news_data.items = news_data.items[:max_items]

        message = Message(f"【知乎日报 ({get_today_date()})】\n\n")

        for i, item in enumerate(news_data.items, 1):
            # 限制标题长度
            title = item.title
            if len(title) > 50:
                title = title[:47] + "..."

            message.append(f"{i}. {title}\n")

            # 只添加链接，不添加热度信息
            if item.url:
                message.append(f"   链接: {item.url}\n")

            message.append("\n")

        # 添加提示
        message.append("提示: 回复数字可查看对应新闻的网页截图\n")
        message.append("例如: 回复 1 查看第一条新闻\n")

        return message


# 注册知乎日报源
zhihu_source = ZhihuNewsSource()
register_news_source(zhihu_source)
