from datetime import datetime
import json
from typing import Any

from nonebot import get_bot, logger, require

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


from ..exceptions import InvalidTimeFormatException, ScheduleException
from .helpers import format_time, validate_time


class ScheduleManager:
    """定时任务管理器"""

    def __init__(self, store_instance=None):
        """初始化定时任务管理器

        Args:
            store_instance: 存储实例
        """
        self.store = store_instance

    async def add_job(
        self,
        group_id: int,
        news_type: str,
        hour: int,
        minute: int,
        format_type: str = "image",
    ) -> bool:
        """添加定时任务

        Args:
            group_id: 群组ID
            news_type: 日报类型
            hour: 小时
            minute: 分钟
            format_type: 格式类型

        Returns:
            是否成功添加

        Raises:
            ScheduleException: 定时任务操作失败
            InvalidTimeFormatException: 无效的时间格式
        """
        if not validate_time(hour, minute):
            raise InvalidTimeFormatException(
                message="无效的时间",
                time_str=f"{hour}:{minute}",
            )

        job_id = f"daily_news_{group_id}_{news_type}"

        try:
            try:
                scheduler.remove_job(job_id)
                logger.debug(f"已移除旧的定时任务: {job_id}")
            except Exception as e:
                logger.debug(f"移除旧任务时出现异常(可能任务不存在): {e}")

            scheduler.add_job(
                self.send_daily_news,
                "cron",
                hour=hour,
                minute=minute,
                id=job_id,
                args=[group_id, news_type, format_type],
                replace_existing=True,
                misfire_grace_time=60,
            )

            if self.store:
                self.store.set_group_schedule(
                    group_id=group_id,
                    news_type=news_type,
                    schedule_time=format_time(hour, minute),
                    format_type=format_type,
                )

            logger.debug(
                f"已为群 {group_id} 设置 {news_type} 日报定时任务，"
                f"时间: {format_time(hour, minute)}，格式: {format_type}"
            )
            return True
        except Exception as e:
            logger.error(
                f"添加定时任务失败 [group_id={group_id}, news_type={news_type}]: {e}"
            )
            raise ScheduleException(
                message=f"添加定时任务失败: {e}",
                group_id=group_id,
                news_type=news_type,
            )

    async def remove_job(self, group_id: int, news_type: str) -> bool:
        """移除定时任务

        Args:
            group_id: 群组ID
            news_type: 日报类型

        Returns:
            是否成功移除

        Raises:
            ScheduleException: 定时任务操作失败
        """
        job_id = f"daily_news_{group_id}_{news_type}"

        try:
            try:
                scheduler.remove_job(job_id)
                logger.debug(f"已移除定时任务: {job_id}")
            except Exception as e:
                logger.debug(f"移除任务时出现异常(可能任务不存在): {e}")

            if self.store:
                self.store.remove_group_schedule(group_id, news_type)

            return True
        except Exception as e:
            logger.error(
                f"移除定时任务失败 [group_id={group_id}, news_type={news_type}]: {e}"
            )
            raise ScheduleException(
                message=f"移除定时任务失败: {e}",
                group_id=group_id,
                news_type=news_type,
            )

    def get_jobs(self, group_id: int | None = None) -> list[dict[str, Any]]:
        """获取定时任务列表

        Args:
            group_id: 群组ID，如果为None则获取所有任务

        Returns:
            任务列表
        """
        jobs = []

        for job in scheduler.get_jobs():
            if not job.id.startswith("daily_news_"):
                continue

            parts = job.id.split("_")
            if len(parts) < 3:
                continue

            job_group_id = int(parts[2])

            if group_id is not None and job_group_id != group_id:
                continue

            job_news_type = parts[3]

            next_run = job.next_run_time
            next_run_str = (
                next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "未知"
            )

            schedule_config = None
            if self.store:
                schedule_config = self.store.get_group_schedule(
                    job_group_id, job_news_type
                )

            format_type = "image"
            if schedule_config and "format_type" in schedule_config:
                format_type = schedule_config["format_type"]

            schedule_time = f"{job.trigger.hour:02d}:{job.trigger.minute:02d}"

            news_description = "未知日报"
            from ..api.sources import get_news_source

            source = get_news_source(job_news_type)
            if source:
                news_description = source.description

            jobs.append(
                {
                    "group_id": job_group_id,
                    "news_type": job_news_type,
                    "schedule_time": schedule_time,
                    "next_run": next_run_str,
                    "format_type": format_type,
                    "news_description": news_description,
                }
            )

        return jobs

    async def send_daily_news(
        self,
        group_id: int,
        news_type: str,
        format_type: str = "image",
    ) -> bool:
        """发送日报

        Args:
            group_id: 群组ID
            news_type: 日报类型
            format_type: 格式类型

        Returns:
            是否成功发送
        """
        try:
            bot = get_bot()

            from ..api.sources import get_news_source

            source = get_news_source(news_type)

            if not source:
                logger.error(f"未知的日报类型: {news_type}")
                return False

            message = await source.fetch(format_type=format_type)

            await bot.send_group_msg(group_id=group_id, message=message)
            logger.info(f"已向群 {group_id} 发送 {news_type} 日报")

            return True
        except Exception as e:
            logger.error(
                f"发送日报失败 [group_id={group_id}, news_type={news_type}]: {e}"
            )
            return False

    async def init_jobs(self) -> bool:
        """初始化所有定时任务

        Returns:
            是否成功初始化
        """
        try:
            if not self.store:
                logger.warning("未提供存储实例，无法初始化定时任务")
                return False

            schedules = self.store.get_all_schedules()

            for group_id, group_schedules in schedules.items():
                for news_type, schedule in group_schedules.items():
                    if "schedule_time" in schedule:
                        try:
                            schedule_time = schedule["schedule_time"]
                            hour, minute = schedule_time.split(":")
                            format_type = schedule.get("format_type", "image")

                            from ..api.sources import get_news_source

                            if not get_news_source(news_type):
                                logger.warning(f"未知的日报类型: {news_type}，跳过加载")
                                continue

                            await self.add_job(
                                group_id=int(group_id),
                                news_type=news_type,
                                hour=int(hour),
                                minute=int(minute),
                                format_type=format_type,
                            )
                        except Exception as e:
                            logger.error(
                                f"加载单个定时任务失败 [group_id={group_id}, news_type={news_type}]: {e}"
                            )

            try:
                scheduler.add_job(
                    self.clear_expired_cache,
                    "interval",
                    hours=6,
                    id="clear_expired_cache",
                    replace_existing=True,
                )
            except Exception as e:
                logger.error(f"添加缓存清理任务失败: {e}")

            logger.info(
                f"日报调度器初始化完成，已加载 {len(scheduler.get_jobs())} 个定时任务"
            )
            return True
        except Exception as e:
            logger.error(f"日报调度器初始化失败: {e}")
            return False

    async def clear_expired_cache(self) -> int:
        """清理过期缓存

        Returns:
            清理的缓存数量
        """
        from ..utils.cache import news_cache

        count = news_cache.clear_expired()
        logger.info(f"已清理过期缓存，共 {count} 项")
        return count


class Store:
    """存储定时任务信息的类"""

    def __init__(self):
        """初始化存储"""
        from nonebot import require

        require("nonebot_plugin_localstore")
        import nonebot_plugin_localstore as localstore

        try:
            config_dir = localstore.get_plugin_config_dir()
        except (AttributeError, Exception):
            try:
                config_dir = localstore.get_config_dir("nonebot_plugin_multi_source_daily")
            except (AttributeError, Exception):
                from pathlib import Path
                config_dir = Path.home() / ".nonebot" / "nonebot_plugin_multi_source_daily" / "config"
                config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = config_dir / "schedules.json"
        self.data = self._load_data()

    def _load_data(self) -> dict[str, dict[str, dict[str, Any]]]:
        """加载数据

        Returns:
            加载的数据
        """
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.config_file.exists():
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return {}

        try:
            with open(self.config_file, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.error("定时任务数据格式错误，重置为空数据")
                return {}

            cleaned_data = {}
            for group_id, group_schedules in data.items():
                if not isinstance(group_schedules, dict):
                    continue

                cleaned_group = {}
                for news_type, schedule in group_schedules.items():
                    if (
                        not isinstance(schedule, dict)
                        or "schedule_time" not in schedule
                    ):
                        continue
                    cleaned_group[news_type] = schedule

                if cleaned_group:
                    cleaned_data[group_id] = cleaned_group

            return cleaned_data
        except json.JSONDecodeError:
            logger.error("定时任务数据文件损坏，创建新的空数据文件")
            backup_file = self.config_file.with_name(
                f"schedules.json.bak.{int(datetime.now().timestamp())}"
            )
            try:
                import shutil

                shutil.copy2(self.config_file, backup_file)
                logger.info(f"已将损坏的数据文件备份为: {backup_file}")
            except Exception as e:
                logger.error(f"备份损坏数据文件失败: {e}")

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return {}
        except Exception as e:
            logger.error(f"加载定时任务数据失败: {e}")
            return {}

    def _save_data(self) -> bool:
        """保存数据

        Returns:
            是否成功保存
        """
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存定时任务数据失败: {e}")
            return False

    def get_group_schedule(
        self, group_id: int, news_type: str
    ) -> dict[str, Any] | None:
        """获取群组的定时任务配置

        Args:
            group_id: 群组ID
            news_type: 日报类型

        Returns:
            定时任务配置
        """
        group_id_str = str(group_id)
        if group_id_str in self.data and news_type in self.data[group_id_str]:
            return self.data[group_id_str][news_type]
        return None

    def get_group_schedules(self, group_id: int) -> dict[str, dict[str, Any]]:
        """获取群组的所有定时任务配置

        Args:
            group_id: 群组ID

        Returns:
            所有定时任务配置
        """
        group_id_str = str(group_id)
        return self.data.get(group_id_str, {})

    def get_all_schedules(self) -> dict[str, dict[str, dict[str, Any]]]:
        """获取所有群组的定时任务配置

        Returns:
            所有群组的定时任务配置
        """
        return self.data

    def get_all_groups_by_news_type(self, news_type: str) -> list[str]:
        """获取订阅了指定日报类型的所有群组

        Args:
            news_type: 日报类型

        Returns:
            群组ID列表
        """
        groups = []
        for group_id, group_schedules in self.data.items():
            if news_type in group_schedules:
                groups.append(group_id)
        return groups

    def set_group_schedule(
        self, group_id: int, news_type: str, schedule_time: str, format_type: str
    ) -> bool:
        """设置群组的定时任务配置

        Args:
            group_id: 群组ID
            news_type: 日报类型
            schedule_time: 定时时间
            format_type: 格式类型

        Returns:
            是否成功设置
        """
        group_id_str = str(group_id)
        if group_id_str not in self.data:
            self.data[group_id_str] = {}

        self.data[group_id_str][news_type] = {
            "schedule_time": schedule_time,
            "format_type": format_type,
        }
        return self._save_data()

    def remove_group_schedule(self, group_id: int, news_type: str) -> bool:
        """移除群组的特定日报类型的定时任务配置

        Args:
            group_id: 群组ID
            news_type: 日报类型

        Returns:
            是否成功移除
        """
        group_id_str = str(group_id)
        if group_id_str in self.data and news_type in self.data[group_id_str]:
            del self.data[group_id_str][news_type]
            if not self.data[group_id_str]:
                del self.data[group_id_str]
            return self._save_data()
        return False


store = Store()

schedule_manager = ScheduleManager(store)
