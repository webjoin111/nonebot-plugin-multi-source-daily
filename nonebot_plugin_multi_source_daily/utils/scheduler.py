from typing import Any

from nonebot import get_bot, logger, require
from ..exceptions import InvalidTimeFormatException, ScheduleException
from .core import format_time, validate_time, schedule_store

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402



class ScheduleManager:
    """定时任务管理器"""

    def __init__(self):
        """初始化定时任务管理器"""

    async def add_job(
        self,
        group_id: int,
        news_type: str,
        hour: int,
        minute: int,
        format_type: str = "image",
    ) -> bool:
        """添加定时任务"""
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
                if "No job by the id" in str(e):
                    logger.debug(f"旧任务 {job_id} 不存在，跳过移除")
                else:
                    logger.debug(f"移除旧任务时出现异常: {e}")

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

            schedule_store.set_group_schedule(
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
            logger.error(f"添加定时任务失败 [group_id={group_id}, news_type={news_type}]: {e}")
            raise ScheduleException(
                message=f"添加定时任务失败: {e}",
                group_id=group_id,
                news_type=news_type,
            )

    async def remove_job(self, group_id: int, news_type: str) -> bool:
        """移除定时任务"""
        job_id = f"daily_news_{group_id}_{news_type}"

        try:
            try:
                scheduler.remove_job(job_id)
                logger.debug(f"已移除定时任务: {job_id}")
            except Exception as e:
                if "No job by the id" in str(e):
                    logger.debug(f"任务 {job_id} 不存在，跳过移除")
                else:
                    logger.debug(f"移除任务时出现异常: {e}")

            schedule_store.remove_group_schedule(group_id, news_type)

            return True
        except Exception as e:
            logger.error(f"移除定时任务失败 [group_id={group_id}, news_type={news_type}]: {e}")
            raise ScheduleException(
                message=f"移除定时任务失败: {e}",
                group_id=group_id,
                news_type=news_type,
            )

    def get_jobs(self, group_id: int | None = None) -> list[dict[str, Any]]:
        """获取定时任务列表"""
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
            next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "未知"

            schedule_config = None
            if schedule_store:
                schedule_config = schedule_store.get_group_schedule(job_group_id, job_news_type)

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
        """发送日报"""
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
            logger.error(f"发送日报失败 [group_id={group_id}, news_type={news_type}]: {e}")
            return False

    async def init_jobs(self) -> bool:
        """初始化所有定时任务"""
        try:
            schedules = schedule_store.get_all_schedules()

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

            logger.info(f"日报调度器初始化完成，已加载 {len(scheduler.get_jobs())} 个定时任务")
            return True
        except Exception as e:
            logger.error(f"日报调度器初始化失败: {e}")
            return False

    async def clear_expired_cache(self) -> int:
        """清理过期缓存"""
        from ..utils.cache import news_cache

        count = news_cache.clear_expired()
        logger.info(f"已清理过期缓存，共 {count} 项")
        return count


schedule_manager = ScheduleManager()
