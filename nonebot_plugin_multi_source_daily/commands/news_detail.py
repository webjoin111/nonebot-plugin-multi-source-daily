from typing import Dict
from nonebot import logger, require
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.rule import Rule

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatcher,
    Args,
    CommandMeta,
    CommandResult,
    on_alconna,
)

from ..api.handlers import get_news_handler
from ..utils.screenshot import capture_webpage_screenshot

recent_news_types: Dict[str, Dict[str, str]] = {}

news_detail = on_alconna(
    Alconna(
        "日报详情",
        Args["news_type", str],
        Args["index", int],
        meta=CommandMeta(
            compact=True,
            description="获取指定日报类型的特定序号新闻详情",
            usage="日报详情 [类型] [数字]",
        ),
    ),
    priority=5,
    block=True,
)


def reply_with_number_rule() -> Rule:
    async def _rule(event: MessageEvent) -> bool:
        if not event.reply:
            return False

        reply_msg = event.reply.message
        has_image = False
        for seg in reply_msg:
            if seg.type == "image":
                has_image = True
                break

        if not has_image:
            return False

        text = event.get_plaintext().strip()
        return text.isdigit()

    return Rule(_rule)


from nonebot.plugin import on_message

quote_detail = on_message(rule=reply_with_number_rule(), priority=5, block=True)


async def extract_news_type_from_reply(event: MessageEvent) -> str | None:
    """从回复消息中提取日报类型"""
    if not event.reply:
        return None

    reply_msg = event.reply.message

    has_image = False
    for seg in reply_msg:
        if seg.type == "image":
            has_image = True
            break

    if not has_image:
        return None

    text = reply_msg.extract_plain_text()
    logger.debug(f"回复消息文本: {text}")

    detail_display_names = {"IT之家": "IT之家", "知乎日报": "知乎日报"}

    for display_name, handler_name in detail_display_names.items():
        if display_name in text:
            logger.debug(f"从文本中识别到显示名称: {display_name}")
            logger.debug(f"映射到日报类型: {handler_name}")
            return handler_name

    type_keywords = {
        "IT之家": ["it之家", "it", "ithome", "IT之家", "IT"],
        "知乎日报": ["知乎日报", "zhihu"],
        "历史上的今天": ["历史上的今天", "历史", "history", "HISTORY"],
    }

    for news_type, keywords in type_keywords.items():
        for keyword in keywords:
            if keyword.lower() in text.lower():
                logger.debug(f"从回复中识别到日报类型: {news_type} (关键词: {keyword})")
                return news_type

    for seg in reply_msg:
        if seg.type == "image":
            url = seg.data.get("url", "")
            logger.debug(f"图片URL: {url}")

            url_lower = url.lower()
            if "ithome" in url_lower or "it之家" in url_lower:
                return "IT之家"
            elif "zhihu" in url_lower or "知乎" in url_lower:
                return "知乎日报"
            elif "history" in url_lower or "历史" in url_lower:
                return "历史上的今天"

    logger.debug("无法从回复中识别日报类型")
    return None


@news_detail.handle()
async def handle_news_detail(
    matcher: AlconnaMatcher,
    res: CommandResult,
):
    """处理日报详情命令"""
    arp = res.result

    news_type = arp.all_matched_args.get("news_type")
    index = arp.all_matched_args.get("index")

    if not news_type or not index:
        await matcher.send("请指定日报类型和数字")
        return

    handler = get_news_handler(news_type)
    if not handler:
        await matcher.send(f"未找到{news_type}类型的日报处理器")
        return

    news_item = await handler.get_news_item_by_index(index)
    if not news_item:
        await matcher.send(f"未找到{news_type}日报的第{index}条新闻")
        return

    if not news_item.url:
        await matcher.send(f"第{index}条新闻没有可访问的链接")
        return

    await matcher.send(f"正在获取 {news_item.title} 的网页截图，请稍候...")

    pic = await capture_webpage_screenshot(url=news_item.url, site_type=handler.name)

    if not pic:
        await matcher.send(f"获取网页截图失败，您可以直接访问: {news_item.url}")
        return

    try:
        await matcher.send(Message(MessageSegment.image(pic)))
    except Exception as e:
        logger.error(f"发送图片失败: {e}")
        await matcher.send(f"发送图片失败，您可以直接访问: {news_item.url}")


@quote_detail.handle()
async def handle_quote_detail(event: MessageEvent):
    """处理引用回复获取详情命令"""
    text = event.get_plaintext().strip()
    try:
        index = int(text)
    except ValueError:
        return

    news_type = await extract_news_type_from_reply(event)
    if not news_type:
        return

    handler = get_news_handler(news_type)
    if not handler:
        return

    news_item = await handler.get_news_item_by_index(index)
    if not news_item:
        return

    if not news_item.url:
        return

    await quote_detail.send(f"正在获取 {news_item.title} 的网页截图，请稍候...")

    pic = await capture_webpage_screenshot(url=news_item.url, site_type=handler.name)

    if not pic:
        await quote_detail.send(f"获取网页截图失败，您可以直接访问: {news_item.url}")

    try:
        await quote_detail.send(Message(MessageSegment.image(pic)))
    except Exception as e:
        logger.error(f"发送图片失败: {e}")
        await quote_detail.send(f"发送图片失败，您可以直接访问: {news_item.url}")
