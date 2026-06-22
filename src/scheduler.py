"""Scheduler for the Ramayan Video Generator.

Provides APScheduler-based daily scheduling that triggers the pipeline
orchestrator at a configured time.

Validates: Requirements 1.1
"""

import logging
from typing import Any, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config_loader import PipelineConfig

logger = logging.getLogger(__name__)


class PipelineScheduler:
    """Schedules daily pipeline execution using APScheduler.

    Parses the configured schedule_time (HH:MM format) and creates
    a CronTrigger that fires once per day at that time.

    Args:
        pipeline_config: PipelineConfig with schedule_time.
        orchestrator: The VideoGeneratorOrchestrator to invoke.
    """

    def __init__(
        self,
        pipeline_config: PipelineConfig,
        orchestrator: Any,
    ):
        self._pipeline_config = pipeline_config
        self._orchestrator = orchestrator
        self._scheduler: Optional[BlockingScheduler] = None

        # Parse schedule time
        parts = pipeline_config.schedule_time.split(":")
        self._hour = int(parts[0])
        self._minute = int(parts[1])

    def _run_pipeline_job(self) -> None:
        """Job function called by the scheduler.

        Invokes the orchestrator's run_pipeline method and logs the result.
        """
        logger.info("Scheduled pipeline run triggered at %s", self._pipeline_config.schedule_time)
        try:
            result = self._orchestrator.run_pipeline()
            if result.success:
                logger.info(
                    "Scheduled run completed: Episode %d (%s) → %s",
                    result.episode_number,
                    result.kanda_name,
                    result.output_path,
                )
            else:
                logger.error(
                    "Scheduled run failed: Episode %d (%s) — %s",
                    result.episode_number,
                    result.kanda_name,
                    result.error_message,
                )
        except Exception as e:
            logger.error("Scheduled pipeline run raised an exception: %s", e)

    def start(self) -> None:
        """Start the scheduler.

        Blocks the current thread. The pipeline job runs daily at the
        configured time.
        """
        self._scheduler = BlockingScheduler()

        trigger = CronTrigger(hour=self._hour, minute=self._minute)

        self._scheduler.add_job(
            self._run_pipeline_job,
            trigger=trigger,
            id="ramayan_daily_pipeline",
            name="Ramayan Daily Video Generation",
            replace_existing=True,
        )

        logger.info(
            "Scheduler started. Pipeline will run daily at %02d:%02d",
            self._hour,
            self._minute,
        )

        try:
            self._scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped.")

    def stop(self) -> None:
        """Stop the scheduler if it is running."""
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down.")

    def run_once(self) -> Any:
        """Run the pipeline once immediately (without scheduling).

        Useful for testing or manual invocation.

        Returns:
            The PipelineResult from the orchestrator.
        """
        return self._run_pipeline_job()
