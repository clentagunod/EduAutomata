import sqlite3

from PySide6.QtCore import QObject, Qt, QTimer, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtGui import QDoubleValidator, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..analytics import summarize
from ..constants import APP_NAME, CATEGORIES
from ..data import Dataset
from ..preferences import Preferences, PreferencesStore
from ..storage import SQLiteRepository
from ..workbook import WorkbookSynchronizer
from .settings_dialog import SettingsDialog
from .learners_view import LearnersView
from .summary_view import SummaryView
from .theme import stylesheet


class WorkbookSyncSignals(QObject):
    completed = Signal(str)
    failed = Signal(str)


class WorkbookSyncWorker(QRunnable):
    def __init__(self, synchronizer, repository, workbook_path):
        super().__init__()
        self.synchronizer = synchronizer
        self.repository = repository
        self.workbook_path = workbook_path
        self.signals = WorkbookSyncSignals()

    @Slot()
    def run(self):
        try:
            path = self.synchronizer.sync(self.repository, self.workbook_path)
        except Exception as error:
            self.signals.failed.emit(str(error) or type(error).__name__)
        else:
            self.signals.completed.emit(str(path))


class MainWindow(QMainWindow):
    def __init__(
        self,
        preferences_store: PreferencesStore | None = None,
        repository: SQLiteRepository | None = None,
    ):
        super().__init__()
        self.preferences_store = preferences_store or PreferencesStore()
        self.preferences = self.preferences_store.load()
        self.repository = repository or SQLiteRepository()
        self.workbook_synchronizer = WorkbookSynchronizer()
        self.migration_error = None
        try:
            self.repository.import_legacy_csvs(
                self.preferences.legacy_csv_paths or {},
                self.preferences.legacy_learners_path,
            )
        except (OSError, ValueError, sqlite3.Error) as error:
            self.migration_error = str(error)
        self.category = self.preferences.category
        self.dark_mode = self.preferences.dark_mode
        self.dataset: Dataset | None = None
        self.selected_row: int | None = None
        self._sync_worker = None
        self._sync_pending = True

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(720, 640)
        self.resize(900, 760)
        if self.preferences.window_geometry:
            try:
                self.restoreGeometry(bytes.fromhex(self.preferences.window_geometry))
            except ValueError:
                pass

        self.build_ui()
        self.apply_theme()
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_entry)
        QShortcut(QKeySequence("Escape"), self, activated=self.clear_search)
        self.load_category(self.category, notify=False)
        self.set_sync_controls_enabled(False)
        if self.migration_error:
            QTimer.singleShot(
                0,
                lambda: self.show_message(
                    QMessageBox.Icon.Critical,
                    "Legacy data import failed",
                    f"No changes were made to the source files. {self.migration_error}",
                ),
            )
        else:
            QTimer.singleShot(100, self.start_workbook_sync)

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(26, 22, 26, 20)
        layout.setSpacing(18)

        header = QHBoxLayout()
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        eyebrow = QLabel("LEARNER RECORDS")
        eyebrow.setObjectName("eyebrow")
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        title_layout.addWidget(eyebrow)
        title_layout.addWidget(title)
        header.addLayout(title_layout)
        header.addStretch()

        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(138)
        self.category_combo.setMinimumHeight(38)
        for category in CATEGORIES:
            self.category_combo.addItem(category, category)
        self.category_combo.setCurrentIndex(
            max(0, self.category_combo.findData(self.category))
        )
        self.category_combo.currentIndexChanged.connect(self.category_changed)
        header.addWidget(self.category_combo)

        self.settings_button = QPushButton("Settings")
        self.settings_button.setMinimumHeight(38)
        self.settings_button.clicked.connect(self.open_settings)
        header.addWidget(self.settings_button)

        self.theme_button = QPushButton()
        self.theme_button.setMinimumSize(70, 38)
        self.theme_button.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_button)
        layout.addLayout(header)

        self.pages = QTabWidget()
        layout.addWidget(self.pages, 1)
        self.pages.addTab(self.build_entry_page(), "Entry")
        self.summary_view = SummaryView(self.repository)
        self.pages.addTab(self.summary_view, "Summary")
        self.learners_view = LearnersView(self.repository)
        self.learners_view.add_student_requested.connect(self.add_student)
        self.learners_view.delete_student_requested.connect(self.delete_student)
        self.pages.addTab(self.learners_view, "Learners")
        self.pages.currentChanged.connect(self.page_changed)

        self.footer = QLabel(
            'by <a href="https://github.com/clentagunod/">' "ClentIndustries</a>"
        )
        self.footer.setObjectName("footer")
        self.footer.setTextFormat(Qt.TextFormat.RichText)
        self.footer.setOpenExternalLinks(True)
        self.footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.footer)

        self.notification_label = QLabel()
        self.notification_label.setObjectName("notification")
        self.notification_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self.notification_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        self.statusBar().addPermanentWidget(self.notification_label, 1)
        self.notification_timer = QTimer(self)
        self.notification_timer.setSingleShot(True)
        self.notification_timer.timeout.connect(self.notification_label.clear)

    def build_entry_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(16)

        search_label = QLabel("FIND LEARNER")
        search_label.setObjectName("label")
        layout.addWidget(search_label)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search learner by name...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(46)
        self.search.textChanged.connect(self.search_changed)
        layout.addWidget(self.search)

        self.learner_card = QFrame()
        self.learner_card.setObjectName("learnerCard")
        learner_layout = QVBoxLayout(self.learner_card)
        learner_layout.setContentsMargins(18, 15, 18, 15)
        label = QLabel("SELECTED LEARNER")
        label.setObjectName("label")
        self.learner_name = QLabel("No learner selected")
        self.learner_name.setObjectName("learnerName")
        learner_layout.addWidget(label)
        learner_layout.addWidget(self.learner_name)
        layout.addWidget(self.learner_card)

        controls = QHBoxLayout()
        controls.setSpacing(14)
        week_layout = QVBoxLayout()
        week_label = QLabel("WEEK")
        week_label.setObjectName("label")
        self.week_combo = QComboBox()
        self.week_combo.setMinimumHeight(44)
        self.week_combo.currentIndexChanged.connect(self.update_value)
        week_layout.addWidget(week_label)
        week_layout.addWidget(self.week_combo)
        value_layout = QVBoxLayout()
        self.value_label = QLabel("ATTENDANCE")
        self.value_label.setObjectName("label")
        self.status_combo = QComboBox()
        self.status_combo.addItem("Present", 1)
        self.status_combo.addItem("Absent", 0)
        self.status_combo.setMinimumHeight(44)
        self.score_input = QLineEdit()
        self.score_input.setPlaceholderText("Enter score")
        self.score_input.setMinimumHeight(44)
        self.score_input.setValidator(
            QDoubleValidator(0.0, 999999999.99, 2, self.score_input)
        )
        value_layout.addWidget(self.value_label)
        value_layout.addWidget(self.status_combo)
        value_layout.addWidget(self.score_input)
        controls.addLayout(week_layout, 1)
        controls.addLayout(value_layout, 1)
        layout.addLayout(controls)

        self.save_button = QPushButton()
        self.save_button.setObjectName("primary")
        self.save_button.setMinimumHeight(48)
        self.save_button.clicked.connect(self.save_entry)
        layout.addWidget(self.save_button)

        self.source_label = QLabel()
        self.source_label.setObjectName("muted")
        self.source_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.source_label)
        layout.addStretch(1)
        return page

    def apply_theme(self):
        self.setStyleSheet(stylesheet(self.dark_mode))
        self.theme_button.setText("Light" if self.dark_mode else "Dark")
        self.theme_button.setToolTip(
            "Switch to light mode" if self.dark_mode else "Switch to dark mode"
        )
        self.refresh_summaries()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.preferences.dark_mode = self.dark_mode
        self.apply_theme()
        self.persist_preferences()

    def category_changed(self):
        category = self.category_combo.currentData()
        if category:
            self.load_category(category)

    def load_category(self, category, notify=True):
        self.category = category
        self.preferences.category = category
        self.update_entry_controls()
        self.selected_row = None
        self.learner_name.setText("No learner selected")
        try:
            self.dataset = self.repository.load(category)
        except (OSError, ValueError, sqlite3.Error) as error:
            self.dataset = None
            self.week_combo.clear()
            self.search.setCompleter(None)
            self.source_label.setText(str(self.repository.database_path))
            if notify:
                self.show_message(
                    QMessageBox.Icon.Warning,
                    "Unable to load database records",
                    str(error),
                )
            self.refresh_summaries()
            self.persist_preferences()
            return

        self.week_combo.blockSignals(True)
        self.week_combo.clear()
        for column in self.dataset.week_columns:
            self.week_combo.addItem(f"Week {self.week_number(column)}", column)
        self.week_combo.blockSignals(False)
        completer = QCompleter(
            [
                row["Learners"].strip()
                for row in self.dataset.rows
                if row.get("Learners")
            ],
            self.search,
        )
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.activated.connect(self.select_from_search)
        self.search.setCompleter(completer)
        self.selected_row = None
        self.learner_name.setText("No learner selected")
        self.source_label.setText(f"Local database: {self.repository.database_path}")
        self.update_value()
        self.refresh_summaries()
        self.persist_preferences()

    def update_entry_controls(self):
        is_attendance = self.category == "Attendance"
        self.value_label.setText("ATTENDANCE" if is_attendance else "SCORE")
        self.status_combo.setVisible(is_attendance)
        self.score_input.setVisible(not is_attendance)
        self.save_button.setText(
            "Save attendance"
            if is_attendance
            else f"Save {self.category.lower()} score"
        )

    def select_from_search(self, learner_name):
        if not self.dataset:
            return
        target = learner_name.strip().casefold()
        for index, row in enumerate(self.dataset.rows):
            if row.get("Learners", "").strip().casefold() == target:
                self.selected_row = index
                self.learner_name.setText(row["Learners"])
                self.update_value()
                return

    def search_changed(self, text):
        if not text.strip():
            self.selected_row = None
            self.learner_name.setText("No learner selected")

    def update_value(self):
        if self.selected_row is None or not self.dataset:
            return
        column = self.week_combo.currentData()
        if not column:
            return
        value = self.dataset.rows[self.selected_row].get(column, "") or ""
        if self.category == "Attendance":
            self.status_combo.setCurrentIndex(0 if value.strip() == "1" else 1)
        else:
            self.score_input.setText(value)

    def clear_search(self):
        self.search.clear()
        self.selected_row = None
        self.learner_name.setText("No learner selected")
        self.search.setFocus()

    def save_entry(self):
        if self._sync_worker is not None:
            self.show_message(
                QMessageBox.Icon.Warning,
                "Sync in progress",
                "Wait for the current workbook sync to finish before saving.",
            )
            return
        if not self.dataset or self.selected_row is None:
            self.show_message(
                QMessageBox.Icon.Warning,
                "No learner selected",
                "Search for a learner and choose a result before saving.",
            )
            return
        column = self.week_combo.currentData()
        if not column:
            self.show_message(
                QMessageBox.Icon.Warning, "No week", "Select a week first."
            )
            return

        if self.category == "Attendance":
            value = str(self.status_combo.currentData())
            description = "Present" if value == "1" else "Absent"
        else:
            value = self.score_input.text().strip()
            if not value:
                self.show_message(
                    QMessageBox.Icon.Warning,
                    "Score required",
                    "Enter a score before saving.",
                )
                return
            try:
                score = float(value)
            except ValueError:
                self.show_message(
                    QMessageBox.Icon.Warning,
                    "Invalid score",
                    "Enter a valid numeric score.",
                )
                return
            if score < 0:
                self.show_message(
                    QMessageBox.Icon.Warning,
                    "Invalid score",
                    "Score cannot be negative.",
                )
                return
            description = f"Score {value}"

        row = self.dataset.rows[self.selected_row]
        previous_value = row.get(column, "")
        row[column] = value
        try:
            self.repository.save(self.dataset)
        except (OSError, sqlite3.Error) as error:
            row[column] = previous_value
            self.show_message(
                QMessageBox.Icon.Critical, "Record save failed", str(error)
            )
            return

        self.refresh_summaries()
        self.search.selectAll()
        self.start_workbook_sync(
            f"{row['Learners']} saved for Week {self.week_number(column)} "
            f"({description}); updating the workbook."
        )

    def add_student(self, name, sex, grade, section):
        if self._sync_worker is not None:
            self.show_message(
                QMessageBox.Icon.Warning,
                "Sync in progress",
                "Wait for the current workbook sync to finish before adding a student.",
            )
            return
        try:
            self.repository.add_learner(
                name,
                sex,
                grade,
                section,
            )
        except (OSError, ValueError, sqlite3.Error) as error:
            self.show_message(QMessageBox.Icon.Warning, "Student not added", str(error))
            return

        self.learners_view.refresh()
        self.summary_view.invalidate()
        self.load_category(self.category, notify=False)
        self.start_workbook_sync(f"{name} added; updating the workbook.")

    def delete_student(self, name):
        if self._sync_worker is not None:
            self.show_message(
                QMessageBox.Icon.Warning,
                "Sync in progress",
                "Wait for the current workbook sync to finish before deleting a learner.",
            )
            return
        try:
            self.repository.delete_learner(
                name,
            )
        except (OSError, ValueError, sqlite3.Error) as error:
            self.show_message(
                QMessageBox.Icon.Warning, "Learner not deleted", str(error)
            )
            return

        self.learners_view.refresh()
        self.summary_view.invalidate()
        self.load_category(self.category, notify=False)
        self.start_workbook_sync(f"{name} deleted; updating the workbook.")

    def open_settings(self):
        dialog = SettingsDialog(
            self.preferences.workbook_path,
            self,
        )
        dialog.setStyleSheet(stylesheet(self.dark_mode))
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        self.preferences.workbook_path = dialog.workbook_path()
        self.persist_preferences()
        self.load_category(self.category)
        self.start_workbook_sync("Settings saved; refreshing the workbook.")

    def start_workbook_sync(self, message=None):
        if self._sync_worker is not None:
            return
        self._sync_pending = True
        self.set_sync_controls_enabled(False)
        self.show_message(
            QMessageBox.Icon.Information,
            "Syncing workbook",
            message or "Excel synchronization is running in the background.",
        )
        worker = WorkbookSyncWorker(
            self.workbook_synchronizer,
            self.repository,
            self.preferences.workbook_path,
        )
        worker.signals.completed.connect(self.workbook_sync_completed)
        worker.signals.failed.connect(self.workbook_sync_failed)
        self._sync_worker = worker
        QThreadPool.globalInstance().start(worker)

    def workbook_sync_completed(self, path):
        self._sync_worker = None
        self._sync_pending = False
        self.set_sync_controls_enabled(True)
        self.show_message(
            QMessageBox.Icon.Information,
            "Workbook synchronized",
            path,
        )

    def workbook_sync_failed(self, error):
        self._sync_worker = None
        self._sync_pending = False
        self.set_sync_controls_enabled(True)
        self.show_message(
            QMessageBox.Icon.Warning,
            "Workbook sync unavailable",
            error,
        )

    def set_sync_controls_enabled(self, enabled):
        self.settings_button.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        self.learners_view.add_button.setEnabled(enabled)
        self.learners_view.delete_button.setEnabled(enabled)

    def refresh_summaries(self):
        if (
            hasattr(self, "summary_view")
            and self.pages.currentWidget() is self.summary_view
        ):
            self.summary_view.refresh(self.dark_mode)

    def page_changed(self, index):
        page = self.pages.widget(index)
        if page is self.summary_view:
            self.refresh_summaries()
        elif page is self.learners_view:
            self.learners_view.refresh()

    def persist_preferences(self):
        try:
            self.preferences_store.save(self.preferences)
        except OSError as error:
            self.show_message(
                QMessageBox.Icon.Warning, "Preferences not saved", str(error)
            )

    def show_message(self, icon, title, text):
        if icon == QMessageBox.Icon.Critical:
            severity = "error"
        elif icon == QMessageBox.Icon.Warning:
            severity = "warning"
        else:
            severity = "success"
        self.notification_label.setProperty("severity", severity)
        self.notification_label.style().unpolish(self.notification_label)
        self.notification_label.style().polish(self.notification_label)
        self.notification_label.setText(f"{title}: {text}".replace("\n", " "))
        self.notification_timer.start(7000)

    @staticmethod
    def week_number(column):
        import re

        match = re.search(r"\d+\s*$", column)
        return int(match.group()) if match else 0

    def closeEvent(self, event):
        self.preferences.window_geometry = bytes(self.saveGeometry()).hex()
        self.persist_preferences()
        super().closeEvent(event)
