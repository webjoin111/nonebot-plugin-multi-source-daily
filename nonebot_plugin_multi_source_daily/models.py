from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from nonebot.adapters.onebot.v11 import Message


@dataclass
class NewsItem:
    """新闻项数据模型"""

    title: str
    url: str = ""
    index: int = 0
    hot: str = ""
    description: str = ""
    image_url: str = ""
    pub_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "url": self.url,
            "index": self.index,
            "hot": self.hot,
            "description": self.description,
            "image_url": self.image_url,
            "pub_time": self.pub_time,
        }


@dataclass
class NewsData:
    """新闻数据集合"""

    title: str
    items: list[NewsItem] = field(default_factory=list)
    update_time: str = ""
    source: str = ""

    def __post_init__(self):
        """初始化后处理"""
        if not self.update_time:
            self.update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def add_item(self, item: NewsItem) -> None:
        """添加新闻项"""
        self.items.append(item)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "items": [item.to_dict() for item in self.items],
            "update_time": self.update_time,
            "source": self.source,
        }


@dataclass
class ApiSource:
    """API源配置"""

    url: str
    priority: int = 1
    parser: str = "default"
    enabled: bool = True
    last_success: float = 0
    failure_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "url": self.url,
            "priority": self.priority,
            "parser": self.parser,
            "enabled": self.enabled,
            "last_success": self.last_success,
            "failure_count": self.failure_count,
        }


class NewsSourceProtocol(Protocol):
    """日报源协议"""

    async def fetch(
        self, format_type: str = "image", force_refresh: bool = False
    ) -> Message:
        """获取日报内容"""
        ...


@dataclass
class NewsSource:
    """日报源定义"""

    name: str
    description: str
    fetch_func: Callable[[dict[str, Any]], Awaitable[Message]]
    default_format: str = "image"
    api_url: str = ""
    formats: list[str] = field(default_factory=lambda: ["image", "text"])
    aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "default_format": self.default_format,
            "api_url": self.api_url,
            "formats": self.formats,
            "aliases": self.aliases,
        }


@dataclass
class ScheduleConfig:
    """定时任务配置"""

    schedule_time: str
    format_type: str = "image"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "schedule_time": self.schedule_time,
            "format_type": self.format_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleConfig":
        """从字典创建实例"""
        return cls(
            schedule_time=data.get("schedule_time", "00:00"),
            format_type=data.get("format_type", "image"),
        )


@dataclass
class CacheItem:
    """缓存项"""

    data: Message
    expire_time: float
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())

    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now().timestamp() > self.expire_time

    def time_to_expire(self) -> float:
        """获取剩余过期时间（秒）"""
        now = datetime.now().timestamp()
        return max(0, self.expire_time - now)


@dataclass
class ApiStatus:
    """API状态"""

    url: str
    enabled: bool
    last_success: datetime | None = None
    failure_count: int = 0
    priority: int = 1
    parser: str = "default"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "url": self.url,
            "enabled": self.enabled,
            "last_success": self.last_success.isoformat()
            if self.last_success
            else None,
            "failure_count": self.failure_count,
            "priority": self.priority,
            "parser": self.parser,
        }


@dataclass
class NewsTypeInfo:
    """日报类型信息"""

    name: str
    description: str
    default_format: str
    formats: list[str]
    aliases: list[str]
    api_sources: list[ApiStatus] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "default_format": self.default_format,
            "formats": self.formats,
            "aliases": self.aliases,
            "api_sources": [source.to_dict() for source in self.api_sources],
        }
