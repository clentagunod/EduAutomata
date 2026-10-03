import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import (
    APP_NAME,
    CATEGORIES,
    DEFAULT_WORKBOOK_PATH,
    LEGACY_CSV_PATHS,
    LEGACY_LEARNERS_PATH,
    PROJECT_ROOT,
)


@dataclass
class Preferences:
    workbook_path: Path
    dark_mode: bool = False
    category: str = "Attendance"
    window_geometry: str | None = None
    legacy_csv_paths: dict[str, Path] | None = None
    legacy_learners_path: Path = LEGACY_LEARNERS_PATH

    @classmethod
    def defaults(cls) -> "Preferences":
        return cls(
            workbook_path=DEFAULT_WORKBOOK_PATH,
            legacy_csv_paths=dict(LEGACY_CSV_PATHS),
        )


class PreferencesStore:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or self.default_config_path()
        self.legacy_config_path = (
            self.default_legacy_config_path() if config_path is None else None
        )

    @staticmethod
    def default_config_path() -> Path:
        app_data = os.environ.get("APPDATA")
        if app_data:
            base = Path(app_data)
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / APP_NAME / "preferences.json"

    @staticmethod
    def default_legacy_config_path() -> Path:
        app_data = os.environ.get("APPDATA")
        if app_data:
            base = Path(app_data)
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "ARAL Automata" / "preferences.json"

    def load(self) -> Preferences:
        preferences = Preferences.defaults()
        source_path = self.config_path
        if (
            not source_path.exists()
            and self.legacy_config_path
            and self.legacy_config_path.exists()
        ):
            source_path = self.legacy_config_path
        try:
            raw: Any = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return preferences

        if not isinstance(raw, dict):
            return preferences

        csv_paths = raw.get("csv_paths", {})
        if isinstance(csv_paths, dict):
            for category in CATEGORIES:
                value = csv_paths.get(category)
                if isinstance(value, str) and value.strip():
                    preferences.legacy_csv_paths[category] = Path(value).expanduser()

        workbook_path = raw.get("workbook_path")
        if isinstance(workbook_path, str) and workbook_path.strip():
            preferences.workbook_path = Path(workbook_path).expanduser()
            legacy_workbook_paths = {
                PROJECT_ROOT / "ARAL_Synced.xlsx",
                PROJECT_ROOT / "excel_synced" / "ARAL_Synced.xlsx",
                DEFAULT_WORKBOOK_PATH.parents[1] / "ARAL_Synced.xlsx",
            }
            if preferences.workbook_path in legacy_workbook_paths:
                preferences.workbook_path = DEFAULT_WORKBOOK_PATH

        learners_path = raw.get("learners_path")
        if isinstance(learners_path, str) and learners_path.strip():
            preferences.legacy_learners_path = Path(learners_path).expanduser()

        preferences.dark_mode = bool(raw.get("dark_mode", False))
        category = raw.get("category")
        if category in CATEGORIES:
            preferences.category = category
        geometry = raw.get("window_geometry")
        if isinstance(geometry, str):
            preferences.window_geometry = geometry
        return preferences

    def save(self, preferences: Preferences) -> None:
        payload = {
            "workbook_path": str(preferences.workbook_path),
            "dark_mode": preferences.dark_mode,
            "category": preferences.category,
            "window_geometry": preferences.window_geometry,
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.config_path.parent,
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                json.dump(payload, temporary_file, indent=2)
                temporary_file.write("\n")
                temporary_path = Path(temporary_file.name)
            os.replace(temporary_path, self.config_path)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()
