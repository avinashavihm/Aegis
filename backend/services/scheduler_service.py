"""Service for scheduling workflow executions"""
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
try:
    from croniter import croniter
except ImportError:
    # Fallback if croniter is not available
    croniter = None
import asyncio
import threading
import time
import logging

logger = logging.getLogger(__name__)


class Scheduler:
    """Scheduler for workflow executions"""
    
    def __init__(self):
        self.scheduled_tasks: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def schedule_workflow(
        self,
        schedule_id: str,
        workflow_id: str,
        schedule_type: str,  # 'cron', 'interval', 'once'
        schedule_config: Dict[str, Any],
        callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """
        Schedule a workflow execution.
        
        Args:
            schedule_id: Unique schedule ID
            workflow_id: Workflow ID to execute
            schedule_type: Type of schedule ('cron', 'interval', 'once')
            schedule_config: Schedule configuration
            callback: Callback function to execute workflow
        """
        task = {
            "schedule_id": schedule_id,
            "workflow_id": workflow_id,
            "schedule_type": schedule_type,
            "schedule_config": schedule_config,
            "callback": callback,
            "next_run": self._calculate_next_run(schedule_type, schedule_config),
            "created_at": datetime.utcnow()
        }
        
        self.scheduled_tasks[schedule_id] = task
        logger.info(f"Scheduled workflow {workflow_id} with schedule {schedule_id}")
    
    def _calculate_next_run(
        self,
        schedule_type: str,
        schedule_config: Dict[str, Any]
    ) -> Optional[datetime]:
        """Calculate next run time based on schedule type"""
        now = datetime.utcnow()
        
        if schedule_type == "cron":
            cron_expr = schedule_config.get("cron_expression")
            if cron_expr and croniter:
                cron = croniter(cron_expr, now)
                return cron.get_next(datetime)
            elif cron_expr:
                logger.warning("croniter not available, cron scheduling disabled")
        
        elif schedule_type == "interval":
            interval_seconds = schedule_config.get("interval_seconds", 60)
            return now + timedelta(seconds=interval_seconds)
        
        elif schedule_type == "once":
            run_at = schedule_config.get("run_at")
            if isinstance(run_at, str):
                run_at = datetime.fromisoformat(run_at)
            return run_at
        
        return None
    
    def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a scheduled task"""
        if schedule_id in self.scheduled_tasks:
            del self.scheduled_tasks[schedule_id]
            logger.info(f"Cancelled schedule {schedule_id}")
            return True
        return False
    
    def start(self) -> None:
        """Start the scheduler"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _run_scheduler(self) -> None:
        """Main scheduler loop"""
        while self.running:
            try:
                now = datetime.utcnow()
                
                # Check all scheduled tasks
                tasks_to_run = []
                for schedule_id, task in list(self.scheduled_tasks.items()):
                    if task["next_run"] and task["next_run"] <= now:
                        tasks_to_run.append(task)
                        # Calculate next run
                        task["next_run"] = self._calculate_next_run(
                            task["schedule_type"],
                            task["schedule_config"]
                        )
                
                # Execute tasks
                for task in tasks_to_run:
                    try:
                        task["callback"](
                            task["workflow_id"],
                            {
                                "schedule_id": task["schedule_id"],
                                "triggered_at": now.isoformat()
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"Error executing scheduled task {task['schedule_id']}: {e}",
                            exc_info=True
                        )
                
                # Sleep for a short interval
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                time.sleep(5)


# Global scheduler instance
_scheduler = Scheduler()


def get_scheduler() -> Scheduler:
    """Get the global scheduler instance"""
    return _scheduler


def parse_cron_expression(cron_expr: str) -> bool:
    """Validate cron expression"""
    if not croniter:
        return False
    try:
        croniter(cron_expr, datetime.utcnow())
        return True
    except Exception:
        return False


def parse_interval(interval_str: str) -> Optional[int]:
    """
    Parse interval string (e.g., '5m', '1h', '30s') to seconds.
    
    Args:
        interval_str: Interval string
    
    Returns:
        Interval in seconds or None if invalid
    """
    if not interval_str:
        return None
    
    interval_str = interval_str.lower().strip()
    
    # Extract number and unit
    if interval_str.endswith('s'):
        return int(interval_str[:-1])
    elif interval_str.endswith('m'):
        return int(interval_str[:-1]) * 60
    elif interval_str.endswith('h'):
        return int(interval_str[:-1]) * 3600
    elif interval_str.endswith('d'):
        return int(interval_str[:-1]) * 86400
    else:
        # Try to parse as integer (seconds)
        try:
            return int(interval_str)
        except ValueError:
            return None

