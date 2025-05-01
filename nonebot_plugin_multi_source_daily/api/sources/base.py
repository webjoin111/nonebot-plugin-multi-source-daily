from abc import ABC, abstractmethod

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message

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
        """初始化日报源

        Args:
            name: 日报源名称
            description: 日报源描述
            default_format: 默认格式
            formats: 支持的格式列表
            aliases: 别名列表
        """
        self.name = name
        self.description = description
        self.default_format = default_format
        self.formats = formats or ["image", "text"]
        self.aliases = aliases or []

    def validate_format(self, format_type: str) -> str:
        """验证格式类型

        Args:
            format_type: 格式类型

        Returns:
            验证后的格式类型

        Raises:
            FormatTypeException: 不支持的格式类型
        """
        if not format_type or format_type not in self.formats:
            return self.default_format
        return format_type

    async def fetch(
        self, format_type: str = None, force_refresh: bool = False
    ) -> Message:
        """获取日报内容

        Args:
            format_type: 格式类型
            force_refresh: 是否强制刷新

        Returns:
            日报内容

        Raises:
            FormatTypeException: 不支持的格式类型
        """
        format_type = self.validate_format(format_type)

        if not force_refresh:
            cached_data = news_cache.get(self.name, format_type)
            if cached_data:
                logger.debug(f"从缓存获取{self.name}日报，格式: {format_type}")
                return cached_data

        try:
            news_data = await self.fetch_data()

            if format_type == "image":
                message = await self.generate_image(news_data)
            elif format_type == "text":
                message = await self.generate_text(news_data)
            else:
                raise FormatTypeException(
                    format_type=format_type,
                    supported_formats=self.formats,
                )

            news_cache.set(self.name, format_type, message)

            return message
        except Exception as e:
            logger.error(f"获取{self.name}日报失败: {e}")
            return Message(f"获取{self.name}日报失败: {e}")

    @abstractmethod
    async def fetch_data(self) -> NewsData:
        """获取原始数据

        Returns:
            新闻数据
        """
        pass

    @abstractmethod
    async def generate_image(self, news_data: NewsData) -> Message:
        """生成图片格式的消息

        Args:
            news_data: 新闻数据

        Returns:
            图片格式的消息
        """
        pass

    @abstractmethod
    async def generate_text(self, news_data: NewsData) -> Message:
        """生成文本格式的消息

        Args:
            news_data: 新闻数据

        Returns:
            文本格式的消息
        """
        pass


news_sources: dict[str, BaseNewsSource] = {}


def register_news_source(source: BaseNewsSource) -> None:
    """注册日报源

    Args:
        source: 日报源
    """
    news_sources[source.name] = source

    for alias in source.aliases:
        if alias not in news_sources:
            news_sources[alias] = source
        else:
            logger.warning(
                f"别名 '{alias}' 已被使用，无法为 '{source.name}' 注册此别名"
            )


def get_news_source(name: str) -> BaseNewsSource | None:
    """获取日报源

    Args:
        name: 日报源名称或别名

    Returns:
        日报源，如果不存在则返回None
    """
    # 先尝试从现有源获取
    source = news_sources.get(name)
    if source:
        return source

    # 如果没有找到，尝试从适配器获取
    try:
        from ..adapter import get_adapter
        return get_adapter(name)
    except (ImportError, Exception) as e:
        logger.debug(f"从适配器获取新闻源失败: {e}")
        return None
