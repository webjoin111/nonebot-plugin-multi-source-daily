from nonebot import logger, require
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    PrivateMessageEvent,
)

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatcher,
    Args,
    CommandMeta,
    CommandResult,
    Option,
    on_alconna,
)

from ..api import get_news_source, news_sources
from ..utils import generate_news_type_error

daily_news = on_alconna(
    Alconna(
        "日报",
        Args["news_type", str],
        Option("-f", Args["format_type", str]),
        Option("-f|--force", help_text="强制刷新，不使用缓存"),
        meta=CommandMeta(
            compact=True,
            description="获取指定类型的日报",
            usage="日报 [类型] [-f 格式] [--force]",
        ),
    ),
    priority=5,
    block=True,
)


daily_news_list = on_alconna(
    Alconna(
        "日报列表",
        meta=CommandMeta(
            description="显示所有支持的日报类型",
            usage="日报列表",
        ),
    ),
    priority=5,
    block=True,
)


@daily_news.handle()
async def handle_daily_news(
    bot: Bot,
    event: GroupMessageEvent | PrivateMessageEvent,
    matcher: AlconnaMatcher,
    res: CommandResult,
):
    """处理日报命令

    Args:
        bot: 机器人实例
        event: 事件
        matcher: 匹配器
        res: 命令结果
    """
    arp = res.result

    news_type = arp.all_matched_args.get("news_type")
    if not news_type:
        await matcher.send("请指定日报类型")
        return

    source = get_news_source(news_type)
    if not source:
        await matcher.send(generate_news_type_error(news_type, news_sources))
        return

    format_type = arp.all_matched_args.get("format_type")

    force_refresh = "-f" in arp.options or "--force" in arp.options

    await matcher.send(f"正在获取{news_type}日报，请稍候...")

    try:
        message = await source.fetch(format_type=format_type, force_refresh=force_refresh)

        await matcher.send(message)
    except Exception as e:
        logger.error(f"获取{news_type}日报失败: {e}")
        await matcher.send(f"获取{news_type}日报失败: {e}")


@daily_news_list.handle()
async def handle_daily_news_list(matcher: AlconnaMatcher):
    """处理日报列表命令

    Args:
        matcher: 匹配器
    """
    unique_sources = {}
    for name, source in news_sources.items():
        if source.name not in unique_sources:
            unique_sources[source.name] = source

    news_list = "【支持的日报类型】\n"
    for name, source in unique_sources.items():
        news_list += f"{name}: {source.description}\n"

        if source.aliases:
            news_list += f"  - 别名: {', '.join(source.aliases)}\n"

        news_list += f"  - 支持格式: {', '.join(source.formats)}\n"
        news_list += "\n"

    await matcher.send(news_list.strip())
