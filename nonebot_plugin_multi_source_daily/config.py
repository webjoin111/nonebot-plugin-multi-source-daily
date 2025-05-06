from pathlib import Path

from nonebot import require, get_plugin_config
from pydantic import BaseModel, Field

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

from .models import ApiSource


class Config(BaseModel):
    """插件配置类"""

    daily_news_60s_apis: list[ApiSource] = Field(
        default_factory=lambda: [
            ApiSource(
                url="https://api.03c3.cn/api/zb", priority=1, parser="binary_image"
            ),
            ApiSource(
                url="https://api.southerly.top/api/60s",
                priority=2,
                parser="binary_image",
            ),
        ]
    )

    daily_news_zhihu_apis: list[ApiSource] = Field(
        default_factory=lambda: [
            ApiSource(
                url="https://api.vvhan.com/api/hotlist/zhihuDay",
                priority=1,
                parser="vvhan",
            ),
        ]
    )

    daily_news_moyu_apis: list[ApiSource] = Field(
        default_factory=lambda: [
            ApiSource(
                url="https://api.vvhan.com/api/moyu", priority=1, parser="binary_image"
            ),
        ]
    )

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

    daily_news_template_dir: str | None = None

    daily_news_enable_personal_sub: bool = False

    daily_news_enable_stats: bool = False
    daily_news_stats_save_interval: int = 3600

    class Config:
        extra = "ignore"

    def get_api_sources(self, news_type: str) -> list[ApiSource]:
        """获取指定日报类型的API源列表"""
        sources_map = {
            "60s": self.daily_news_60s_apis,
            "知乎": self.daily_news_zhihu_apis,
            "moyu": self.daily_news_moyu_apis,
            "ithome": self.daily_news_ithome_apis,
            "历史上的今天": self.daily_news_history_apis,
        }
        return sources_map.get(news_type, [])

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
        if self.daily_news_template_dir:
            return Path(self.daily_news_template_dir)
        return Path(__file__).parent / "templates"


config = Config()


def update_config_from_global():
    """从全局配置中更新设置"""
    from nonebot import get_driver

    global config

    try:
        plugin_config = get_plugin_config(Config)
        config = plugin_config
    except Exception:
        driver = get_driver()

        try:
            config_dict = driver.config.model_dump()
        except AttributeError:
            try:
                config_dict = driver.config.dict()
            except AttributeError:
                config_dict = {}

        for key, value in config_dict.items():
            if key.startswith("daily_news_") and hasattr(config, key):
                setattr(config, key, value)
