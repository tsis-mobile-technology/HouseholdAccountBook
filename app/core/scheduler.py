import asyncio
import logging
from datetime import datetime, timedelta
from app.services.gdrive_service import load_gdrive_config, upload_backup_to_drive, GDRIVE_CREDS_FILE
from app.core.backup import perform_daily_backup

logger = logging.getLogger("scheduler")

_scheduler_task: asyncio.Task | None = None
_running = False

async def backup_scheduler_worker():
    """Background worker that periodically checks and triggers backups."""
    global _running
    logger.info("Starting background backup scheduler...")
    while _running:
        try:
            config = load_gdrive_config()
            schedule = config.get("schedule", "off")

            if schedule != "off":
                now = datetime.now()
                last_time_str = config.get("last_backup_time")
                should_backup = False

                if not last_time_str:
                    should_backup = True
                else:
                    try:
                        last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
                        elapsed = now - last_time

                        if schedule == "daily" and elapsed >= timedelta(days=1):
                            should_backup = True
                        elif schedule == "weekly" and elapsed >= timedelta(days=7):
                            should_backup = True
                        elif schedule == "monthly" and elapsed >= timedelta(days=30):
                            should_backup = True
                    except Exception as e:
                        logger.warning(f"Error parsing last_backup_time: {e}")
                        should_backup = True

                if should_backup:
                    logger.info(f"Triggering scheduled backup (schedule={schedule})...")
                    # 1. Local daily snapshot
                    perform_daily_backup()

                    # 2. Upload to Google Drive if credentials exist
                    if GDRIVE_CREDS_FILE.exists():
                        try:
                            res = upload_backup_to_drive()
                            logger.info(f"Scheduled Google Drive backup completed: {res.get('file_name')}")
                        except Exception as e:
                            logger.error(f"Scheduled Google Drive backup failed: {e}")

        except Exception as e:
            logger.error(f"Error in backup_scheduler_worker loop: {e}")

        # Sleep for 15 minutes before checking again
        try:
            await asyncio.sleep(900)
        except asyncio.CancelledError:
            break

def start_scheduler():
    """Starts the backup scheduler background task."""
    global _scheduler_task, _running
    if _scheduler_task is None or _scheduler_task.done():
        _running = True
        loop = asyncio.get_event_loop()
        _scheduler_task = loop.create_task(backup_scheduler_worker())
        logger.info("Backup scheduler initiated.")

def stop_scheduler():
    """Stops the backup scheduler gracefully."""
    global _scheduler_task, _running
    _running = False
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Backup scheduler cancelled.")
