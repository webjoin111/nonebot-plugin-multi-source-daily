from nonebot import require
from nonebot.permission import SUPERUSER
from ..utils import news_cache

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import (  # noqa: E402
    Alconna,
    AlconnaMatcher,
    CommandMeta,
    CommandResult,
    Option,
    on_alconna,
)


daily_news_cache = on_alconna(
    Alconna(
        "日报缓存",
        Option("reset|重置", help_text="重置所有缓存"),
        meta=CommandMeta(
            description="日报缓存管理（仅限超级用户）",
            usage="日报缓存 [reset|重置]",
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
    """处理日报缓存命令"""
    from nonebot import logger

    arp = res.result

    if "reset" in arp.options or "重置" in arp.options:
        logger.debug("执行重置操作 - 重置所有缓存")
        count = news_cache.clear()
        await matcher.send(f"已重置所有日报缓存，共 {count} 项")
        return

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
            message += f"- {item['type']} ({item['format']}"
            if "api_source" in item:
                message += f", {item['api_source']}"
            message += f"): 将在 {item['expires_in']}秒后过期\n"

    await matcher.send(message.strip())
