"""新闻处理器模块

包含各种新闻源的处理器实现。
"""

from .base_handler import BaseNewsHandler, NewsHandlerFactory
from .ithome_handler import ITHomeNewsHandler
from .zhihu_handler import ZhihuNewsHandler

# 导出工厂和基类
__all__ = ["BaseNewsHandler", "NewsHandlerFactory", "get_news_handler", "get_all_handlers"]


def get_news_handler(name: str):
    """获取新闻处理器

    Args:
        name: 处理器名称或别名

    Returns:
        处理器或None
    """
    return NewsHandlerFactory.get_handler(name)


def get_all_handlers():
    """获取所有处理器

    Returns:
        处理器字典
    """
    return NewsHandlerFactory.get_all_handlers()
