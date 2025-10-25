"""
Report Scheduler

Manages scheduled report generation and delivery:
- Daily summaries at configured time
- Weekly trends on Monday mornings
- Monthly reports on 1st of month
- Manual report triggers
"""

from typing import Dict, Any, List, Callable, Optional
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from shared.logging import get_logger
from shared.report_generator import get_report_generator, ReportType

logger = get_logger(__name__)


class ReportSchedule:
    """Report schedule configuration"""

    def __init__(
        self,
        report_type: ReportType,
        enabled: bool = True,
        cron_expression: Optional[str] = None,
        hour: int = 8,
        minute: int = 0,
        day_of_week: Optional[str] = None,
        day: Optional[int] = None
    ):
        self.report_type = report_type
        self.enabled = enabled
        self.cron_expression = cron_expression
        self.hour = hour
        self.minute = minute
        self.day_of_week = day_of_week  # 'mon', 'tue', etc.
        self.day = day  # Day of month (1-31)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "report_type": self.report_type.value,
            "enabled": self.enabled,
            "cron_expression": self.cron_expression,
            "hour": self.hour,
            "minute": self.minute,
            "day_of_week": self.day_of_week,
            "day": self.day
        }


class ReportScheduler:
    """Manages scheduled report generation"""

    def __init__(self, report_callback: Optional[Callable] = None):
        """
        Initialize report scheduler

        Args:
            report_callback: Async function to call with generated report
                           Signature: async def callback(report_type: str, report_text: str)
        """
        self.scheduler = AsyncIOScheduler()
        self.report_callback = report_callback
        self.report_generator = None
        self.logger = logger

        # Default schedules
        self.schedules: Dict[ReportType, ReportSchedule] = {
            ReportType.DAILY_SUMMARY: ReportSchedule(
                report_type=ReportType.DAILY_SUMMARY,
                enabled=True,
                hour=8,
                minute=0
            ),
            ReportType.WEEKLY_TRENDS: ReportSchedule(
                report_type=ReportType.WEEKLY_TRENDS,
                enabled=True,
                hour=8,
                minute=0,
                day_of_week='mon'
            ),
            ReportType.MONTHLY_SUMMARY: ReportSchedule(
                report_type=ReportType.MONTHLY_SUMMARY,
                enabled=False,  # Disabled by default
                hour=8,
                minute=0,
                day=1
            )
        }

    def set_report_generator(self, infrastructure_agent=None, network_agent=None, alert_manager=None):
        """Set up report generator with agents"""
        self.report_generator = get_report_generator(
            infrastructure_agent=infrastructure_agent,
            network_agent=network_agent,
            alert_manager=alert_manager
        )

    async def _generate_and_send_report(self, report_type: ReportType):
        """
        Generate report and send via callback

        Args:
            report_type: Type of report to generate
        """
        try:
            self.logger.info(f"Generating scheduled report: {report_type.value}")

            if not self.report_generator:
                self.logger.error("Report generator not initialized")
                return

            # Generate report
            if report_type == ReportType.DAILY_SUMMARY:
                report_text = await self.report_generator.generate_daily_summary()
            elif report_type == ReportType.WEEKLY_TRENDS:
                report_text = await self.report_generator.generate_weekly_trends()
            elif report_type == ReportType.MONTHLY_SUMMARY:
                report_text = await self.report_generator.generate_monthly_summary()
            else:
                self.logger.error(f"Unknown report type: {report_type}")
                return

            # Send via callback
            if self.report_callback:
                await self.report_callback(report_type.value, report_text)
                self.logger.info(f"Report sent: {report_type.value}")
            else:
                self.logger.warning("No report callback configured")

        except Exception as e:
            self.logger.error(f"Error generating report {report_type.value}: {e}")

    def start(self):
        """Start the scheduler"""
        try:
            # Add jobs based on schedules
            for report_type, schedule in self.schedules.items():
                if not schedule.enabled:
                    continue

                # Build cron trigger
                if schedule.cron_expression:
                    trigger = CronTrigger.from_crontab(schedule.cron_expression)
                else:
                    trigger_kwargs = {
                        'hour': schedule.hour,
                        'minute': schedule.minute
                    }

                    if schedule.day_of_week:
                        trigger_kwargs['day_of_week'] = schedule.day_of_week

                    if schedule.day:
                        trigger_kwargs['day'] = schedule.day

                    trigger = CronTrigger(**trigger_kwargs)

                # Add job
                self.scheduler.add_job(
                    self._generate_and_send_report,
                    trigger=trigger,
                    args=[report_type],
                    id=f"report_{report_type.value}",
                    replace_existing=True
                )

                self.logger.info(f"Scheduled {report_type.value}: {trigger}")

            # Start scheduler
            self.scheduler.start()
            self.logger.info("Report scheduler started")

        except Exception as e:
            self.logger.error(f"Error starting scheduler: {e}")

    def stop(self):
        """Stop the scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                self.logger.info("Report scheduler stopped")
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {e}")

    def update_schedule(self, report_type: ReportType, enabled: Optional[bool] = None,
                       hour: Optional[int] = None, minute: Optional[int] = None):
        """
        Update report schedule

        Args:
            report_type: Type of report to update
            enabled: Enable/disable the report
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
        """
        try:
            if report_type not in self.schedules:
                self.logger.error(f"Unknown report type: {report_type}")
                return False

            schedule = self.schedules[report_type]

            # Update schedule
            if enabled is not None:
                schedule.enabled = enabled

            if hour is not None:
                schedule.hour = hour

            if minute is not None:
                schedule.minute = minute

            # Restart scheduler to apply changes
            if self.scheduler.running:
                self.stop()
                self.start()

            self.logger.info(f"Updated schedule for {report_type.value}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating schedule: {e}")
            return False

    def get_schedules(self) -> Dict[str, Dict[str, Any]]:
        """Get all configured schedules"""
        return {
            report_type.value: schedule.to_dict()
            for report_type, schedule in self.schedules.items()
        }

    def get_next_run_times(self) -> Dict[str, Optional[datetime]]:
        """Get next run times for all scheduled reports"""
        next_runs = {}

        for job in self.scheduler.get_jobs():
            if job.id.startswith("report_"):
                report_type = job.id.replace("report_", "")
                next_runs[report_type] = job.next_run_time

        return next_runs

    async def trigger_report_now(self, report_type: ReportType):
        """
        Manually trigger a report immediately

        Args:
            report_type: Type of report to generate
        """
        await self._generate_and_send_report(report_type)


# Global instance
_report_scheduler = None


def get_report_scheduler(report_callback: Optional[Callable] = None):
    """Get or create the global report scheduler instance"""
    global _report_scheduler
    if _report_scheduler is None:
        _report_scheduler = ReportScheduler(report_callback=report_callback)
    elif report_callback is not None:
        _report_scheduler.report_callback = report_callback
    return _report_scheduler
