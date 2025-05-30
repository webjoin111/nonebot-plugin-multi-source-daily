import time
from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message

from ..config import config
from ..models import CacheItem


class NewsCache:
    """新闻缓存管理类"""

    def __init__(self, expire_time: int = None):
        """初始化缓存管理器"""
        self.cache: dict[str, CacheItem] = {}
        self.default_expire_time = expire_time or config.daily_news_cache_expire

    def get_cache_key(self, news_type: str, format_type: str, api_index: int = None) -> str:
        """生成缓存键"""
        if api_index is not None:
            return f"{news_type}:{format_type}:api{api_index}"
        return f"{news_type}:{format_type}"

    def get(self, news_type: str, format_type: str, api_index: int = None) -> Message | None:
        """获取缓存"""
        key = self.get_cache_key(news_type, format_type, api_index)
        if key in self.cache:
            cache_item = self.cache[key]
            if not cache_item.is_expired():
                return cache_item.data
            else:
                del self.cache[key]
                logger.debug(f"缓存已过期并被清理: {key}")
        return None

    def set(
        self,
        news_type: str,
        format_type: str,
        data: Message,
        expire_time: int | None = None,
        api_index: int = None,
    ) -> None:
        """设置缓存"""
        key = self.get_cache_key(news_type, format_type, api_index)
        expire_seconds = expire_time or self.default_expire_time
        expire_timestamp = time.time() + expire_seconds

        self.cache[key] = CacheItem(
            data=data,
            expire_time=expire_timestamp,
            created_at=time.time(),
        )

        logger.debug(f"已缓存 {key} 的数据，过期时间: {expire_seconds}秒")

    def delete(self, news_type: str, format_type: str, api_index: int = None) -> bool:
        """删除指定缓存"""
        key = self.get_cache_key(news_type, format_type, api_index)
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"已删除缓存: {key}")
            return True
        return False

    def delete_by_type(self, news_type: str) -> int:
        """删除指定类型的所有缓存"""
        count = 0
        keys_to_delete = []

        for key in self.cache:
            if key.startswith(f"{news_type}:"):
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self.cache[key]
            count += 1

        if count > 0:
            logger.debug(f"已删除 {news_type} 类型的 {count} 项缓存")

        return count

    def clear(self) -> int:
        """清空所有缓存"""
        count = len(self.cache)
        self.cache.clear()
        logger.debug(f"已清空所有缓存，共 {count} 项")
        return count

    def clear_expired(self) -> int:
        """清理过期缓存"""
        count = 0
        keys_to_delete = []

        for key, item in self.cache.items():
            if item.is_expired():
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self.cache[key]
            count += 1

        if count > 0:
            logger.debug(f"已清理 {count} 项过期缓存")

        return count

    def get_status(self) -> dict[str, Any]:
        """获取缓存状态"""
        types = {}
        for key in self.cache:
            news_type = key.split(":")[0]
            if news_type not in types:
                types[news_type] = 0
            types[news_type] += 1

        return {
            "total": len(self.cache),
            "types": types,
        }

    def get_detailed_status(self) -> dict[str, Any]:
        """获取详细缓存状态"""
        details = []

        for key, item in self.cache.items():
            parts = key.split(":")
            news_type = parts[0]
            format_type = parts[1]
            api_info = parts[2] if len(parts) > 2 else None

            detail_item = {
                "type": news_type,
                "format": format_type,
                "created_at": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(item.created_at)
                ),
                "expires_in": int(item.time_to_expire()),
            }

            if api_info:
                detail_item["api_source"] = api_info

            details.append(detail_item)

        return {
            "total": len(self.cache),
            "details": details,
        }


news_cache = NewsCache()
