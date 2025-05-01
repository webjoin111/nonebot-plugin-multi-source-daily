from nonebot import get_driver, require, get_plugin_config
from nonebot.log import logger
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_alconna")
require("nonebot_plugin_apscheduler")
require("nonebot_plugin_htmlrender")
require("nonebot_plugin_localstore")

from .config import config, Config, update_config_from_global
from .api import (
    api_manager,
    init_api_sources,
    news_sources,
)
from .commands import (
    daily_news,
    daily_news_api,
    daily_news_cache,
    daily_news_list,
    daily_news_schedule,
)
from .commands.news_detail import news_detail, quote_detail
from .utils import (
    news_cache,
    schedule_manager,
    store,
)

__plugin_meta__ = PluginMetadata(
    name="多源日报",
    description="获取各种日报信息，支持定时发送和多API源",
    usage=(
        "【基础命令】\n"
        "  日报 [类型] [-f 格式]\n"
        "    - 获取指定类型的日报信息\n"
        "    - 可选格式: image(图片), text(文字)\n"
        "    - 例如: 日报 60s -f text\n"
        "    - 例如: 日报 历史上的今天\n\n"
        "  日报详情 [类型] [数字]\n"
        "    - 获取指定日报类型中特定序号新闻的网页截图\n"
        "    - 例如: 日报详情 IT 3\n"
        "    - 仅对有网页链接的日报类型有效\n\n"
        "  [数字]\n"
        "    - 回复日报图片并发送数字，获取对应序号新闻的网页截图\n"
        "    - 例如: 回复IT之家日报图片 + 5\n"
        "    - 仅对有网页链接的日报类型有效\n\n"
        "【定时日报命令】\n"
        "  定时日报 设置 [类型] [HH:MM或HHMM] [-g 群号] [-all] [-f 格式]\n"
        "    - 设置定时发送指定类型的日报(仅限超级用户)\n"
        "    - -g 参数可指定特定群号\n"
        "    - -all 参数将对所有群生效\n"
        "    - -f 参数可设置格式(image/text)\n"
        "    - 例如: 定时日报 设置 60s 08:00 -g 123456 -f text\n"
        "    - 例如: 定时日报 设置 知乎 09:30 -all\n\n"
        "  定时日报 取消 [类型] [-g 群号] [-all]\n"
        "    - 取消本群或指定群的定时日报(仅限超级用户)\n"
        "    - 例如: 定时日报 取消 60s -g 123456\n\n"
        "  定时日报 查看 [-g 群号] [-all] [-t]\n"
        "    - 查看当前群的日报订阅情况\n"
        "    - -g 和 -all 参数仅限超级用户使用\n"
        "    - -t 使用文本方式显示，默认为图片\n"
        "    - 例如: 定时日报 查看 -all -t\n\n"
        "  定时日报 修复 [-a]\n"
        "    - 修复日报系统，重新加载定时任务配置\n"
        "    - -a 参数将重置所有定时任务配置\n\n"
        "  日报列表\n"
        "    - 显示所有支持的日报类型\n\n"
        "【API源管理命令】(仅限超级用户)\n"
        "  日报API [-t]\n"
        "    - 查看所有日报API源及其状态\n"
        "    - -t 使用文本方式显示，默认为图片\n\n"
        "  日报API 启用 [类型] [序号]\n"
        "    - 启用指定的日报API源\n"
        "    - 例如: 日报API 启用 知乎 2\n\n"
        "  日报API 禁用 [类型] [序号]\n"
        "    - 禁用指定的日报API源\n"
        "    - 例如: 日报API 禁用 知乎 2\n\n"
        "  日报API 重置 [类型]\n"
        "    - 重置指定日报类型的API源状态\n"
        "    - 类型可以是: 60s, 知乎, moyu, ithome, 历史上的今天, all\n"
        "    - 例如: 日报API 重置 知乎\n\n"
        "  日报API 重置 -a\n"
        "    - 重置所有API源状态\n"
        "    - 当所有日报来源均不可用时使用\n"
    ),
    type="application",
    homepage="https://github.com/webjoin111/nonebot-plugin-multi-source-daily",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

__all__ = [
    "daily_news",
    "daily_news_api",
    "daily_news_cache",
    "daily_news_list",
    "daily_news_schedule",
    "news_cache",
    "news_detail",
    "news_sources",
    "quote_detail",
    "store",
]

driver = get_driver()


@driver.on_startup
async def startup():
    update_config_from_global()

    plugin_config = get_plugin_config(Config)

    template_path = plugin_config.get_template_dir()
    template_path.mkdir(parents=True, exist_ok=True)

    config_dir = plugin_config.get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    data_dir = plugin_config.get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = plugin_config.get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        init_api_sources()
        logger.info("已初始化API源")

        for source in news_sources.values():
            source.update_default_format()

        latest_config = get_plugin_config(Config)
        logger.info(
            f"已更新所有日报源的默认格式，全局默认格式: {latest_config.daily_news_default_format}"
        )

        count = api_manager.reset_all_api_sources()
        logger.info(f"已重置所有API源状态，共 {count} 个")

        await schedule_manager.init_jobs()
        logger.info("已初始化定时任务")
    except Exception as e:
        logger.error(f"初始化失败: {e}")
