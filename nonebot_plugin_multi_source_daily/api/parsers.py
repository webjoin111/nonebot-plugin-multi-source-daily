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
    """二进制图片或JSON解析器"""

    async def parse(self, response: httpx.Response) -> NewsData:
        """解析API响应"""
        try:
            content_type = response.headers.get("Content-Type", "")

            if content_type.startswith("application/json"):
                logger.debug("检测到JSON格式响应，尝试解析")
                try:
                    data = response.json()

                    news_data = NewsData(
                        title="60秒日报",
                        update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        source=response.url.host,
                    )

                    if isinstance(data, dict):
                        if "data" in data and isinstance(data["data"], list):
                            items = data["data"]
                            for i, item in enumerate(items, 1):
                                if isinstance(item, dict):
                                    title = item.get("title", "")
                                    description = item.get(
                                        "desc", item.get("description", "")
                                    )
                                    if title:
                                        news_data.add_item(
                                            NewsItem(
                                                title=title,
                                                description=description,
                                                index=i,
                                            )
                                        )
                        elif "news" in data and isinstance(data["news"], list):
                            items = data["news"]
                            for i, item in enumerate(items, 1):
                                if isinstance(item, dict):
                                    title = item.get("title", "")
                                    description = item.get(
                                        "desc", item.get("description", "")
                                    )
                                    if title:
                                        news_data.add_item(
                                            NewsItem(
                                                title=title,
                                                description=description,
                                                index=i,
                                            )
                                        )
                        else:
                            for i, (key, value) in enumerate(data.items(), 1):
                                if (
                                    isinstance(value, str)
                                    and key != "date"
                                    and key != "time"
                                ):
                                    news_data.add_item(
                                        NewsItem(
                                            title=value,
                                            index=i,
                                        )
                                    )

                    if not news_data.items:
                        logger.warning(f"JSON解析后没有有效数据: {data}")
                        raise APIResponseParseException(
                            message="JSON解析后没有有效数据",
                            parser="binary_image",
                        )

                    return news_data
                except Exception as json_e:
                    logger.error(f"JSON解析失败: {json_e}")
                    raise APIResponseParseException(
                        message=f"JSON解析失败: {json_e}",
                        parser="binary_image",
                    )

            elif content_type.startswith("image/"):
                logger.debug(f"检测到图片格式响应，Content-Type: {content_type}")

                if not response.content or len(response.content) == 0:
                    logger.error("图片响应内容为空")
                    raise APIResponseParseException(
                        message="图片响应内容为空",
                        parser="binary_image",
                    )

                news_data = NewsData(
                    title="每日60秒",
                    update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    source=response.url.host,
                )

                news_data.add_item(
                    NewsItem(
                        title="每日60秒读懂世界",
                        url=str(response.url),
                        index=1,
                        image_url=str(response.url),
                    )
                )

                try:
                    news_data.binary_data = response.content
                    logger.debug(
                        f"成功获取图片数据，大小: {len(response.content)} 字节"
                    )

                    if len(response.content) < 100:
                        logger.warning(
                            f"图片数据可能无效，大小仅为 {len(response.content)} 字节"
                        )
                except Exception as e:
                    logger.error(f"处理图片数据时出错: {e}")
                    raise APIResponseParseException(
                        message=f"处理图片数据时出错: {e}",
                        parser="binary_image",
                    )

                return news_data
            else:
                raise APIResponseParseException(
                    message=f"响应格式不支持，Content-Type: {content_type}",
                    parser="binary_image",
                )
        except Exception as e:
            logger.error(f"二进制图片/JSON解析器解析失败: {e}")
            raise APIResponseParseException(
                message=f"二进制图片/JSON解析器解析失败: {e}",
                parser="binary_image",
            )


class Viki60sJsonParser(ApiParser):
    """Viki 60s JSON解析器"""

    async def parse(self, response: httpx.Response) -> NewsData:
        """解析API响应"""
        try:
            data = response.json()
            logger.debug(f"Viki 60s API响应: {data}")

            if not isinstance(data, dict) or data.get("code") != 200:
                raise APIResponseParseException(
                    message="API响应格式错误或状态码不正确",
                    parser="viki_60s_json",
                )

            api_data = data.get("data", {})
            if not isinstance(api_data, dict):
                raise APIResponseParseException(
                    message="API数据格式错误",
                    parser="viki_60s_json",
                )

            date = api_data.get("date", datetime.now().strftime("%Y-%m-%d"))
            news_data = NewsData(
                title=f"每日60秒 ({date})",
                update_time=api_data.get("api_updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                source="60s-api.viki.moe",
            )

            # 获取新闻列表
            news_list = api_data.get("news", [])
            if isinstance(news_list, list):
                for i, news_item in enumerate(news_list, 1):
                    if isinstance(news_item, str) and news_item.strip():
                        news_data.add_item(
                            NewsItem(
                                title=news_item.strip(),
                                index=i,
                            )
                        )

            if not news_data.items:
                logger.warning("Viki 60s API解析后没有有效数据")
                raise APIResponseParseException(
                    message="未获取到60s新闻数据",
                    parser="viki_60s_json",
                )

            logger.info(f"Viki 60s API解析成功，共 {len(news_data.items)} 条数据")
            return news_data
        except Exception as e:
            logger.error(f"Viki 60s JSON解析器解析失败: {e}")
            raise APIResponseParseException(
                message=f"Viki 60s JSON解析器解析失败: {e}",
                parser="viki_60s_json",
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
    "viki_60s_json": Viki60sJsonParser,
    "history_today": HistoryTodayParser,
}


def get_parser(parser_name: str) -> ApiParser:
    """获取指定名称的解析器"""
    parser_class = PARSERS.get(parser_name)
    if parser_class is None:
        logger.warning(f"未找到解析器: {parser_name}，使用默认解析器")
        parser_class = DefaultParser
    return parser_class()
