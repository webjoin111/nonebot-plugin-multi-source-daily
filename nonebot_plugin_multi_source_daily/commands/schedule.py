import datetime
from pathlib import Path

from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.permission import SUPERUSER

from .. import HAS_HTMLRENDER

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

if HAS_HTMLRENDER:
    from nonebot_plugin_htmlrender import md_to_pic


from ..api import get_news_source, news_sources
from ..exceptions import (
    InvalidTimeFormatException,
    ScheduleException,
)
from ..utils import (
    generate_news_type_error,
    parse_time,
    schedule_manager,
    validate_time,
)

CUSTOM_CSS_PATH = str(Path(__file__).parent.parent / "templates" / "custom_markdown.css")

TIME_REGEX = r"(0?[0-9]|1[0-9]|2[0-3]):([0-5][0-9])|(0?[0-9]|1[0-9]|2[0-3])([0-5][0-9])"

daily_news_schedule = on_alconna(
    Alconna(
        "定时日报",
        Subcommand(
            "设置",
            Args["news_type", str],
            Args["time", f"re:{TIME_REGEX}"],
            Option("-g", Args["target_group_id", int]),
            Option("-all"),
            Option("-f", Args["format_type", str]),
        ),
        Subcommand(
            "取消",
            Args["news_type", str],
            Option("-g", Args["target_group_id", int]),
            Option("-all"),
        ),
        Subcommand(
            "查看",
            Option("-g", Args["target_group_id", int]),
            Option("-all", alias=["--all"], help_text="查看所有群组的订阅情况"),
        ),
        meta=CommandMeta(
            compact=True,
            description="定时日报管理",
            usage=(
                "定时日报 设置 [类型] [HH:MM或HHMM] [-g 群号] [-all] [-f 格式]（仅限超级用户）\n"
                "定时日报 取消 [类型] [-g 群号] [-all]（仅限超级用户）\n"
                "定时日报 查看 [-g 群号] [-all]（-g 和 -all 参数仅限超级用户）"
            ),
        ),
    ),
    priority=5,
    block=True,
)


@daily_news_schedule.assign("设置")
async def handle_daily_news_set(
    bot: Bot,
    event: GroupMessageEvent | PrivateMessageEvent,
    matcher: AlconnaMatcher,
    res: CommandResult,
):
    """处理定时日报设置命令"""
    is_superuser = await SUPERUSER(bot, event)
    if not is_superuser:
        await matcher.send("只有超级用户才能使用此命令")
        return

    arp = res.result

    news_type = arp.all_matched_args.get("news_type")
    if not news_type:
        await matcher.send("请指定日报类型")
        return

    source = get_news_source(news_type)
    if not source:
        await matcher.send(generate_news_type_error(news_type, news_sources))
        return

    time_str = arp.all_matched_args.get("time")
    if not time_str:
        await matcher.send("请指定时间，格式为HH:MM或HHMM")
        return

    target_group = None
    if "target_group_id" in arp.all_matched_args:
        target_group = arp.all_matched_args["target_group_id"]

    logger.debug(f"设置命令选项: {arp.options}")
    logger.debug(f"设置命令子命令: {arp.subcommands}")

    if "设置" in arp.subcommands:
        set_options = arp.subcommands["设置"].options
        logger.debug(f"设置子命令选项: {set_options}")
        all_groups = "all" in set_options
    else:
        all_groups = "all" in arp.options

    format_type = arp.all_matched_args.get("format_type", "image")
    if format_type not in source.formats:
        await matcher.send(f"不支持的格式: {format_type}，可用格式: {', '.join(source.formats)}")
        return

    try:
        hour, minute = parse_time(time_str)

        if not validate_time(hour, minute):
            await matcher.send(f"无效的时间: {time_str}，请使用HH:MM或HHMM格式")
            return

        if all_groups:
            group_list = await bot.get_group_list()
            success_count = 0

            for group in group_list:
                try:
                    await schedule_manager.add_job(group["group_id"], news_type, hour, minute, format_type)
                    success_count += 1
                except Exception as e:
                    logger.error(f"为群 {group['group_id']} 设置定时任务失败: {e}")

            await matcher.send(
                f"已为所有群({success_count}/{len(group_list)}个)设置{news_type}日报，"
                f"时间: {hour:02d}:{minute:02d}，格式: {format_type}"
            )
            return

        if target_group:
            await schedule_manager.add_job(target_group, news_type, hour, minute, format_type)
            await matcher.send(
                f"已为群 {target_group} 设置{news_type}日报，"
                f"时间: {hour:02d}:{minute:02d}，格式: {format_type}"
            )
            return

        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
            await schedule_manager.add_job(group_id, news_type, hour, minute, format_type)
            await matcher.send(
                f"已为本群设置{news_type}日报，时间: {hour:02d}:{minute:02d}，格式: {format_type}"
            )
            return

        await matcher.send("请指定目标群号(-g)或使用-all参数")
    except InvalidTimeFormatException as e:
        await matcher.send(f"无效的时间格式: {e.time_str}")
    except ScheduleException as e:
        await matcher.send(f"设置定时任务失败: {e.message}")
    except Exception as e:
        logger.error(f"设置定时任务失败: {e}")
        await matcher.send(f"设置定时任务失败: {e}")


@daily_news_schedule.assign("取消")
async def handle_daily_news_remove(
    bot: Bot,
    event: GroupMessageEvent | PrivateMessageEvent,
    matcher: AlconnaMatcher,
    res: CommandResult,
):
    """处理定时日报取消命令"""
    is_superuser = await SUPERUSER(bot, event)
    if not is_superuser:
        await matcher.send("只有超级用户才能使用此命令")
        return

    arp = res.result

    news_type = arp.all_matched_args.get("news_type")
    if not news_type:
        await matcher.send("请指定日报类型")
        return

    source = get_news_source(news_type)
    if not source:
        await matcher.send(generate_news_type_error(news_type, news_sources))
        return

    target_group = None
    if "target_group_id" in arp.all_matched_args:
        target_group = arp.all_matched_args["target_group_id"]

    logger.debug(f"取消命令选项: {arp.options}")
    logger.debug(f"取消命令子命令: {arp.subcommands}")

    if "取消" in arp.subcommands:
        cancel_options = arp.subcommands["取消"].options
        logger.debug(f"取消子命令选项: {cancel_options}")
        all_groups = "all" in cancel_options
    else:
        all_groups = "all" in arp.options

    try:
        if all_groups:
            from ..utils.core import schedule_store

            removed_count = 0
            groups = schedule_store.get_all_groups_by_news_type(news_type)
            for group_id in groups:
                try:
                    await schedule_manager.remove_job(int(group_id), news_type)
                    removed_count += 1
                except Exception as e:
                    logger.error(f"为群 {group_id} 取消定时任务失败: {e}")

            await matcher.send(f"已取消所有群({removed_count}/{len(groups)}个)的{news_type}日报定时任务")
            return

        if target_group:
            await schedule_manager.remove_job(target_group, news_type)
            await matcher.send(f"已取消群 {target_group} 的{news_type}日报定时任务")
            return

        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
            await schedule_manager.remove_job(group_id, news_type)
            await matcher.send(f"已取消本群的{news_type}日报定时任务")
            return

        await matcher.send("请指定目标群号(-g)或使用-all参数")
    except ScheduleException as e:
        await matcher.send(f"取消定时任务失败: {e.message}")
    except Exception as e:
        logger.error(f"取消定时任务失败: {e}")
        await matcher.send(f"取消定时任务失败: {e}")


@daily_news_schedule.assign("查看")
async def handle_daily_news_view(
    bot: Bot,
    event: GroupMessageEvent | PrivateMessageEvent,
    matcher: AlconnaMatcher,
    res: CommandResult,
):
    """处理定时日报查看命令"""
    arp = res.result

    target_group = None
    if "target_group_id" in arp.all_matched_args:
        target_group = arp.all_matched_args["target_group_id"]

    logger.debug(f"查看命令选项: {arp.options}")
    logger.debug(f"查看命令子命令: {arp.subcommands}")
    logger.debug(f"查看命令所有参数: {arp.all_matched_args}")

    if "查看" in arp.subcommands:
        view_options = arp.subcommands["查看"].options
        logger.debug(f"查看子命令选项: {view_options}")
        all_groups = "all" in view_options
    else:
        all_groups = "all" in arp.options

    is_superuser = await SUPERUSER(bot, event)
    if (target_group or all_groups) and not is_superuser:
        await matcher.send("只有超级用户才能使用 -g 或 -all 参数查看其他群组的订阅情况")
        return

    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if all_groups:
            from ..utils.core import schedule_store

            all_schedules = schedule_store.get_all_schedules()
            if not all_schedules:
                await matcher.send("当前没有任何群组订阅日报")
                return

            html_data = {
                "title": "所有群组的日报订阅情况",
                "current_time": current_time,
                "groups": [],
            }

            for group_id, schedules in all_schedules.items():
                try:
                    group_info = await bot.get_group_info(group_id=int(group_id))
                    group_name = group_info.get("group_name", f"群 {group_id}")
                except Exception:
                    group_name = f"群 {group_id}"

                group_data = {
                    "group_id": group_id,
                    "group_name": group_name,
                    "jobs": [],
                }

                for news_type, schedule in schedules.items():
                    source = get_news_source(news_type)
                    news_description = source.description if source else "未知日报类型"
                    schedule_time = schedule.get("schedule_time", "未知时间")
                    format_type = schedule.get("format_type", "image")

                    group_data["jobs"].append(
                        {
                            "news_type": news_type,
                            "news_description": news_description,
                            "schedule_time": schedule_time,
                            "format_type": format_type,
                        }
                    )

                html_data["groups"].append(group_data)

            md_text = f"# 📊 {html_data['title']}\n\n"
            md_text += f"**查询时间**: {html_data['current_time']}\n\n"

            for group in html_data["groups"]:
                md_text += f"## 🏠 {group['group_name']} ({group['group_id']})\n\n"

                if not group["jobs"]:
                    md_text += "💤 该群没有订阅任何日报\n\n"
                else:
                    for job in group["jobs"]:
                        md_text += f"📰 **{job['news_type']}** - {job['news_description']}\n\n"
                        md_text += f"⏰ **推送时间**: {job['schedule_time']} | 📱 **格式**: {job['format_type']}\n\n"
                        md_text += "---\n\n"

            if HAS_HTMLRENDER:
                try:
                    pic = await md_to_pic(md=md_text, css_path=CUSTOM_CSS_PATH)
                    await matcher.send(MessageSegment.image(pic))
                except Exception as e:
                    logger.error(f"生成订阅情况图片失败: {e}，将使用文本模式")
                    text_message = (
                        f"【所有群组的日报订阅情况】\n查询时间: {html_data['current_time']}\n\n"
                    )
                    for group in html_data["groups"]:
                        text_message += f"▶ {group['group_name']} ({group['group_id']})\n"
                        if not group["jobs"]:
                            text_message += "  该群没有订阅任何日报\n\n"
                        else:
                            for job in group["jobs"]:
                                text_message += f"  • {job['news_type']} ({job['news_description']})\n"
                                text_message += f"    订阅时间: {job['schedule_time']}\n"
                                text_message += f"    格式: {job['format_type']}\n\n"
                    await matcher.send(text_message.strip())
            else:
                logger.warning("htmlrender插件不可用，将使用文本模式显示订阅情况")
                text_message = f"【所有群组的日报订阅情况】\n查询时间: {html_data['current_time']}\n\n"
                for group in html_data["groups"]:
                    text_message += f"▶ {group['group_name']} ({group['group_id']})\n"
                    if not group["jobs"]:
                        text_message += "  该群没有订阅任何日报\n\n"
                    else:
                        for job in group["jobs"]:
                            text_message += f"  • {job['news_type']} ({job['news_description']})\n"
                            text_message += f"    订阅时间: {job['schedule_time']}\n"
                            text_message += f"    格式: {job['format_type']}\n\n"
                await matcher.send(text_message.strip())

            return

        if target_group:
            from ..utils.core import schedule_store

            schedules = schedule_store.get_group_schedules(target_group)

            try:
                group_info = await bot.get_group_info(group_id=target_group)
                group_name = group_info.get("group_name", f"群 {target_group}")
            except Exception:
                group_name = f"群 {target_group}"

            jobs = []
            for news_type, schedule in schedules.items():
                source = get_news_source(news_type)
                news_description = source.description if source else "未知日报类型"
                schedule_time = schedule.get("schedule_time", "未知时间")
                format_type = schedule.get("format_type", "image")

                jobs.append(
                    {
                        "news_type": news_type,
                        "news_description": news_description,
                        "schedule_time": schedule_time,
                        "format_type": format_type,
                    }
                )

            html_data = {
                "title": f"{group_name} 的日报订阅情况",
                "current_time": current_time,
                "jobs": jobs,
                "group_name": group_name,
                "group_id": target_group,
            }

            md_text = f"# 📊 {html_data['title']}\n\n"
            md_text += f"**查询时间**: {html_data['current_time']}\n\n"

            if not html_data["jobs"]:
                md_text += "💤 该群没有订阅任何日报\n\n"
            else:
                for idx, job in enumerate(html_data["jobs"], 1):
                    md_text += f"## {idx}. 📰 {job['news_type']}\n\n"
                    md_text += f"📝 **描述**: {job['news_description']}\n\n"
                    md_text += (
                        f"⏰ **推送时间**: {job['schedule_time']} | 📱 **格式**: {job['format_type']}\n\n"
                    )
                    md_text += "---\n\n"

            if HAS_HTMLRENDER:
                try:
                    pic = await md_to_pic(md=md_text, css_path=CUSTOM_CSS_PATH)
                    await matcher.send(MessageSegment.image(pic))
                except Exception as e:
                    logger.error(f"生成订阅情况图片失败: {e}，将使用文本模式")
                    text_message = (
                        f"【{group_name} 的日报订阅情况】\n查询时间: {html_data['current_time']}\n\n"
                    )
                    if not html_data["jobs"]:
                        text_message += "该群没有订阅任何日报"
                    else:
                        for idx, job in enumerate(html_data["jobs"], 1):
                            text_message += f"{idx}. {job['news_type']} ({job['news_description']})\n"
                            text_message += f"   - 订阅时间: {job['schedule_time']}\n"
                            text_message += f"   - 格式: {job['format_type']}\n\n"
                    await matcher.send(text_message.strip())
            else:
                logger.warning("htmlrender插件不可用，将使用文本模式显示订阅情况")
                text_message = (
                    f"【{group_name} 的日报订阅情况】\n查询时间: {html_data['current_time']}\n\n"
                )
                if not html_data["jobs"]:
                    text_message += "该群没有订阅任何日报"
                else:
                    for idx, job in enumerate(html_data["jobs"], 1):
                        text_message += f"{idx}. {job['news_type']} ({job['news_description']})\n"
                        text_message += f"   - 订阅时间: {job['schedule_time']}\n"
                        text_message += f"   - 格式: {job['format_type']}\n\n"
                await matcher.send(text_message.strip())

            return

        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
            from ..utils.core import schedule_store

            schedules = schedule_store.get_group_schedules(group_id)

            try:
                group_info = await bot.get_group_info(group_id=group_id)
                group_name = group_info.get("group_name", "本群")
            except Exception:
                group_name = "本群"

            jobs = []
            for news_type, schedule in schedules.items():
                source = get_news_source(news_type)
                news_description = source.description if source else "未知日报类型"
                schedule_time = schedule.get("schedule_time", "未知时间")
                format_type = schedule.get("format_type", "image")

                jobs.append(
                    {
                        "news_type": news_type,
                        "news_description": news_description,
                        "schedule_time": schedule_time,
                        "format_type": format_type,
                    }
                )

            html_data = {
                "title": f"{group_name} 的日报订阅情况",
                "current_time": current_time,
                "jobs": jobs,
                "group_name": group_name,
                "group_id": group_id,
            }

            md_text = f"# 📊 {html_data['title']}\n\n"
            md_text += f"**查询时间**: {html_data['current_time']}\n\n"

            if not html_data["jobs"]:
                md_text += "💤 本群没有订阅任何日报\n\n"
            else:
                for idx, job in enumerate(html_data["jobs"], 1):
                    md_text += f"## {idx}. 📰 {job['news_type']}\n\n"
                    md_text += f"📝 **描述**: {job['news_description']}\n\n"
                    md_text += (
                        f"⏰ **推送时间**: {job['schedule_time']} | 📱 **格式**: {job['format_type']}\n\n"
                    )
                    md_text += "---\n\n"

            try:
                pic = await md_to_pic(md=md_text, css_path=CUSTOM_CSS_PATH)
                await matcher.send(MessageSegment.image(pic))
            except Exception as e:
                logger.error(f"生成订阅情况图片失败: {e}，将使用文本模式")
                text_message = (
                    f"【{group_name} 的日报订阅情况】\n查询时间: {html_data['current_time']}\n\n"
                )
                if not html_data["jobs"]:
                    text_message += "本群没有订阅任何日报"
                else:
                    for idx, job in enumerate(html_data["jobs"], 1):
                        text_message += f"{idx}. {job['news_type']} ({job['news_description']})\n"
                        text_message += f"   - 订阅时间: {job['schedule_time']}\n"
                        text_message += f"   - 格式: {job['format_type']}\n\n"
                await matcher.send(text_message.strip())

            return

        await matcher.send("请指定目标群号(-g)或使用-all参数")
    except Exception as e:
        logger.error(f"查询订阅情况失败: {e}")
        await matcher.send(f"查询订阅情况失败: {e}")