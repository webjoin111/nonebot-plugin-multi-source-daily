"""日报API管理命令模块"""

from nonebot import require
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.permission import SUPERUSER

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatcher,
    Args,
    CommandMeta,
    CommandResult,
    Option,
    Subcommand,
    on_alconna,
)

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic

from ..api import api_manager
from ..utils import get_current_time

daily_news_api = on_alconna(
    Alconna(
        "日报API",
        Option("-t", alias=["--text"], help_text="使用文本方式显示，默认为图片"),
        Subcommand(
            "启用",
            Args["news_type", str],
            Args["index", int],
            help_text="启用指定的日报API源",
        ),
        Subcommand(
            "禁用",
            Args["news_type", str],
            Args["index", int],
            help_text="禁用指定的日报API源",
        ),
        Subcommand(
            "重置",
            Args["news_type?", str],
            Option("-a|--all", help_text="重置所有日报类型的API源"),
            help_text="重置指定日报类型或所有类型的API源状态",
        ),
        meta=CommandMeta(
            description="日报API源管理",
            usage=(
                "日报API [-t]  # 查看所有API源状态\n"
                "日报API 启用 [类型] [序号]  # 启用指定API源\n"
                "日报API 禁用 [类型] [序号]  # 禁用指定API源\n"
                "日报API 重置 [类型]  # 重置指定类型API源\n"
                "日报API 重置 -a  # 重置所有API源"
            ),
        ),
    ),
    permission=SUPERUSER,
    priority=1,
    block=True,
)


@daily_news_api.handle()
async def handle_daily_news_api(
    matcher: AlconnaMatcher,
    res: CommandResult,
):
    """处理日报API命令"""
    arp = res.result

    if not arp.subcommands:
        use_text = "-t" in arp.options or "--text" in arp.options
        await handle_api_list(matcher, use_text)
        return

    if "启用" in arp.subcommands:
        sub_args = arp.subcommands["启用"].args
        news_type = sub_args.get("news_type")
        index = sub_args.get("index")
        await handle_api_toggle(matcher, news_type, index, enable=True)
        return

    if "禁用" in arp.subcommands:
        sub_args = arp.subcommands["禁用"].args
        news_type = sub_args.get("news_type")
        index = sub_args.get("index")
        await handle_api_toggle(matcher, news_type, index, enable=False)
        return

    if "重置" in arp.subcommands:
        sub_args = arp.subcommands["重置"].args
        sub_options = arp.subcommands["重置"].options
        news_type = sub_args.get("news_type")
        reset_all = "-a" in sub_options or "--all" in sub_options
        await handle_api_reset(matcher, news_type, reset_all)
        return


async def handle_api_list(matcher: AlconnaMatcher, use_text: bool = False):
    """处理API源列表查看"""
    api_status = api_manager.get_api_status()

    if use_text:
        message = f"【日报API源状态】\n查询时间: {get_current_time()}\n\n"

        for news_type, status in api_status.items():
            message += f"▶ {news_type} 日报:\n"

            for i, source in enumerate(status["sources"], 1):
                message += f"  {i}. {source['url']}\n"
                message += f"     - 状态: {'启用' if source['enabled'] else '禁用'}\n"
                message += f"     - 优先级: {source['priority']}\n"
                message += f"     - 解析器: {source['parser']}\n"

                if source["last_success"] > 0:
                    import time

                    last_success_time = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(source["last_success"]),
                    )
                    message += f"     - 上次成功: {last_success_time}\n"
                else:
                    message += "     - 上次成功: 从未\n"

                message += f"     - 失败次数: {source['failure_count']}\n"

            message += "\n"

        await matcher.send(message.strip())
    else:
        md_text = "# 日报API源状态\n\n"
        md_text += f"查询时间: {get_current_time()}\n\n"

        for news_type, status in api_status.items():
            md_text += f"## {news_type} 日报\n\n"

            for i, source in enumerate(status["sources"], 1):
                md_text += f"### {i}. {source['url']}\n"
                md_text += f"- **状态**: {'启用' if source['enabled'] else '禁用'}\n"
                md_text += f"- **优先级**: {source['priority']}\n"
                md_text += f"- **解析器**: {source['parser']}\n"

                if source["last_success"] > 0:
                    import time

                    last_success_time = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(source["last_success"]),
                    )
                    md_text += f"- **上次成功**: {last_success_time}\n"
                else:
                    md_text += "- **上次成功**: 从未\n"

                md_text += f"- **失败次数**: {source['failure_count']}\n\n"

        pic = await md_to_pic(md=md_text)

        await matcher.send(MessageSegment.image(pic))


async def handle_api_toggle(
    matcher: AlconnaMatcher, news_type: str, index: int, enable: bool = True
):
    """处理API源启用/禁用"""
    sources = api_manager.get_api_sources(news_type)
    if not sources:
        await matcher.send(f"未知的日报类型: {news_type}")
        return

    if index <= 0 or index > len(sources):
        await matcher.send(f"无效的序号: {index}，有效范围: 1-{len(sources)}")
        return

    source = sources[index - 1]
    action = "启用" if enable else "禁用"

    if enable:
        api_manager.enable_api_source(news_type, source.url)
    else:
        api_manager.disable_api_source(news_type, source.url)

    await matcher.send(f"已{action} {news_type} 日报的第 {index} 个API源: {source.url}")


async def handle_api_reset(
    matcher: AlconnaMatcher, news_type: str = None, reset_all: bool = False
):
    """处理API源重置"""
    if reset_all or (news_type and news_type.lower() == "all"):
        count = api_manager.reset_all_api_sources()
        await matcher.send(f"已重置所有日报类型的API源状态，共 {count} 个")
    elif news_type:
        sources = api_manager.get_api_sources(news_type)
        if not sources:
            await matcher.send(f"未知的日报类型: {news_type}")
            return

        count = api_manager.reset_api_sources(news_type)
        await matcher.send(f"已重置 {news_type} 日报的API源状态，共 {count} 个")
    else:
        await matcher.send("请指定要重置的日报类型，或使用 -a 参数重置所有类型")
