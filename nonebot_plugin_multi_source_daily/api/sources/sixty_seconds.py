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
        """获取原始数据"""
        from nonebot import logger, get_plugin_config
        from ...config import Config

        format_type = self.default_format
        config = get_plugin_config(Config)

        logger.debug(
            f"60s日报获取数据，当前默认格式: {format_type}, 全局默认格式: {config.daily_news_default_format}"
        )

        params = {}

        if config.daily_news_default_format == "text":
            if format_type == "image":
                try:
                    logger.debug("根据全局配置，先尝试获取JSON数据")
                    json_params = {"format": "json"}
                    news_data = await api_manager.fetch_data(self.name, json_params)

                    if (
                        news_data
                        and hasattr(news_data, "items")
                        and len(news_data.items) > 0
                    ):
                        logger.debug("成功获取JSON数据，将用于渲染图片")
                        return news_data

                    logger.debug("未获取到有效的JSON数据，回退到请求图片")
                except Exception as e:
                    logger.warning(f"获取JSON数据失败，回退到请求图片: {e}")

                params["format"] = "image"
            else:
                params["format"] = "json"
        else:
            if format_type == "text":
                params["format"] = "json"
            else:
                params["format"] = "image"

        logger.debug(f"60s日报请求参数: {params}")

        return await api_manager.fetch_data(self.name, params)

    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        from nonebot import logger

        if hasattr(news_data, "binary_data") and news_data.binary_data:
            logger.debug("检测到二进制图片数据，直接使用API返回的图片")
            try:
                if len(news_data.binary_data) > 0:
                    return Message(MessageSegment.image(news_data.binary_data))
                else:
                    logger.warning("二进制图片数据为空，回退到渲染文本")
            except Exception as e:
                logger.error(f"使用二进制图片数据失败: {e}，回退到渲染文本")

        logger.debug("未检测到二进制图片数据或使用失败，将文本渲染为图片")
        try:
            pic = await render_news_to_image(
                news_data,
                "sixty_seconds.html",
                f"每日60秒 ({get_today_date()})",
                {
                    "date": get_today_date(),
                },
            )

            if pic and len(pic) > 0:
                logger.debug(f"成功渲染图片，大小: {len(pic)} 字节")
                return Message(MessageSegment.image(pic))
            else:
                logger.error("渲染图片失败: 生成的图片数据为空")
                return Message("获取60秒日报失败: 生成的图片数据为空")
        except Exception as e:
            logger.error(f"渲染图片失败: {e}")
            return Message(f"获取60秒日报失败: {e}")

    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        message = Message(f"【每日60秒 ({get_today_date()})】\n\n")

        for i, item in enumerate(news_data.items, 1):
            message.append(f"{i}. {item.title}\n")
            if item.description:
                message.append(f"   {item.description}\n")
            message.append("\n")

        return message


sixty_seconds_source = SixtySecondsNewsSource()
register_news_source(sixty_seconds_source)
