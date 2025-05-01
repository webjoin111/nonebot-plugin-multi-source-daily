from .base_handler import BaseNewsHandler, NewsHandlerFactory
from .ithome_handler import ithome_handler
from .zhihu_handler import zhihu_handler

__all__ = [
    "BaseNewsHandler",
    "NewsHandlerFactory",
    "get_news_handler",
    "get_all_handlers",
    "ithome_handler",
    "zhihu_handler",
]


def get_news_handler(name: str):
    """获取新闻处理器"""
    if name.upper() == "IT":
        return ithome_handler

    if name == "知乎":
        return zhihu_handler

    handler = NewsHandlerFactory.get_handler(name)
    if handler:
        return handler

    handler = NewsHandlerFactory.get_handler(name.lower())
    if handler:
        return handler

    handler = NewsHandlerFactory.get_handler(name.capitalize())
    if handler:
        return handler

    return None


def get_all_handlers():
    """获取所有处理器"""
    return NewsHandlerFactory.get_all_handlers()
