import csv
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .constants import CATEGORIES, DATABASE_PATH
from .data import Dataset, category_columns

DEFAULT_PERIODS = {
    "Attendance": [f"Week {number}" for number in range(1, 9)],
    "Activity": [f"Activity {number}" for number in range(1, 9)],
    "Assessment": [f"Assessment{number}" for number in range(1, 9)],
}
PERIOD_TABLES = {
    "Attendance": "attendance_periods",
    "Activity": "activity_periods",
    "Assessment": "assessment_periods",
}
RECORD_TABLES = {
    "Attendance": "attendance_records",
    "Activity": "activity_records",
    "Assessment": "assessment_records",
}


class SQLiteRepository:
    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or DATABASE_PATH
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS learners (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    sex TEXT NOT NULL DEFAULT '' CHECK (sex IN ('', 'F', 'M')),
                    grade TEXT NOT NULL DEFAULT '',
                    section TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS app_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """)
            for category in CATEGORIES:
                period_table = PERIOD_TABLES[category]
                record_table = RECORD_TABLES[category]
                connection.execute(f"""CREATE TABLE IF NOT EXISTS {period_table} (
                        name TEXT PRIMARY KEY,
                        position INTEGER NOT NULL
                    )""")
                connection.execute(f"""CREATE TABLE IF NOT EXISTS {record_table} (
                        learner_id INTEGER NOT NULL REFERENCES learners(id)
                            ON DELETE CASCADE,
                        period TEXT NOT NULL REFERENCES {period_table}(name)
                            ON DELETE CASCADE,
                        value TEXT,
                        PRIMARY KEY (learner_id, period)
                    )""")
                if not connection.execute(
                    f"SELECT 1 FROM {period_table} LIMIT 1"
                ).fetchone():
                    self._replace_periods(
                        connection, category, DEFAULT_PERIODS[category]
                    )

    def _replace_periods(
        self, connection: sqlite3.Connection, category: str, names: list[str]
    ) -> None:
        period_table = PERIOD_TABLES[category]
        connection.execute(f"DELETE FROM {period_table}")
        connection.executemany(
            f"INSERT INTO {period_table}(name, position) VALUES (?, ?)",
            [(name, index) for index, name in enumerate(names)],
        )

    @staticmethod
    def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
        with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames or "Learners" not in reader.fieldnames:
                raise ValueError(f'{path.name} must contain a "Learners" header.')
            if len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError(f"{path.name} contains duplicate column names.")
            return list(reader.fieldnames), list(reader)

    def import_legacy_csvs(
        self, csv_paths: dict[str, Path], learners_path: Path
    ) -> bool:
        with self.connection() as connection:
            imported = connection.execute(
                "SELECT value FROM app_metadata WHERE key = 'legacy_csv_imported'"
            ).fetchone()
            if imported:
                return False

            learner_table = None
            if learners_path.is_file():
                learner_table = self._read_csv(learners_path)
                if not {"Sex", "Grade-Section"}.issubset(learner_table[0]):
                    raise ValueError(
                        f'{learners_path.name} must contain "Sex" and "Grade-Section".'
                    )

            category_tables = {}
            for category in CATEGORIES:
                path = csv_paths.get(category)
                if path and path.is_file():
                    category_tables[category] = self._read_csv(path)

            if learner_table:
                for row in learner_table[1]:
                    name = (row.get("Learners") or "").strip()
                    if not name:
                        continue
                    grade_section = (row.get("Grade-Section") or "").strip()
                    grade, separator, section = grade_section.partition(" - ")
                    sex = (row.get("Sex") or "").strip().upper()
                    if sex not in {"F", "M"}:
                        sex = ""
                    connection.execute(
                        """INSERT OR IGNORE INTO learners(name, sex, grade, section)
                           VALUES (?, ?, ?, ?)""",
                        (name, sex, grade if separator else grade_section, section),
                    )

            for category, (headers, rows) in category_tables.items():
                periods = category_columns(category, headers)
                if not periods:
                    raise ValueError(f"{category} CSV has no reporting period columns.")
                self._replace_periods(connection, category, periods)
                for row in rows:
                    name = (row.get("Learners") or "").strip()
                    if not name:
                        continue
                    connection.execute(
                        "INSERT OR IGNORE INTO learners(name) VALUES (?)", (name,)
                    )
                    learner = connection.execute(
                        "SELECT id FROM learners WHERE name = ? COLLATE NOCASE",
                        (name,),
                    ).fetchone()
                    connection.executemany(
                        f"""INSERT INTO {RECORD_TABLES[category]}
                               (learner_id, period, value) VALUES (?, ?, ?)
                           ON CONFLICT(learner_id, period)
                           DO UPDATE SET value = excluded.value""",
                        [
                            (learner["id"], period, row.get(period) or None)
                            for period in periods
                        ],
                    )

            connection.execute(
                "INSERT INTO app_metadata(key, value) VALUES ('legacy_csv_imported', '1')"
            )
            return bool(learner_table or category_tables)

    def load(self, category: str) -> Dataset:
        if category not in CATEGORIES:
            raise ValueError(f"Unknown record category: {category}")
        period_table = PERIOD_TABLES[category]
        record_table = RECORD_TABLES[category]
        with self.connection() as connection:
            periods = [
                row["name"]
                for row in connection.execute(
                    f"SELECT name FROM {period_table} ORDER BY position"
                )
            ]
            learners = list(
                connection.execute(
                    "SELECT id, name FROM learners ORDER BY name COLLATE NOCASE"
                )
            )
            values = {
                (row["learner_id"], row["period"]): row["value"] or ""
                for row in connection.execute(
                    f"SELECT learner_id, period, value FROM {record_table}"
                )
            }
            rows = []
            for learner in learners:
                row = {"Learners": learner["name"]}
                row.update(
                    {
                        period: values.get((learner["id"], period), "")
                        for period in periods
                    }
                )
                rows.append(row)
        return Dataset(category, ["Learners", *periods], rows, periods)

    def load_learners(self) -> tuple[list[str], list[dict[str, str]]]:
        with self.connection() as connection:
            rows = [
                {
                    "Learners": row["name"],
                    "Sex": row["sex"],
                    "Grade-Section": " - ".join(
                        value for value in (row["grade"], row["section"]) if value
                    ),
                }
                for row in connection.execute(
                    "SELECT name, sex, grade, section FROM learners "
                    "ORDER BY name COLLATE NOCASE"
                )
            ]
        return ["Learners", "Sex", "Grade-Section"], rows

    def save(self, dataset: Dataset) -> None:
        if dataset.category not in CATEGORIES:
            raise ValueError(f"Unknown record category: {dataset.category}")
        record_table = RECORD_TABLES[dataset.category]
        with self.connection() as connection:
            for row in dataset.rows:
                learner = connection.execute(
                    "SELECT id FROM learners WHERE name = ? COLLATE NOCASE",
                    (row["Learners"],),
                ).fetchone()
                if not learner:
                    continue
                for period in dataset.week_columns:
                    value = (row.get(period) or "").strip()
                    if value:
                        connection.execute(
                            f"""INSERT INTO {record_table}(learner_id, period, value)
                               VALUES (?, ?, ?)
                               ON CONFLICT(learner_id, period)
                               DO UPDATE SET value = excluded.value""",
                            (learner["id"], period, value),
                        )
                    else:
                        connection.execute(
                            f"DELETE FROM {record_table} "
                            "WHERE learner_id = ? AND period = ?",
                            (learner["id"], period),
                        )

    def add_learner(self, name: str, sex: str, grade: str, section: str) -> None:
        name, sex = name.strip(), sex.strip().upper()
        grade, section = grade.strip(), section.strip()
        if not name or not grade or not section:
            raise ValueError("Name, grade, and section are required.")
        if sex not in {"F", "M"}:
            raise ValueError("Sex must be F or M.")
        try:
            with self.connection() as connection:
                connection.execute(
                    "INSERT INTO learners(name, sex, grade, section) VALUES (?, ?, ?, ?)",
                    (name, sex, grade, section),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(f"A learner named {name} already exists.") from error

    def delete_learner(self, name: str) -> None:
        with self.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM learners WHERE name = ? COLLATE NOCASE", (name.strip(),)
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Learner {name} was not found.")
