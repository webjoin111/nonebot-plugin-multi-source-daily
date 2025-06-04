"""核心工具和存储模块"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, TypeVar, Generic

import httpx
from nonebot import logger, require

from .. import HAS_HTMLRENDER

if HAS_HTMLRENDER:
    from nonebot_plugin_htmlrender import template_to_pic

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

from ..config import config
from ..exceptions import (
    APIException,
    APITimeoutException,
    InvalidTimeFormatException,
)

T = TypeVar("T")


async def fetch_with_retry(
    url: str,
    max_retries: int = None,
    timeout: float = None,
    headers: dict[str, str] = None,
    params: dict[str, Any] = None,
) -> httpx.Response:
    """带重试的HTTP请求"""
    max_retries = max_retries or config.daily_news_max_retries
    timeout_seconds = timeout or config.daily_news_timeout

    retries = 0
    retry_delay = 1.0
    last_error = None

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    if headers:
        default_headers.update(headers)

    while retries <= max_retries:
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(
                    url,
                    headers=default_headers,
                    params=params,
                    follow_redirects=True,
                )

                if response.status_code != 200:
                    error = APIException(
                        message="API请求失败",
                        status_code=response.status_code,
                        api_url=url,
                    )
                    if response.status_code in [429, 500, 502, 503, 504]:
                        last_error = error
                        retries += 1
                        logger.warning(
                            f"服务器返回错误状态码 {response.status_code}，第{retries}次重试: {url}"
                        )

                        retry_after = response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            await asyncio.sleep(int(retry_after))
                        else:
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 1.5

                        continue
                    else:
                        raise error

                return response

        except httpx.TimeoutException:
            last_error = APITimeoutException(
                message="API请求超时",
                api_url=url,
                timeout=timeout_seconds,
            )
            retries += 1
            logger.warning(f"请求超时，第{retries}次重试: {url}")
            await asyncio.sleep(retry_delay)
            retry_delay *= 1.5

        except Exception as e:
            last_error = APIException(
                message=f"API请求失败: {e!s}",
                api_url=url,
            )
            retries += 1
            logger.warning(f"请求失败，第{retries}次重试: {url}, 错误: {e!s}")
            await asyncio.sleep(retry_delay)
            retry_delay *= 1.5

    raise last_error or APIException(f"请求失败，已重试{max_retries}次", api_url=url)


def parse_time(time_str: str) -> tuple[int, int]:
    """解析时间字符串为小时和分钟"""
    try:
        if ":" in time_str:
            hour, minute = time_str.split(":")
            return int(hour), int(minute)

        if len(time_str) == 4:
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            return hour, minute
        elif len(time_str) == 3:
            hour = int(time_str[0])
            minute = int(time_str[1:])
            return hour, minute
        else:
            raise InvalidTimeFormatException(time_str=time_str)
    except ValueError:
        raise InvalidTimeFormatException(time_str=time_str)


def validate_time(hour: int, minute: int) -> bool:
    """验证时间是否有效"""
    return 0 <= hour < 24 and 0 <= minute < 60


def format_time(hour: int, minute: int) -> str:
    """格式化时间"""
    return f"{hour:02d}:{minute:02d}"


def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_today_date() -> str:
    """获取今天的日期"""
    return datetime.now().strftime("%Y年%m月%d日")


async def render_news_to_image(
    news_data: Any,
    template_name: str,
    title: str,
    template_data: dict[str, Any] = None,
) -> bytes | None:
    """渲染新闻数据为图片"""
    if hasattr(news_data, "binary_data") and news_data.binary_data is not None:
        logger.debug(f"检测到二进制图片数据，大小: {len(news_data.binary_data)} 字节，直接使用")
        return news_data.binary_data

    if not HAS_HTMLRENDER:
        logger.warning("htmlrender插件不可用，无法渲染图片，将尝试使用文本模式")
        return None

    template_path = config.get_template_dir()
    template_path.mkdir(parents=True, exist_ok=True)

    data = {
        "title": title,
        "date": get_today_date(),
        "news_items": getattr(news_data, "items", []),
        "update_time": getattr(news_data, "update_time", get_current_time()),
    }

    if template_data:
        data.update(template_data)

    viewport = {"width": 800, "height": 600}
    if template_name == "ithome.html":
        viewport = {"width": 600, "height": 1000}
    elif template_name == "sixty_seconds.html":
        viewport = {"width": 520, "height": 600}

    try:
        pic = await template_to_pic(
            template_path=str(template_path),
            template_name=template_name,
            templates=data,
            pages={"viewport": viewport},
        )
        return pic
    except Exception as e:
        logger.error(f"渲染模板失败: {e}")
        try:
            pic = await template_to_pic(
                template_path=str(template_path),
                template_name=template_name,
                templates=data,
                pages={"viewport": viewport},
            )
            return pic
        except Exception as e2:
            logger.error(f"使用旧版参数渲染模板也失败: {e2}")
            return None


def generate_news_type_error(invalid_type: str, news_sources: dict[str, Any]) -> str:
    """生成友好的日报类型错误提示"""
    unique_sources = {}
    for name, source in news_sources.items():
        if source.name not in unique_sources:
            unique_sources[source.name] = source

    error_msg = f"未知的日报类型: {invalid_type}\n\n【可用的日报类型】\n"

    for name, source in unique_sources.items():
        error_msg += f"▶ {name}"
        if source.aliases:
            error_msg += f"（别名：{', '.join(source.aliases)}）"
        error_msg += "\n"

    return error_msg


class BaseStorage(Generic[T]):
    """基础存储类"""

    def __init__(self, file_name: str, default_value: T):
        """初始化存储

        Args:
            file_name: 存储文件名
            default_value: 默认值
        """
        self.file_name = file_name
        self.default_value = default_value
        self.storage_file = self._get_storage_file()
        self.data: T = self._load_data()

    def _get_storage_file(self) -> Path:
        """获取存储文件路径"""
        try:
            config_dir = store.get_plugin_config_dir()
        except (AttributeError, Exception):
            try:
                config_dir = store.get_config_dir("nonebot_plugin_multi_source_daily")
            except (AttributeError, Exception):
                config_dir = Path.home() / ".nonebot" / "nonebot_plugin_multi_source_daily" / "config"
                config_dir.mkdir(parents=True, exist_ok=True)

        return config_dir / self.file_name

    def _load_data(self) -> T:
        """加载数据"""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.storage_file.exists():
            self._save_data(self.default_value)
            return self.default_value

        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError:
            logger.error(f"解析存储文件失败: {self.storage_file}")

            backup_file = self.storage_file.with_suffix(f".bak.{int(time.time())}")
            try:
                import shutil

                shutil.copy2(self.storage_file, backup_file)
                logger.info(f"已将损坏的数据文件备份为: {backup_file}")
            except Exception as e:
                logger.error(f"备份损坏数据文件失败: {e}")

            self._save_data(self.default_value)
            return self.default_value
        except Exception as e:
            logger.error(f"加载存储数据失败: {e}")
            return self.default_value

    def _save_data(self, data: T) -> bool:
        """保存数据"""
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存存储数据失败: {e}")
            return False

    def save(self) -> bool:
        """保存当前数据"""
        return self._save_data(self.data)

    def reset(self) -> bool:
        """重置为默认值"""
        self.data = self.default_value
        return self.save()


class ScheduleStorage(BaseStorage[Dict[str, Dict[str, Dict[str, Any]]]]):
    """定时任务存储类"""

    def __init__(self):
        """初始化定时任务存储"""
        super().__init__("schedules.json", {})
        self._migrate_old_data()

    def _migrate_old_data(self) -> bool:
        """迁移旧数据：将'知乎'改为'知乎日报'"""
        migrated = False
        for group_id, schedules in self.data.items():
            if "知乎" in schedules:
                schedules["知乎日报"] = schedules["知乎"]
                del schedules["知乎"]
                migrated = True
                logger.info(f"已将群 {group_id} 的'知乎'定时任务迁移到'知乎日报'")

        if migrated:
            self.save()
            logger.info("定时任务数据迁移完成")

        return migrated

    def set_group_schedule(self, group_id: int, news_type: str, schedule_time: str, format_type: str) -> bool:
        """设置群组的定时任务配置"""
        group_id_str = str(group_id)
        if group_id_str not in self.data:
            self.data[group_id_str] = {}

        self.data[group_id_str][news_type] = {
            "schedule_time": schedule_time,
            "format_type": format_type,
        }
        return self.save()

    def remove_group_schedule(self, group_id: int, news_type: str) -> bool:
        """移除群组的特定日报类型的定时任务配置"""
        group_id_str = str(group_id)
        if group_id_str in self.data and news_type in self.data[group_id_str]:
            del self.data[group_id_str][news_type]
            if not self.data[group_id_str]:
                del self.data[group_id_str]
            return self.save()
        return False

    def get_group_schedules(self, group_id: int) -> Dict[str, Dict[str, Any]]:
        """获取群组的所有定时任务配置"""
        return self.data.get(str(group_id), {})

    def get_all_schedules(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """获取所有定时任务配置"""
        return self.data

    def get_group_schedule(self, group_id: int, news_type: str) -> Dict[str, Any] | None:
        """获取群组的特定日报类型的定时任务配置"""
        group_id_str = str(group_id)
        if group_id_str in self.data and news_type in self.data[group_id_str]:
            return self.data[group_id_str][news_type]
        return None

    def get_all_groups_by_news_type(self, news_type: str) -> list[str]:
        """获取订阅了特定日报类型的所有群组ID"""
        groups = []
        for group_id, schedules in self.data.items():
            if news_type in schedules:
                groups.append(group_id)
        return groups


class ApiStatusStorage(BaseStorage[Dict[str, Any]]):
    """API状态存储类"""

    def __init__(self):
        """初始化API状态存储"""
        super().__init__("api_status.json", {})


schedule_store = ScheduleStorage()
api_status_store = ApiStatusStorage()
