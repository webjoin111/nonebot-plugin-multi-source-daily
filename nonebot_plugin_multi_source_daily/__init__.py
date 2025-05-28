from nonebot import get_driver, get_plugin_config
from nonebot.log import logger
from nonebot.plugin import PluginMetadata, require

try:
    require("nonebot_plugin_alconna")
except Exception as e:
    logger.error(f"加载 nonebot_plugin_alconna 失败: {e}")
    raise

try:
    require("nonebot_plugin_apscheduler")
except Exception as e:
    logger.error(f"加载 nonebot_plugin_apscheduler 失败: {e}")
    raise

try:
    require("nonebot_plugin_localstore")
except Exception as e:
    logger.error(f"加载 nonebot_plugin_localstore 失败: {e}")
    raise

try:
    require("nonebot_plugin_htmlrender")
    HAS_HTMLRENDER = True
    logger.info("成功加载 nonebot_plugin_htmlrender 插件")
except Exception as e:
    HAS_HTMLRENDER = False
    logger.warning(f"加载 nonebot_plugin_htmlrender 失败: {e}，图片渲染功能将不可用")

from .config import Config, update_config_from_global
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
    schedule_store,
    api_status_store,
)

__plugin_meta__ = PluginMetadata(
    name="多源日报",
    description="获取各种日报信息，支持定时发送和多API源",
    usage=(
        "📰 基础命令\n"
        "• 日报 [类型] [-f 格式] [--force] [-a API索引]\n"
        "• 日报详情 [类型] [数字] (仅支持IT之家和知乎日报)\n"
        "• 日报列表 - 显示所有支持的日报类型\n\n"

        "⏰ 定时日报 (超级用户)\n"
        "• 定时日报 设置 [类型] [时间] [-g 群号] [-all] [-f 格式]\n"
        "• 定时日报 取消/查看/修复 [选项]\n\n"

        "🔧 管理命令 (超级用户)\n"
        "• 日报API [-t] - 查看API源状态\n"
        "• 日报API 启用/禁用/重置 [类型] [序号]\n"
        "• 日报缓存 [状态/重置] [类型] [-a]\n\n"

        "💡 支持的日报类型\n"
        "• 60秒 (别名: 60s) • 知乎日报 • 知乎热榜\n"
        "• 微博热搜 (别名: weibo/微博) • IT之家 (别名: it之家/it/IT)\n"
        "• 历史上的今天 (别名: 历史/today) • 摸鱼日历 (别名: 摸鱼/moyu)\n\n"

        "📝 示例: 日报 60s | 日报 知乎热榜 -f text | 定时日报 设置 60s 08:30 -all"
    ),
    type="application",
    homepage="https://github.com/webjoin111/nonebot-plugin-multi-source-daily",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

__all__ = [
    "api_status_store",
    "daily_news",
    "daily_news_api",
    "daily_news_cache",
    "daily_news_list",
    "daily_news_schedule",
    "news_cache",
    "news_detail",
    "news_sources",
    "quote_detail",
    "schedule_store",
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

        if api_manager.load_status():
            logger.info("已加载保存的API源状态")
        else:
            count = api_manager.reset_all_api_sources()
            logger.info(f"未找到保存的API源状态，已重置所有API源状态，共 {count} 个")

        await schedule_manager.init_jobs()
        logger.info("已初始化定时任务")
    except Exception as e:
        logger.error(f"初始化失败: {e}")
