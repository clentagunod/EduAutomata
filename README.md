# Edu Automata

Edu Automata is a PySide6 desktop application for recording learner details, attendance, activity scores, and assessment scores. SQLite is the source of truth; Excel is an optional export containing separate Attendance, Activity, Assessment, and Learners worksheets.

## Run

Install the dependencies and start the application from the workspace root:

```powershell
python -m pip install -r requirements.txt
python main.py
```

The database is stored in the current user's application-data directory under `Edu Automata/database/records.sqlite3`. On first launch during development, existing CSV files are imported once if present. The CSV files are left untouched as a recovery copy and are not used for subsequent reads or writes. Use **Settings** to choose where Excel exports are written; exports are refreshed in the background after records change.

Preferences are stored under the current user's `Edu Automata` configuration folder. The app-data directory also contains the default `exports/ARAL_Synced.xlsx`; choose a different destination in Settings at any time. Packaged builds do not include CSV files, so each new installation starts with no learners and blank reporting periods. The user can add learners and records from the app.

## Build a Windows executable

Follow [PACKAGING_GUIDE.md](PACKAGING_GUIDE.md) to build a one-directory app with auto-py-to-exe and create a per-user installer with Inno Setup. The PyInstaller spec is also configured for one-directory output.

```powershell
python -m pip install -r requirements.txt
pyinstaller --noconfirm --clean EduAutomata.spec
```

The app folder is written under `dist/EduAutomata/`. New installations start with an empty learner database. The application uses Qt-drawn charts, requires only PySide6 Essentials, and does not bundle Matplotlib or NumPy.

## Structure

- `main.py`: application entry point.
- `source/preferences.py`: workbook destination and UI preferences.
- `source/data.py`: reporting-period and dataset definitions.
- `source/storage.py`: SQLite schema, repository, and one-time CSV migration.
- `source/ui/learners_view.py`: searchable, sortable learner register.
- `source/workbook.py`: Excel export from SQLite.
- `source/analytics.py`: weekly summary calculations.
- `source/ui/`: Qt main window, settings dialog, charts, and theme.
- `tests/`: automated service and analytics tests.
- `EduAutomata.spec`: PyInstaller configuration.

## Tests

```powershell
python -m unittest discover -s tests -v
```
