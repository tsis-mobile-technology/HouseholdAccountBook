import shutil
from datetime import datetime
from pathlib import Path
from app.core.config import DB_PATH, BACKUP_DIR

def perform_daily_backup(max_retained: int = 7) -> str | None:
    """Takes a snapshot of the SQLite DB file and cleans up older backups."""
    if not DB_PATH.exists():
        return None

    today_str = datetime.now().strftime("%Y%m%d")
    backup_file = BACKUP_DIR / f"account_book_{today_str}.db"

    # Only copy if today's backup does not already exist
    if not backup_file.exists():
        shutil.copy2(DB_PATH, backup_file)

    # Clean old backups exceeding max_retained
    backups = sorted(BACKUP_DIR.glob("account_book_*.db"), key=lambda p: p.name)
    if len(backups) > max_retained:
        for old in backups[:-max_retained]:
            try:
                old.unlink()
            except Exception:
                pass

    return str(backup_file)
