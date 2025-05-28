import json
import time
from pathlib import Path
from typing import Any, Dict, TypeVar, Generic

from nonebot import logger, require

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

T = TypeVar("T")


class BaseStorage(Generic[T]):
    """基础存储类"""

    def __init__(self, file_name: str, default_value: T):
        """初始化存储

        Args:
            file_name: 存储文件名
            default_value: 默认值
        """
        self.file_name = file_name
        self.default_value = default_value
        self.storage_file = self._get_storage_file()
        self.data: T = self._load_data()

    def _get_storage_file(self) -> Path:
        """获取存储文件路径"""
        try:
            config_dir = store.get_plugin_config_dir()
        except (AttributeError, Exception):
            try:
                config_dir = store.get_config_dir("nonebot_plugin_multi_source_daily")
            except (AttributeError, Exception):
                config_dir = (
                    Path.home()
                    / ".nonebot"
                    / "nonebot_plugin_multi_source_daily"
                    / "config"
                )
                config_dir.mkdir(parents=True, exist_ok=True)

        return config_dir / self.file_name

    def _load_data(self) -> T:
        """加载数据"""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.storage_file.exists():
            self._save_data(self.default_value)
            return self.default_value

        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError:
            logger.error(f"解析存储文件失败: {self.storage_file}")

            backup_file = self.storage_file.with_suffix(f".bak.{int(time.time())}")
            try:
                import shutil

                shutil.copy2(self.storage_file, backup_file)
                logger.info(f"已将损坏的数据文件备份为: {backup_file}")
            except Exception as e:
                logger.error(f"备份损坏数据文件失败: {e}")

            self._save_data(self.default_value)
            return self.default_value
        except Exception as e:
            logger.error(f"加载存储数据失败: {e}")
            return self.default_value

    def _save_data(self, data: T) -> bool:
        """保存数据"""
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存存储数据失败: {e}")
            return False

    def save(self) -> bool:
        """保存当前数据"""
        return self._save_data(self.data)

    def reset(self) -> bool:
        """重置为默认值"""
        self.data = self.default_value
        return self.save()


class ScheduleStorage(BaseStorage[Dict[str, Dict[str, Dict[str, Any]]]]):
    """定时任务存储类"""

    def __init__(self):
        """初始化定时任务存储"""
        super().__init__("schedules.json", {})
        self._migrate_old_data()

    def _migrate_old_data(self) -> bool:
        """迁移旧数据：将'知乎'改为'知乎日报'"""
        migrated = False
        for group_id, schedules in self.data.items():
            if "知乎" in schedules:
                schedules["知乎日报"] = schedules["知乎"]
                del schedules["知乎"]
                migrated = True
                logger.info(f"已将群 {group_id} 的'知乎'定时任务迁移到'知乎日报'")

        if migrated:
            self.save()
            logger.info("定时任务数据迁移完成")

        return migrated

    def set_group_schedule(
        self, group_id: int, news_type: str, schedule_time: str, format_type: str
    ) -> bool:
        """设置群组的定时任务配置"""
        group_id_str = str(group_id)
        if group_id_str not in self.data:
            self.data[group_id_str] = {}

        self.data[group_id_str][news_type] = {
            "schedule_time": schedule_time,
            "format_type": format_type,
        }
        return self.save()

    def remove_group_schedule(self, group_id: int, news_type: str) -> bool:
        """移除群组的特定日报类型的定时任务配置"""
        group_id_str = str(group_id)
        if group_id_str in self.data and news_type in self.data[group_id_str]:
            del self.data[group_id_str][news_type]
            if not self.data[group_id_str]:
                del self.data[group_id_str]
            return self.save()
        return False

    def get_group_schedules(self, group_id: int) -> Dict[str, Dict[str, Any]]:
        """获取群组的所有定时任务配置"""
        return self.data.get(str(group_id), {})

    def get_all_schedules(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """获取所有定时任务配置"""
        return self.data

    def get_group_schedule(
        self, group_id: int, news_type: str
    ) -> Dict[str, Any] | None:
        """获取群组的特定日报类型的定时任务配置"""
        group_id_str = str(group_id)
        if group_id_str in self.data and news_type in self.data[group_id_str]:
            return self.data[group_id_str][news_type]
        return None

    def get_all_groups_by_news_type(self, news_type: str) -> list[str]:
        """获取订阅了特定日报类型的所有群组ID"""
        groups = []
        for group_id, schedules in self.data.items():
            if news_type in schedules:
                groups.append(group_id)
        return groups


class ApiStatusStorage(BaseStorage[Dict[str, Any]]):
    """API状态存储类"""

    def __init__(self):
        """初始化API状态存储"""
        super().__init__("api_status.json", {})


schedule_store = ScheduleStorage()
api_status_store = ApiStatusStorage()
