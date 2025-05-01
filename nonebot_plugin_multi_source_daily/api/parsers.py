from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from nonebot import logger

from ..exceptions import APIResponseParseException
from ..models import NewsData, NewsItem


class ApiParser(ABC):
    """API解析器基类"""

    @abstractmethod
    async def parse(self, response: httpx.Response) -> NewsData:
        """解析API响应"""
        pass


class DefaultParser(ApiParser):
    """默认解析器"""

    async def parse(self, response: httpx.Response) -> NewsData:
        """解析API响应"""
        try:
            data = response.json()

            news_data = NewsData(
                title="日报",
                update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source=response.url.host,
            )

            if isinstance(data, dict):
                items = data.get("data", [])
                if isinstance(items, list):
                    for i, item in enumerate(items, 1):
                        if isinstance(item, dict):
                            title = item.get("title", "")
                            url = item.get("url", "")
                            if title:
                                news_data.add_item(
                                    NewsItem(
                                        title=title,
                                        url=url,
                                        index=i,
                                    )
                                )

            return news_data
        except Exception as e:
            logger.error(f"默认解析器解析失败: {e}")
            raise APIResponseParseException(
                message=f"默认解析器解析失败: {e}",
                parser="default",
            )


class VVHanZhihuParser(ApiParser):
    """VVHan知乎日报解析器"""

    async def parse(self, response: httpx.Response) -> NewsData:
        """解析API响应"""
        try:
            data = response.json()

            if not isinstance(data, dict) or data.get("success") != 1:
                raise APIResponseParseException(
                    message="API响应格式错误",
                    parser="vvhan",
                )

            news_data = NewsData(
                title="知乎日报",
                update_time=data.get(
                    "update_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ),
                source="知乎",
            )

            items = data.get("data", [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        title = item.get("title", "")
                        url = item.get("url", "")
                        index = item.get("index", 0)
                        if title:
                            news_data.add_item(
                                NewsItem(
                                    title=title,
                                    url=url,
                                    index=index,
                                )
                            )

            return news_data
        except Exception as e:
            logger.error(f"VVHan知乎日报解析器解析失败: {e}")
            raise APIResponseParseException(
                message=f"VVHan知乎日报解析器解析失败: {e}",
                parser="vvhan",
            )


class OIOWebZhihuParser(ApiParser):
    """OIOWeb知乎日报解析器"""

    async def parse(self, response: httpx.Response) -> NewsData:
        """解析API响应"""
        try:
            data = response.json()

            news_data = NewsData(
                title="知乎日报",
                update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source="知乎",
            )

            if isinstance(data, dict) and "data" in data:
                items = data["data"]
                if isinstance(items, list):
                    for i, item in enumerate(items, 1):
                        if isinstance(item, dict):
                            title = item.get("title", "")
                            url = item.get("url", "")
                            hot = item.get("hot", "")
                            if title:
                                news_data.add_item(
                                    NewsItem(
                                        title=title,
                                        url=url,
                                        index=i,
                                        hot=hot,
                                    )
                                )

            return news_data
        except Exception as e:
            logger.error(f"OIOWeb知乎日报解析器解析失败: {e}")
            raise APIResponseParseException(
                message=f"OIOWeb知乎日报解析器解析失败: {e}",
                parser="oioweb",
            )


class RssParser(ApiParser):
    """RSS解析器"""

    async def parse(self, response: httpx.Response) -> NewsData:
        """解析API响应"""
        try:
            import feedparser

            feed = feedparser.parse(response.text)

            news_data = NewsData(
                title=feed.feed.title if hasattr(feed.feed, "title") else "RSS日报",
                update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source=feed.feed.title if hasattr(feed.feed, "title") else "RSS",
            )

            for i, entry in enumerate(feed.entries[:20], 1):
                title = entry.title if hasattr(entry, "title") else ""
                url = entry.link if hasattr(entry, "link") else ""
                description = entry.description if hasattr(entry, "description") else ""
                pub_time = entry.published if hasattr(entry, "published") else ""

                if title:
                    news_data.add_item(
                        NewsItem(
                            title=title,
                            url=url,
                            index=i,
                            description=description,
                            pub_time=pub_time,
                        )
                    )

            return news_data
        except Exception as e:
            logger.error(f"RSS解析器解析失败: {e}")
            raise APIResponseParseException(
                message=f"RSS解析器解析失败: {e}",
                parser="rss",
            )


class BinaryImageParser(ApiParser):
    """二进制图片解析器"""

    async def parse(self, response: httpx.Response) -> NewsData:
        """解析API响应"""
        try:
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                raise APIResponseParseException(
                    message=f"响应不是图片，Content-Type: {content_type}",
                    parser="binary_image",
                )

            news_data = NewsData(
                title="图片日报",
                update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source=response.url.host,
            )

            news_data.add_item(
                NewsItem(
                    title="图片日报",
                    url=str(response.url),
                    index=1,
                    image_url=str(response.url),
                )
            )

            news_data.binary_data = response.content

            return news_data
        except Exception as e:
            logger.error(f"二进制图片解析器解析失败: {e}")
            raise APIResponseParseException(
                message=f"二进制图片解析器解析失败: {e}",
                parser="binary_image",
            )


class HistoryTodayParser(ApiParser):
    """历史上的今天解析器"""

    async def parse(self, response: httpx.Response) -> NewsData:
        """解析API响应"""
        try:
            data = response.json()
            logger.debug(f"历史上的今天API响应: {data}")

            today = datetime.now().strftime("%m月%d日")
            news_data = NewsData(
                title=f"历史上的今天 ({today})",
                update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source="历史上的今天",
            )

            if isinstance(data, dict) and "data" in data:
                items = data["data"]
                if isinstance(items, list):
                    if not items:
                        logger.warning("历史上的今天API返回的数据列表为空")
                        try:
                            import json
                            import os

                            backup_file = os.path.join("assets", "history_data.json")
                            if os.path.exists(backup_file):
                                with open(backup_file, "r", encoding="utf-8") as f:
                                    backup_data = json.load(f)
                                    if (
                                        isinstance(backup_data, dict)
                                        and "data" in backup_data
                                    ):
                                        items = backup_data["data"]
                                        logger.info(f"使用备用数据，共 {len(items)} 条")
                        except Exception as backup_e:
                            logger.error(f"加载备用数据失败: {backup_e}")

                    for i, item in enumerate(items[:20], 1):
                        if isinstance(item, dict):
                            title = item.get("title", "")
                            year = item.get("year", "")
                            description = item.get("description", "")

                            if not title and description:
                                title = description

                            if title:
                                full_title = f"{year}年：{title}" if year else title
                                news_data.add_item(
                                    NewsItem(
                                        title=full_title,
                                        index=i,
                                        description=description
                                        if description != title
                                        else "",
                                    )
                                )

            if not news_data.items:
                logger.warning("历史上的今天解析后没有有效数据")
                raise APIResponseParseException(
                    message="未获取到历史上的今天数据",
                    parser="history_today",
                )

            logger.info(f"历史上的今天解析成功，共 {len(news_data.items)} 条数据")
            return news_data
        except Exception as e:
            logger.error(f"历史上的今天解析器解析失败: {e}")
            raise APIResponseParseException(
                message=f"历史上的今天解析器解析失败: {e}",
                parser="history_today",
            )


PARSERS: dict[str, type[ApiParser]] = {
    "default": DefaultParser,
    "vvhan": VVHanZhihuParser,
    "oioweb": OIOWebZhihuParser,
    "rss": RssParser,
    "binary_image": BinaryImageParser,
    "history_today": HistoryTodayParser,
}


def get_parser(parser_name: str) -> ApiParser:
    """获取指定名称的解析器"""
    parser_class = PARSERS.get(parser_name)
    if parser_class is None:
        logger.warning(f"未找到解析器: {parser_name}，使用默认解析器")
        parser_class = DefaultParser
    return parser_class()
