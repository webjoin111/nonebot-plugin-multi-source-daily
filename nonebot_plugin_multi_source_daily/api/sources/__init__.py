from .base import BaseNewsSource, get_news_source, news_sources, register_news_source
from .history import HistoryNewsSource, history_source
from .ithome import ITHomeNewsSource, ithome_source
from .moyu import MoyuNewsSource, moyu_source
from .sixty_seconds import SixtySecondsNewsSource, sixty_seconds_source
from .zhihu import ZhihuNewsSource, ZhihuHotNewsSource, zhihu_source, zhihu_hot_source
from .weibo import WeiboHotNewsSource, weibo_hot_source

__all__ = [
    "BaseNewsSource",
    "HistoryNewsSource",
    "ITHomeNewsSource",
    "MoyuNewsSource",
    "SixtySecondsNewsSource",
    "ZhihuNewsSource",
    "ZhihuHotNewsSource",
    "WeiboHotNewsSource",
    "get_news_source",
    "history_source",
    "ithome_source",
    "moyu_source",
    "news_sources",
    "register_news_source",
    "sixty_seconds_source",
    "zhihu_source",
    "zhihu_hot_source",
    "weibo_hot_source",
]
