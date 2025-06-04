from pathlib import Path

from nonebot import require, get_plugin_config
from nonebot.log import logger
from pydantic import BaseModel, Field
from .models import ApiSource
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store  # noqa: E402



class NewsLimits:
    """新闻条目数量限制"""

    ZHIHU_IMAGE_MAX_ITEMS = 15
    ZHIHU_TEXT_MAX_ITEMS = 10
    ZHIHU_HOT_IMAGE_MAX_ITEMS = 15
    ZHIHU_HOT_TEXT_MAX_ITEMS = 10
    WEIBO_HOT_IMAGE_MAX_ITEMS = 15
    WEIBO_HOT_TEXT_MAX_ITEMS = 10
    TITLE_MAX_LENGTH = 50
    DEFAULT_TEXT_MAX_ITEMS = 10


class ViewportConfig:
    """视口配置"""

    DEFAULT = {"width": 800, "height": 600}
    ITHOME = {"width": 600, "height": 1000}
    ZHIHU = {"width": 800, "height": 1200}


class RetryConfig:
    """重试配置"""

    INITIAL_DELAY = 1.0
    BACKOFF_MULTIPLIER = 1.5
    MAX_RETRIES = 3
    GRACE_TIME = 60


class TemplateConfig:
    """模板配置"""

    TEMPLATES = {
        "60秒": "sixty_seconds.html",
        "知乎日报": "zhihu.html",
        "知乎热榜": "zhihu_hot.html",
        "微博热搜": "weibo_hot.html",
        "IT之家": "ithome.html",
        "历史上的今天": "history.html",
        "摸鱼日历": "news_template.html",
    }


class FormatConfig:
    """格式配置"""

    SUPPORTED_FORMATS = ["image", "text"]
    DEFAULT_FORMAT = "image"

    FORMAT_MAPPING = {
        "image": "image",
        "text": "json",
    }


class DetailConfig:
    """详情功能配置"""

    SUPPORTED_TYPES = ["IT之家", "知乎日报", "知乎热榜", "微博热搜"]


class CacheConfig:
    """缓存配置"""

    DEFAULT_EXPIRE = 3600
    CLEANUP_INTERVAL = 6 * 3600


class UserAgentConfig:
    """用户代理配置"""

    DEFAULT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


class ErrorMessages:
    """错误消息"""

    NO_DATA = "未获取到有效数据"
    RENDER_FAILED = "渲染失败"
    API_FAILED = "API请求失败"
    TIMEOUT = "请求超时"
    PARSE_FAILED = "数据解析失败"


class DefaultApiSources:
    """默认API源配置 - 不可配置的静态数据"""

    DAILY_NEWS_60S_APIS = [
        ApiSource(
            url="https://api.southerly.top/api/60s",
            priority=1,
            parser="binary_image",
        ),
        ApiSource(
            url="https://60s-api.viki.moe/v2/60s",
            priority=2,
            parser="viki_60s_json",
        ),
    ]

    DAILY_NEWS_ZHIHU_APIS = [
        ApiSource(
            url="https://api.vvhan.com/api/hotlist/zhihuDay",
            priority=1,
            parser="vvhan",
        ),
    ]

    DAILY_NEWS_ZHIHU_HOT_APIS = [
        ApiSource(
            url="https://60s-api.viki.moe/v2/zhihu",
            priority=1,
            parser="zhihu_hot",
        ),
    ]

    DAILY_NEWS_WEIBO_HOT_APIS = [
        ApiSource(
            url="https://weibo.com/ajax/side/hotSearch",
            priority=1,
            parser="weibo_hot_search",
        ),
        ApiSource(
            url="https://60s-api.viki.moe/v2/weibo",
            priority=2,
            parser="weibo_hot",
        ),
    ]

    DAILY_NEWS_MOYU_APIS = [
        ApiSource(url="https://api.vvhan.com/api/moyu", priority=1, parser="binary_image"),
        ApiSource(
            url="https://dayu.qqsuu.cn/moyuribao/apis.php?type=json", priority=2, parser="moyu_json"
        ),
        ApiSource(url="https://www.yviii.com/moyu/moyu2.php", priority=3, parser="binary_image"),
    ]


class Config(BaseModel):
    """插件配置类"""

    daily_news_ithome_apis: list[ApiSource] = Field(
        default_factory=lambda: [
            ApiSource(url="https://www.ithome.com/rss/", priority=1, parser="rss"),
        ]
    )

    daily_news_history_apis: list[ApiSource] = Field(
        default_factory=lambda: [
            ApiSource(
                url="https://api.03c3.cn/api/history",
                priority=1,
                parser="history_today",
            ),
        ]
    )

    daily_news_max_retries: int = 3
    daily_news_timeout: float = 10.0
    daily_news_cache_expire: int = 3600
    daily_news_auto_failover: bool = True

    daily_news_default_format: str = "image"
    daily_news_supported_formats: list[str] = ["image", "text"]

    daily_news_enable_personal_sub: bool = False

    daily_news_enable_stats: bool = False
    daily_news_stats_save_interval: int = 3600

    weibo_cookie: str = Field(
        default="",
        description="微博Cookie，用于获取微博详情内容。如果为空则无法获取微博详情",
    )

    class Config:
        extra = "ignore"

    def get_api_sources(self, news_type: str) -> list[ApiSource]:
        """获取API源列表"""
        # 静态配置的API源
        static_sources_map = {
            "60秒": DefaultApiSources.DAILY_NEWS_60S_APIS,
            "知乎日报": DefaultApiSources.DAILY_NEWS_ZHIHU_APIS,
            "知乎热榜": DefaultApiSources.DAILY_NEWS_ZHIHU_HOT_APIS,
            "微博热搜": DefaultApiSources.DAILY_NEWS_WEIBO_HOT_APIS,
            "摸鱼日历": DefaultApiSources.DAILY_NEWS_MOYU_APIS,
        }

        # 可配置的API源
        configurable_sources_map = {
            "IT之家": self.daily_news_ithome_apis,
            "历史上的今天": self.daily_news_history_apis,
        }

        # 优先返回静态配置，然后是可配置的
        if news_type in static_sources_map:
            return static_sources_map[news_type]
        return configurable_sources_map.get(news_type, [])

    def get_config_dir(self) -> Path:
        """获取配置目录"""
        return store.get_plugin_config_dir()

    def get_data_dir(self) -> Path:
        """获取数据目录"""
        data_dir = store.get_plugin_data_dir()
        return data_dir

    def get_cache_dir(self) -> Path:
        """获取缓存目录"""
        cache_dir = store.get_plugin_cache_dir()
        return cache_dir

    def get_template_dir(self) -> Path:
        """获取模板目录"""
        return Path(__file__).parent / "templates"


config = Config()


def update_config_from_global():
    """从全局配置中更新设置"""
    global config

    config = get_plugin_config(Config)
    logger.debug(f"已使用 get_plugin_config 更新配置，默认格式: {config.daily_news_default_format}")
