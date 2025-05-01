from nonebot import require
from nonebot.permission import SUPERUSER

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
from ..utils import generate_news_type_error, news_cache

daily_news_cache = on_alconna(
    Alconna(
        "日报缓存",
        Args["operation?", str],
        Args["type?", str],
        Option("-a|--all", help_text="重置所有缓存"),
        meta=CommandMeta(
            description="日报缓存管理（仅限超级用户）",
            usage="日报缓存 [重置|状态] [类型]",
        ),
    ),
    permission=SUPERUSER,
    priority=5,
    block=True,
)


@daily_news_cache.handle()
async def handle_daily_news_cache(
    matcher: AlconnaMatcher,
    res: CommandResult,
):
    """处理日报缓存命令

    Args:
        matcher: 匹配器
        res: 命令结果
    """
    arp = res.result

    operation = arp.all_matched_args.get("operation", "状态")
    news_type = arp.all_matched_args.get("type")
    reset_all = "-a" in arp.options or "--all" in arp.options

    if operation in ["状态", "state", "status"]:
        if news_type:
            source = get_news_source(news_type)
            if not source:
                await matcher.send(generate_news_type_error(news_type, news_sources))
                return

            status = news_cache.get_detailed_status()
            filtered_details = [item for item in status["details"] if item["type"] == news_type]

            if not filtered_details:
                await matcher.send(f"当前没有 {news_type} 类型的缓存")
                return

            message = f"【{news_type} 日报缓存状态】\n"
            message += f"共有 {len(filtered_details)} 项缓存\n\n"

            for item in filtered_details:
                message += f"格式: {item['format']}\n"
                message += f"创建时间: {item['created_at']}\n"
                message += f"过期时间: {item['expires_in']}秒后\n\n"

            await matcher.send(message.strip())
        else:
            status = news_cache.get_status()
            detailed = news_cache.get_detailed_status()

            message = "【日报缓存状态】\n"
            message += f"共有 {status['total']} 项缓存\n"

            if status["total"] > 0:
                message += "\n各类型缓存数量:\n"
                for type_name, count in status["types"].items():
                    message += f"- {type_name}: {count}项\n"

                message += "\n详细缓存信息:\n"
                for item in detailed["details"]:
                    message += f"- {item['type']} ({item['format']}): "
                    message += f"将在 {item['expires_in']}秒后过期\n"

            await matcher.send(message.strip())
        return

    if operation in ["重置", "reset", "clear", "刷新", "refresh"]:
        if reset_all:
            count = news_cache.clear()
            await matcher.send(f"已重置所有日报缓存，共 {count} 项")
        elif news_type:
            source = get_news_source(news_type)
            if not source:
                await matcher.send(generate_news_type_error(news_type, news_sources))
                return

            count = news_cache.delete_by_type(news_type)
            if count > 0:
                await matcher.send(f"已重置 {news_type} 日报的缓存，共 {count} 项")
            else:
                await matcher.send(f"当前没有 {news_type} 类型的缓存")
        else:
            await matcher.send("请指定要重置的日报类型，或使用 -a 参数重置所有缓存")
        return

    await matcher.send("未知操作，可用操作：重置、状态")
