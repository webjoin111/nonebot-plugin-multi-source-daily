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
        "• 日报 [类型] [-f 格式] [--force] [-a API索引]  获取指定类型日报\n"
        "  - 类型: 60s/知乎日报/ithome/历史上的今天/moyu (可用别名)\n"
        "  - 格式: image(图片)/text(文本)，默认图片\n"
        "  - --force: 强制刷新，不使用缓存\n"
        "  - -a API索引: 指定使用第几个API源 (1-based)\n"
        "• 日报详情 [类型] [数字]  查看指定新闻的网页截图\n"
        "  - 仅支持IT之家和知乎日报\n"
        "• [数字]  回复日报图片后发送数字查看详情\n"
        "• 日报列表  显示所有支持的日报类型和别名\n\n"

        "⏰ 定时日报 (需要超级用户权限)\n"
        "• 定时日报 设置 [类型] [时间] [选项]  设置定时推送\n"
        "  - 时间格式: HH:MM 或 HHMM (如 08:30 或 0830)\n"
        "  - 选项: -g 群号 (指定群) / -all (所有群) / -f 格式\n"
        "• 定时日报 取消 [类型] [选项]  取消定时推送\n"
        "  - 选项: -g 群号 (指定群) / -all (所有群)\n"
        "• 定时日报 查看 [选项]  查看定时任务状态\n"
        "  - 选项: -g 群号 / -all / -t (显示表格)\n"
        "• 定时日报 修复 [-a]  修复异常的定时任务\n"
        "  - -a: 修复所有任务\n\n"

        "🔧 API管理 (需要超级用户权限)\n"
        "• 日报API [-t]  查看所有API源状态和优先级\n"
        "  - -t: 以文本形式显示，默认为图片\n"
        "• 日报API 启用 [类型] [序号]  启用指定的API源\n"
        "• 日报API 禁用 [类型] [序号]  禁用指定的API源\n"
        "• 日报API 重置 [类型]  重置指定类型的API源状态\n"
        "• 日报API 重置 -a  重置所有API源状态\n\n"

        "💾 缓存管理 (需要超级用户权限)\n"
        "• 日报缓存 [操作] [类型] [选项]  管理日报缓存\n"
        "  - 操作: 状态/重置 (默认为状态)\n"
        "  - 类型: 指定日报类型 (可选)\n"
        "  - 选项: -a (重置所有缓存)\n\n"

        "📝 使用示例\n"
        "• 日报 60s  获取60秒日报(图片)\n"
        "• 日报 60s -a 2  使用60s日报的第2个API源\n"
        "• 日报 知乎日报 -f text --force  强制获取知乎日报(文本)\n"
        "• 日报详情 ithome 3  查看IT之家第3条新闻详情\n"
        "• 定时日报 设置 60s 08:30 -all  所有群8:30推送60s日报\n"
        "• 定时日报 设置 知乎日报 18:00 -g 123456 -f text  指定群推送文本格式\n"
        "• 定时日报 查看 -t  查看定时任务(表格形式)\n"
        "• 日报API 启用 60s 2  启用60s日报的第2个API源\n"
        "• 日报缓存 重置 60s  重置60s日报的缓存\n\n"

        "💡 支持的日报类型\n"
        "• 60s: 每日60秒读懂世界 (别名: 60秒/早报/每日60秒/60s日报/60秒日报)\n"
        "• 知乎日报: 知乎热门文章\n"
        "• ithome: IT之家科技新闻 (别名: it之家/IT之家/it/IT)\n"
        "• 历史上的今天: 历史上的今天发生的大事 (别名: 历史/today)\n"
        "• moyu: 摸鱼人日历 (别名: 摸鱼/摸鱼人/摸鱼日历/摸鱼日报)"
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
