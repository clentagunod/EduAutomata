import os
import sys
from pathlib import Path

APP_NAME = "Edu Automata"
CATEGORIES = ("Attendance", "Activity", "Assessment")
IS_FROZEN = getattr(sys, "frozen", False)
if IS_FROZEN:
    RESOURCE_ROOT = Path(
        getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)
    )
    PROJECT_ROOT = (
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        / APP_NAME
    )
else:
    RESOURCE_ROOT = Path(__file__).resolve().parents[1]
    PROJECT_ROOT = RESOURCE_ROOT
if os.environ.get("LOCALAPPDATA"):
    USER_DATA_DIRECTORY = Path(os.environ["LOCALAPPDATA"]) / APP_NAME
elif os.environ.get("XDG_DATA_HOME"):
    USER_DATA_DIRECTORY = Path(os.environ["XDG_DATA_HOME"]) / APP_NAME
else:
    USER_DATA_DIRECTORY = Path.home() / ".local" / "share" / APP_NAME

DATABASE_PATH = USER_DATA_DIRECTORY / "database" / "records.sqlite3"
DEFAULT_WORKBOOK_PATH = USER_DATA_DIRECTORY / "exports" / "ARAL_Synced.xlsx"
LEGACY_CSV_DIRECTORY = RESOURCE_ROOT / "csv_files"
LEGACY_CSV_PATHS = {
    category: LEGACY_CSV_DIRECTORY / f"{category}.csv" for category in CATEGORIES
}
LEGACY_LEARNERS_PATH = LEGACY_CSV_DIRECTORY / "Learners.csv"
