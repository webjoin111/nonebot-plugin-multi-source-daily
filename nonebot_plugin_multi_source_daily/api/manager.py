import time
from typing import Any

from nonebot import logger

from ..config import config
from ..exceptions import (
    APIException,
    APIResponseParseException,
    NoAvailableAPIException,
)
from ..models import ApiSource, NewsData
from ..utils import fetch_with_retry
from .parsers import get_parser


class ApiManager:
    """API管理器"""

    def __init__(self):
        """初始化API管理器"""
        self.api_sources: dict[str, list[ApiSource]] = {}
        self.api_status: dict[str, dict[str, Any]] = {}

    def register_api_source(self, news_type: str, api_source: ApiSource) -> None:
        """注册API源"""
        if news_type not in self.api_sources:
            self.api_sources[news_type] = []

        for source in self.api_sources[news_type]:
            if source.url == api_source.url:
                return

        self.api_sources[news_type].append(api_source)

        if news_type not in self.api_status:
            self.api_status[news_type] = {}

        self.api_status[news_type][api_source.url] = {
            "enabled": api_source.enabled,
            "last_success": api_source.last_success,
            "failure_count": api_source.failure_count,
        }

    def register_api_sources(
        self, news_type: str, api_sources: list[ApiSource]
    ) -> None:
        """注册多个API源"""
        for api_source in api_sources:
            self.register_api_source(news_type, api_source)

    def get_api_sources(self, news_type: str) -> list[ApiSource]:
        """获取指定日报类型的API源列表"""
        return self.api_sources.get(news_type, [])

    def get_enabled_api_sources(self, news_type: str) -> list[ApiSource]:
        """获取指定日报类型的已启用API源列表"""
        sources = self.get_api_sources(news_type)
        return [source for source in sources if source.enabled]

    def get_api_source(self, news_type: str, url: str) -> ApiSource | None:
        """获取指定URL的API源"""
        for source in self.get_api_sources(news_type):
            if source.url == url:
                return source
        return None

    def enable_api_source(self, news_type: str, url: str) -> bool:
        """启用API源"""
        source = self.get_api_source(news_type, url)
        if source:
            source.enabled = True
            if news_type in self.api_status and url in self.api_status[news_type]:
                self.api_status[news_type][url]["enabled"] = True
            return True
        return False

    def disable_api_source(self, news_type: str, url: str) -> bool:
        """禁用API源"""
        source = self.get_api_source(news_type, url)
        if source:
            source.enabled = False
            if news_type in self.api_status and url in self.api_status[news_type]:
                self.api_status[news_type][url]["enabled"] = False
            return True
        return False

    def reset_api_source(self, news_type: str, url: str) -> bool:
        """重置API源状态"""
        source = self.get_api_source(news_type, url)
        if source:
            source.enabled = True
            source.failure_count = 0
            source.last_success = 0

            if news_type in self.api_status and url in self.api_status[news_type]:
                self.api_status[news_type][url] = {
                    "enabled": True,
                    "last_success": 0,
                    "failure_count": 0,
                }
            return True
        return False

    def reset_api_sources(self, news_type: str) -> int:
        """重置指定日报类型的所有API源状态"""
        count = 0
        for source in self.get_api_sources(news_type):
            if self.reset_api_source(news_type, source.url):
                count += 1
        return count

    def reset_all_api_sources(self) -> int:
        """重置所有API源状态"""
        count = 0
        for news_type in self.api_sources:
            count += self.reset_api_sources(news_type)
        return count

    def update_api_source_status(self, news_type: str, url: str, success: bool) -> None:
        """更新API源状态"""
        source = self.get_api_source(news_type, url)
        if not source:
            return

        if success:
            source.last_success = time.time()
            source.failure_count = 0
        else:
            source.failure_count += 1

            if source.failure_count >= config.daily_news_max_retries * 2:
                source.enabled = False
                logger.warning(f"API源 {url} 失败次数过多，已自动禁用")

        if news_type in self.api_status and url in self.api_status[news_type]:
            self.api_status[news_type][url] = {
                "enabled": source.enabled,
                "last_success": source.last_success,
                "failure_count": source.failure_count,
            }

    def get_best_api_source(self, news_type: str) -> ApiSource | None:
        """获取最佳API源"""
        sources = self.get_enabled_api_sources(news_type)
        if not sources:
            return None

        sources.sort(key=lambda x: x.priority)

        if sources[0].last_success > 0:
            return sources[0]

        return sources[0]

    async def fetch_data(self, news_type: str, extra_params: dict = None) -> NewsData:
        """获取数据

        Args:
            news_type: 日报类型
            extra_params: 额外的请求参数
        """
        source = self.get_best_api_source(news_type)
        if not source:
            raise NoAvailableAPIException(news_type=news_type)

        parser = get_parser(source.parser)

        # 记录是否启用了故障转移
        failover_enabled = config.daily_news_auto_failover
        logger.debug(
            f"日报类型: {news_type}, 主API源: {source.url}, 故障转移已{'启用' if failover_enabled else '禁用'}"
        )

        try:
            # 解析URL中可能已经包含的查询参数
            url = source.url
            params = {}

            # 添加额外的请求参数
            if extra_params:
                params.update(extra_params)
                logger.debug(f"添加额外请求参数: {extra_params}")

            # 如果URL中已经包含查询参数，不再额外添加
            logger.debug(f"尝试请求主API源: {url}, 参数: {params}")

            response = await fetch_with_retry(
                url,
                max_retries=config.daily_news_max_retries,
                timeout=config.daily_news_timeout,
                params=params,
            )

            try:
                news_data = await parser.parse(response)

                self.update_api_source_status(news_type, source.url, True)
                logger.debug(f"成功从API源 {source.url} 获取 {news_type} 日报数据")

                return news_data
            except Exception as e:
                self.update_api_source_status(news_type, source.url, False)

                logger.error(f"API响应解析失败: {e}")

                # 如果启用了故障转移，尝试其他API源
                if failover_enabled:
                    logger.warning(f"API源 {source.url} 响应解析失败，尝试其他API源")
                    return await self._try_failover_sources(
                        news_type, source.url, extra_params
                    )

                raise APIResponseParseException(
                    message=f"API响应解析失败: {e}",
                    api_url=source.url,
                    parser=source.parser,
                )
        except APIException as e:
            self.update_api_source_status(news_type, source.url, False)
            logger.error(f"API请求失败: {e}")

            # 如果启用了故障转移，尝试其他API源
            if failover_enabled:
                logger.warning(f"API源 {source.url} 请求失败，尝试其他API源")
                return await self._try_failover_sources(
                    news_type, source.url, extra_params
                )
            else:
                logger.warning("故障转移已禁用，不尝试其他API源")
                raise
        except Exception as e:
            self.update_api_source_status(news_type, source.url, False)
            logger.error(f"获取数据时发生未知错误: {e}")

            # 如果启用了故障转移，尝试其他API源
            if failover_enabled:
                logger.warning(f"API源 {source.url} 发生未知错误，尝试其他API源")
                return await self._try_failover_sources(
                    news_type, source.url, extra_params
                )
            else:
                raise

    async def _try_failover_sources(
        self, news_type: str, failed_url: str, extra_params: dict = None
    ) -> NewsData:
        """尝试使用备用API源

        Args:
            news_type: 日报类型
            failed_url: 失败的API源URL
            extra_params: 额外的请求参数
        """
        other_sources = [
            s for s in self.get_enabled_api_sources(news_type) if s.url != failed_url
        ]

        if not other_sources:
            logger.error(f"没有可用的备用API源，日报类型: {news_type}")
            raise NoAvailableAPIException(news_type=news_type)

        other_sources.sort(key=lambda x: x.priority)
        logger.info(f"找到 {len(other_sources)} 个备用API源，将按优先级尝试")

        for other_source in other_sources:
            try:
                other_parser = get_parser(other_source.parser)
                logger.info(
                    f"尝试备用API源: {other_source.url}, 优先级: {other_source.priority}"
                )

                # 解析URL中可能已经包含的查询参数
                url = other_source.url
                params = {}

                # 添加额外的请求参数
                if extra_params:
                    params.update(extra_params)
                    logger.debug(f"添加额外请求参数: {extra_params}")

                # 如果URL中已经包含查询参数，不再额外添加
                logger.debug(f"尝试请求备用API源: {url}, 参数: {params}")

                other_response = await fetch_with_retry(
                    url,
                    max_retries=config.daily_news_max_retries,
                    timeout=config.daily_news_timeout,
                    params=params,
                )

                try:
                    news_data = await other_parser.parse(other_response)

                    self.update_api_source_status(news_type, other_source.url, True)
                    logger.info(
                        f"成功从备用API源 {other_source.url} 获取 {news_type} 日报数据"
                    )

                    return news_data
                except Exception as parse_e:
                    self.update_api_source_status(news_type, other_source.url, False)
                    logger.error(
                        f"备用API源 {other_source.url} 响应解析失败: {parse_e}"
                    )
            except Exception as other_e:
                self.update_api_source_status(news_type, other_source.url, False)
                logger.error(f"备用API源 {other_source.url} 请求失败: {other_e}")

        logger.error(f"所有备用API源都失败，日报类型: {news_type}")
        raise NoAvailableAPIException(news_type=news_type)

    def get_api_status(self, news_type: str | None = None) -> dict[str, Any]:
        """获取API状态"""
        if news_type:
            result = {
                "news_type": news_type,
                "sources": [],
            }

            for source in self.get_api_sources(news_type):
                result["sources"].append(
                    {
                        "url": source.url,
                        "enabled": source.enabled,
                        "last_success": source.last_success,
                        "failure_count": source.failure_count,
                        "priority": source.priority,
                        "parser": source.parser,
                    }
                )

            return result
        else:
            result = {}

            for news_type in self.api_sources:
                result[news_type] = self.get_api_status(news_type)

            return result


api_manager = ApiManager()


def init_api_sources():
    """从配置中初始化API源"""
    api_manager.register_api_sources("60s", config.daily_news_60s_apis)

    api_manager.register_api_sources("知乎", config.daily_news_zhihu_apis)

    api_manager.register_api_sources("moyu", config.daily_news_moyu_apis)

    api_manager.register_api_sources("ithome", config.daily_news_ithome_apis)

    api_manager.register_api_sources("历史上的今天", config.daily_news_history_apis)
