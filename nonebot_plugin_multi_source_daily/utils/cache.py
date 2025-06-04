import hashlib
import time
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta

from nonebot import logger, get_plugin_config
from nonebot.adapters.onebot.v11 import Message

from ..config import config, Config
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
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item.created_at)),
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


class FileCache:
    """通用文件缓存工具类"""

    def __init__(self, cache_subdir: str, expire_hours: int = 24, enabled: bool = True):
        """初始化缓存工具"""
        self.cache_subdir = cache_subdir
        self.expire_hours = expire_hours
        self.enabled = enabled
        self._cache_dir = None

    def _get_cache_dir(self) -> Path:
        """获取缓存目录"""
        if self._cache_dir is None:
            plugin_config = get_plugin_config(Config)
            cache_dir = plugin_config.get_cache_dir() / self.cache_subdir
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_dir = cache_dir
            logger.debug(f"缓存目录: {cache_dir}")

        return self._cache_dir

    def _get_cache_key(self, key: str) -> str:
        """生成缓存键"""
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def _get_cache_file_path(self, cache_key: str, extension: str = "cache") -> Path:
        """获取缓存文件路径"""
        return self._get_cache_dir() / f"{cache_key}.{extension}"

    def _is_cache_valid(self, cache_file: Path) -> bool:
        """检查缓存是否有效"""
        if not cache_file.exists():
            return False

        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        expire_time = datetime.now() - timedelta(hours=self.expire_hours)

        return file_time > expire_time

    def get(self, key: str, extension: str = "cache") -> Optional[bytes]:
        """从缓存获取数据"""
        if not self.enabled:
            return None

        try:
            cache_key = self._get_cache_key(key)
            cache_file = self._get_cache_file_path(cache_key, extension)

            if self._is_cache_valid(cache_file):
                with open(cache_file, "rb") as f:
                    data = f.read()
                logger.debug(f"从缓存加载: {cache_file}")
                return data
            else:
                if cache_file.exists():
                    cache_file.unlink()
                    logger.debug(f"删除过期缓存: {cache_file}")

        except Exception as e:
            logger.warning(f"从缓存加载失败: {e}")

        return None

    def set(self, key: str, data: bytes, extension: str = "cache") -> bool:
        """保存数据到缓存"""
        if not self.enabled:
            return False

        try:
            cache_key = self._get_cache_key(key)
            cache_file = self._get_cache_file_path(cache_key, extension)

            with open(cache_file, "wb") as f:
                f.write(data)

            logger.debug(f"数据已缓存: {cache_file}")
            return True

        except Exception as e:
            logger.warning(f"保存到缓存失败: {e}")
            return False

    def delete(self, key: str, extension: str = "cache") -> bool:
        """删除指定缓存"""
        try:
            cache_key = self._get_cache_key(key)
            cache_file = self._get_cache_file_path(cache_key, extension)

            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"删除缓存: {cache_file}")
                return True

        except Exception as e:
            logger.warning(f"删除缓存失败: {e}")

        return False

    def cleanup_expired(self) -> int:
        """清理过期的缓存文件"""
        try:
            cache_dir = self._get_cache_dir()
            expire_time = datetime.now() - timedelta(hours=self.expire_hours)

            cleaned_count = 0
            for cache_file in cache_dir.iterdir():
                if cache_file.is_file():
                    try:
                        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                        if file_time <= expire_time:
                            cache_file.unlink()
                            cleaned_count += 1
                    except Exception as e:
                        logger.debug(f"清理缓存文件失败: {cache_file}, {e}")

            if cleaned_count > 0:
                logger.debug(f"清理了 {cleaned_count} 个过期的缓存文件")

            return cleaned_count

        except Exception as e:
            logger.warning(f"清理过期缓存失败: {e}")
            return 0

    def clear_all(self) -> int:
        """清理所有缓存文件"""
        try:
            cache_dir = self._get_cache_dir()
            cleaned_count = 0

            for cache_file in cache_dir.iterdir():
                if cache_file.is_file():
                    try:
                        cache_file.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.debug(f"删除缓存文件失败: {cache_file}, {e}")

            logger.info(f"清理了 {cleaned_count} 个缓存文件")
            return cleaned_count

        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return 0

    def get_cache_info(self) -> dict:
        """获取缓存信息"""
        try:
            cache_dir = self._get_cache_dir()

            if not cache_dir.exists():
                return {
                    "cache_dir": str(cache_dir),
                    "cache_subdir": self.cache_subdir,
                    "total_files": 0,
                    "total_size": 0,
                    "total_size_mb": 0.0,
                    "valid_files": 0,
                    "expired_files": 0,
                    "expire_hours": self.expire_hours,
                    "enabled": self.enabled,
                }

            total_files = 0
            total_size = 0
            valid_files = 0
            expired_files = 0

            expire_time = datetime.now() - timedelta(hours=self.expire_hours)

            for cache_file in cache_dir.iterdir():
                if cache_file.is_file():
                    try:
                        total_files += 1
                        total_size += cache_file.stat().st_size

                        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                        if file_time > expire_time:
                            valid_files += 1
                        else:
                            expired_files += 1

                    except Exception as e:
                        logger.debug(f"检查缓存文件失败: {cache_file}, {e}")

            return {
                "cache_dir": str(cache_dir),
                "cache_subdir": self.cache_subdir,
                "total_files": total_files,
                "total_size": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "valid_files": valid_files,
                "expired_files": expired_files,
                "expire_hours": self.expire_hours,
                "enabled": self.enabled,
            }

        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            return {"error": str(e), "cache_subdir": self.cache_subdir, "enabled": self.enabled}


screenshot_cache = FileCache("screenshots", expire_hours=24)
weibo_screenshot_cache = FileCache("weibo_screenshots", expire_hours=24)
news_data_cache = FileCache("news_data", expire_hours=1)
api_response_cache = FileCache("api_responses", expire_hours=6)
