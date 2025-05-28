from abc import ABC, abstractmethod

from nonebot import logger, get_plugin_config
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ...config import Config
from ...exceptions import (
    FormatTypeException,
)
from ...models import NewsData
from ...utils import news_cache


class BaseNewsSource(ABC):
    """日报源基类"""

    def __init__(
        self,
        name: str,
        description: str,
        default_format: str = "image",
        formats: list[str] = None,
        aliases: list[str] = None,
    ):
        """初始化日报源"""
        self.name = name
        self.description = description
        self.formats = formats or ["image", "text"]
        self.default_format = default_format
        self.aliases = aliases or []

    def update_default_format(self):
        """更新默认格式，使用全局配置中的默认格式"""
        latest_config = get_plugin_config(Config)
        global_default_format = latest_config.daily_news_default_format

        if global_default_format in self.formats:
            self.default_format = global_default_format
            logger.debug(
                f"更新 {self.name} 日报源的默认格式为: {self.default_format} (来自全局配置)"
            )
        else:
            logger.debug(
                f"全局默认格式 {global_default_format} 不在 {self.name} 日报源支持的格式列表中，保持原默认格式: {self.default_format}"
            )

    def validate_format(self, format_type: str) -> str:
        """验证格式类型"""
        if not format_type or format_type not in self.formats:
            logger.debug(
                f"格式类型 {format_type} 无效或不支持，使用默认格式 {self.default_format}"
            )
            return self.default_format
        return format_type

    async def fetch(
        self, format_type: str = None, force_refresh: bool = False
    ) -> Message:
        """获取日报内容"""
        self.update_default_format()

        latest_config = get_plugin_config(Config)
        logger.debug(
            f"获取{self.name}日报，原始格式: {format_type}，全局默认格式: {latest_config.daily_news_default_format}，当前默认格式: {self.default_format}"
        )
        format_type = self.validate_format(format_type)
        logger.debug(f"验证后的格式: {format_type}")

        if not force_refresh:
            cached_data = news_cache.get(self.name, format_type)
            if cached_data:
                logger.debug(f"从缓存获取{self.name}日报，格式: {format_type}")
                return cached_data

        try:
            news_data = await self.fetch_data()

            if (
                format_type == "image"
                and hasattr(news_data, "binary_data")
                and news_data.binary_data
                and len(news_data.binary_data) > 0
            ):
                logger.debug("检测到二进制图片数据，直接使用")
                message = Message(MessageSegment.image(news_data.binary_data))

                if self._supports_detail():
                    display_name = self._get_detail_display_name()
                    message.append(display_name)
                    logger.debug(f"已为{self.name}日报添加显示名称: {display_name}")

                news_cache.set(self.name, format_type, message)

                return message

            if (
                not news_data
                or not hasattr(news_data, "items")
                or len(news_data.items) == 0
            ):
                logger.warning(f"获取{self.name}日报失败: 未获取到有效数据")
                return Message(f"获取{self.name}日报失败: 未获取到有效数据")

            if format_type == "image":
                message = await self.generate_image(news_data)
            elif format_type == "text":
                message = await self.generate_text(news_data)
            else:
                raise FormatTypeException(
                    format_type=format_type,
                    supported_formats=self.formats,
                )

            if message and len(message) > 0:
                if format_type == "image" and message[0].type == "image":
                    if self._supports_detail():
                        display_name = self._get_detail_display_name()
                        message.append(display_name)
                        logger.debug(f"已为{self.name}日报添加显示名称: {display_name}")

                news_cache.set(self.name, format_type, message)

            return message
        except Exception as e:
            logger.error(f"获取{self.name}日报失败: {e}")
            return Message(f"获取{self.name}日报失败: {e}")

    @abstractmethod
    async def fetch_data(self) -> NewsData:
        """获取原始数据"""
        pass

    @abstractmethod
    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息"""
        pass

    @abstractmethod
    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息"""
        pass

    def _supports_detail(self) -> bool:
        """检查是否支持详情功能"""
        detail_supported_types = ["ithome", "知乎日报"]
        return self.name in detail_supported_types

    def _get_detail_display_name(self) -> str:
        """获取详情功能的显示名称"""
        display_names = {
            "ithome": "IT之家",
            "知乎日报": "知乎日报"
        }
        return display_names.get(self.name, self.name)


news_sources: dict[str, BaseNewsSource] = {}


def register_news_source(source: BaseNewsSource) -> None:
    """注册日报源"""
    news_sources[source.name] = source

    for alias in source.aliases:
        if alias not in news_sources:
            news_sources[alias] = source
        else:
            logger.warning(
                f"别名 '{alias}' 已被使用，无法为 '{source.name}' 注册此别名"
            )


def get_news_source(name: str) -> BaseNewsSource | None:
    """获取日报源"""
    source = news_sources.get(name)
    if source:
        return source

    try:
        from ..adapter import get_adapter

        return get_adapter(name)
    except (ImportError, Exception) as e:
        logger.debug(f"从适配器获取新闻源失败: {e}")
        return None
