from abc import ABC
from typing import Any, Optional

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from ...models import NewsData
from ...utils import get_today_date, render_news_to_image


class ImageRenderMixin(ABC):
    """图片渲染混入类"""

    async def render_with_fallback(
        self,
        news_data: NewsData,
        template_name: str,
        title: str,
        extra_data: Optional[dict[str, Any]] = None,
        max_items: Optional[int] = None,
    ) -> Message:
        """统一的图片渲染逻辑，支持二进制数据回退和条目限制"""
        if hasattr(news_data, "binary_data") and news_data.binary_data:
            logger.debug("检测到二进制图片数据，直接使用API返回的图片")
            try:
                if len(news_data.binary_data) > 0:
                    return Message(MessageSegment.image(news_data.binary_data))
                else:
                    logger.warning("二进制图片数据为空，回退到渲染文本")
            except Exception as e:
                logger.error(f"使用二进制图片数据失败: {e}，回退到渲染文本")

        if max_items and len(news_data.items) > max_items:
            logger.info(
                f"{self.name}条目过多，限制为{max_items}条 (原有{len(news_data.items)}条)"
            )
            news_data.items = news_data.items[:max_items]

        logger.debug("未检测到二进制图片数据或使用失败，将文本渲染为图片")
        try:
            template_data = {"date": get_today_date()}
            if extra_data:
                template_data.update(extra_data)

            pic = await render_news_to_image(
                news_data,
                template_name,
                title,
                template_data,
            )

            if pic and len(pic) > 0:
                logger.debug(f"成功渲染图片，大小: {len(pic)} 字节")
                return Message(MessageSegment.image(pic))
            else:
                logger.error("渲染图片失败: 生成的图片数据为空")
                return Message(f"获取{self.name}日报失败: 生成的图片数据为空")
        except Exception as e:
            logger.error(f"渲染图片失败: {e}")
            return Message(f"获取{self.name}日报失败: {e}")


class TextFormatMixin(ABC):
    """文本格式化混入类"""

    def format_text_with_limit(
        self,
        news_data: NewsData,
        title: str,
        max_items: Optional[int] = None,
        title_max_length: int = 50,
        show_description: bool = True,
        show_url: bool = False,
        show_detail_hint: bool = False,
    ) -> Message:
        """统一的文本格式化逻辑"""
        if max_items and len(news_data.items) > max_items:
            logger.info(
                f"{self.name}文本格式条目过多，限制为{max_items}条 (原有{len(news_data.items)}条)"
            )
            news_data.items = news_data.items[:max_items]

        message = Message(f"【{title}】\n\n")

        for i, item in enumerate(news_data.items, 1):
            item_title = item.title
            if len(item_title) > title_max_length:
                item_title = item_title[: title_max_length - 3] + "..."

            message.append(f"{i}. {item_title}\n")

            if show_description and item.description:
                message.append(f"   {item.description}\n")

            if show_url and item.url:
                message.append(f"   链接: {item.url}\n")

            message.append("\n")

        if show_detail_hint:
            message.append("提示: 回复数字可查看对应新闻的网页截图\n")
            message.append("例如: 回复 1 查看第一条新闻\n")

        return message


class BinaryDataMixin(ABC):
    """二进制数据处理混入类"""

    def handle_binary_data(self, news_data: NewsData) -> Optional[Message]:
        """处理二进制图片数据"""
        if not (hasattr(news_data, "binary_data") and news_data.binary_data):
            return None

        try:
            if len(news_data.binary_data) > 0:
                logger.debug(
                    f"使用二进制图片数据，大小: {len(news_data.binary_data)} 字节"
                )
                return Message(MessageSegment.image(news_data.binary_data))
            else:
                logger.warning("二进制图片数据为空")
                return None
        except Exception as e:
            logger.error(f"处理二进制图片数据失败: {e}")
            return None


class NewsItemProcessorMixin(ABC):
    """新闻条目处理混入类"""

    def process_news_items(
        self,
        news_data: NewsData,
        max_items: Optional[int] = None,
        ensure_index: bool = True,
        ensure_url: bool = True,
        default_url: str = "#",
    ) -> NewsData:
        """处理新闻条目"""
        if max_items and len(news_data.items) > max_items:
            logger.info(
                f"{self.name}条目过多，限制为{max_items}条 (原有{len(news_data.items)}条)"
            )
            news_data.items = news_data.items[:max_items]

        for i, item in enumerate(news_data.items):
            if ensure_index and not item.index:
                item.index = i + 1

            if ensure_url and not item.url:
                item.url = default_url

        return news_data


class ConfigurableFormatMixin(ABC):
    """可配置格式混入类"""

    def determine_api_format(
        self, requested_format: str, global_default: str
    ) -> dict[str, Any]:
        """根据请求格式和全局配置确定API请求参数"""
        params = {}

        if global_default == "text":
            if requested_format == "image":
                logger.debug("根据全局配置，先尝试获取JSON数据用于图片渲染")
                params["format"] = "json"
            else:
                params["format"] = "json"
        else:
            if requested_format == "text":
                params["format"] = "json"
            else:
                params["format"] = "image"

        return params

    async def fetch_with_format_fallback(
        self,
        api_manager,
        requested_format: str,
        global_default: str,
        api_index: int = None,
    ) -> NewsData:
        """带格式回退的数据获取"""
        params = self.determine_api_format(requested_format, global_default)
        logger.debug(f"{self.name}日报请求参数: {params}")

        if requested_format == "image" and global_default == "text":
            try:
                json_params = {"format": "json"}
                news_data = await api_manager.fetch_data(self.name, json_params, api_index)

                if (
                    news_data
                    and hasattr(news_data, "items")
                    and len(news_data.items) > 0
                ):
                    logger.debug("成功获取JSON数据，将用于渲染图片")
                    return news_data

                logger.debug("未获取到有效的JSON数据，回退到请求图片")
                params["format"] = "image"
            except Exception as e:
                logger.warning(f"获取JSON数据失败，回退到请求图片: {e}")
                params["format"] = "image"

        return await api_manager.fetch_data(self.name, params, api_index)


class ImageSizeOptimizationMixin(ABC):
    """图片大小优化混入类"""

    async def render_with_size_optimization(
        self,
        news_data: NewsData,
        template_name: str,
        title: str,
        extra_data: Optional[dict[str, Any]] = None,
        max_size_mb: float = 1.0,
        size_reduction_steps: list[int] = None,
    ) -> Message:
        """带图片大小优化的渲染逻辑"""
        if size_reduction_steps is None:
            size_reduction_steps = [15, 10, 5]

        if hasattr(news_data, "binary_data") and news_data.binary_data:
            logger.debug("检测到二进制图片数据，直接使用API返回的图片")
            try:
                if len(news_data.binary_data) > 0:
                    return Message(MessageSegment.image(news_data.binary_data))
            except Exception as e:
                logger.error(f"使用二进制图片数据失败: {e}，回退到渲染文本")

        logger.debug("未检测到二进制图片数据，将文本渲染为图片")

        for step_items in size_reduction_steps:
            try:
                current_items = news_data.items[:step_items]
                temp_news_data = NewsData(
                    title=news_data.title,
                    items=current_items,
                    update_time=news_data.update_time,
                    source=news_data.source,
                )

                for i, item in enumerate(temp_news_data.items):
                    if not item.index:
                        item.index = i + 1
                    if not item.url:
                        item.url = "#"

                template_data = {"date": get_today_date()}
                if extra_data:
                    template_data.update(extra_data)

                pic = await render_news_to_image(
                    temp_news_data,
                    template_name,
                    title,
                    template_data,
                )

                if pic and len(pic) > 0:
                    size_mb = len(pic) / 1024 / 1024
                    if size_mb <= max_size_mb:
                        logger.debug(f"成功渲染图片，大小: {size_mb:.2f}MB")
                        return Message(MessageSegment.image(pic))
                    else:
                        logger.warning(
                            f"图片过大: {size_mb:.2f}MB，尝试减少条目到{step_items}条"
                        )
                        continue

            except Exception as e:
                logger.error(f"渲染图片失败: {e}")
                continue

        logger.error("所有图片渲染尝试都失败")
        return Message(f"获取{self.name}日报失败: 图片渲染失败")
