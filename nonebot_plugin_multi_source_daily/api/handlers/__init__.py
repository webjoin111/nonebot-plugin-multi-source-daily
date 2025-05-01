# 导入处理器相关类和函数
from .base_handler import BaseNewsHandler, NewsHandlerFactory
# 显式导入所有处理器，确保它们被初始化
from .ithome_handler import ithome_handler
from .zhihu_handler import zhihu_handler
# 导入其他处理器...

__all__ = [
    "BaseNewsHandler",
    "NewsHandlerFactory",
    "get_news_handler",
    "get_all_handlers",
    "ithome_handler",
    "zhihu_handler",
]

def get_news_handler(name: str):
    """获取新闻处理器

    Args:
        name: 处理器名称或别名

    Returns:
        处理器或None
    """
    # 特殊处理常见的情况
    if name.upper() == "IT":
        return ithome_handler

    if name == "知乎":
        return zhihu_handler

    # 首先尝试直接获取
    handler = NewsHandlerFactory.get_handler(name)
    if handler:
        return handler

    # 尝试使用小写
    handler = NewsHandlerFactory.get_handler(name.lower())
    if handler:
        return handler

    # 尝试使用首字母大写
    handler = NewsHandlerFactory.get_handler(name.capitalize())
    if handler:
        return handler

    return None


def get_all_handlers():
    """获取所有处理器

    Returns:
        处理器字典
    """
    return NewsHandlerFactory.get_all_handlers()
