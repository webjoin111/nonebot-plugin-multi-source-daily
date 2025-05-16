from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ...models import NewsData
from ...utils import render_news_to_image
from ..manager import api_manager
from .base import BaseNewsSource, register_news_source


class MoyuNewsSource(BaseNewsSource):
    """摸鱼人日历日报源"""

    def __init__(self):
        """初始化摸鱼人日历日报源"""
        super().__init__(
            name="moyu",
            description="摸鱼人日历",
            default_format="image",
            formats=["image"],
            aliases=["摸鱼", "摸鱼人", "摸鱼日历", "摸鱼日报"],
        )

    async def fetch_data(self) -> NewsData:
        """获取原始数据"""
        return await api_manager.fetch_data(self.name)

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        from nonebot import logger

        if hasattr(news_data, "binary_data") and news_data.binary_data is not None:
            logger.debug("检测到二进制图片数据，直接使用API返回的图片")
            return Message(MessageSegment.image(news_data.binary_data))

        logger.debug("未检测到二进制图片数据，将文本渲染为图片")

        pic = await render_news_to_image(
            news_data,
            "moyu.html",
            "摸鱼人日历",
            {},
        )

        if pic:
            logger.debug(f"成功渲染摸鱼人日历图片，大小: {len(pic)} 字节")
            return Message(MessageSegment.image(pic))
        else:
            logger.error("渲染摸鱼人日历图片失败：未获取到图片数据")
            return Message("获取摸鱼人日历失败：未获取到图片数据")

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        return Message("摸鱼人日历仅支持图片格式，请使用 '日报 摸鱼 -f image' 命令获取")


moyu_source = MoyuNewsSource()
register_news_source(moyu_source)
