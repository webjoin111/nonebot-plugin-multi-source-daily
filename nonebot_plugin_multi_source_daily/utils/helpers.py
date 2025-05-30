import asyncio
from datetime import datetime
from typing import Any

import httpx
from nonebot import logger

from .. import HAS_HTMLRENDER

if HAS_HTMLRENDER:
    from nonebot_plugin_htmlrender import template_to_pic

from ..config import config
from ..exceptions import (
    APIException,
    APITimeoutException,
    InvalidTimeFormatException,
)


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
        logger.debug(
            f"检测到二进制图片数据，大小: {len(news_data.binary_data)} 字节，直接使用"
        )
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
