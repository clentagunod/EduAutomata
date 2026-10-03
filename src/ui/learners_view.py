import sqlite3

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    QSortFilterProxyModel,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..storage import SQLiteRepository


class LearnersTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers: list[str] = []
        self.rows: list[dict[str, str]] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        return self.rows[index.row()].get(self.headers[index.column()], "") or ""

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.headers[section] if 0 <= section < len(self.headers) else None
        return str(section + 1)

    def set_table(self, headers, rows):
        self.beginResetModel()
        self.headers = headers
        self.rows = rows
        self.endResetModel()


class LearnersView(QWidget):
    add_student_requested = Signal(str, str, str, str)
    delete_student_requested = Signal(str)

    def __init__(self, repository: SQLiteRepository, parent=None):
        super().__init__(parent)
        self.repository = repository

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(12)

        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter learners...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(42)
        controls.addWidget(self.search, 1)
        self.count = QLabel("No learner records loaded")
        self.count.setObjectName("muted")
        controls.addWidget(self.count)
        self.add_button = QPushButton("ADD A STUDENT")
        self.add_button.setObjectName("primary")
        self.add_button.setMinimumHeight(42)
        self.add_button.clicked.connect(self.open_add_student)
        controls.addWidget(self.add_button)
        self.delete_button = QPushButton("DELETE LEARNER")
        self.delete_button.setMinimumHeight(42)
        self.delete_button.clicked.connect(self.delete_selected_student)
        controls.addWidget(self.delete_button)
        layout.addLayout(controls)

        self.model = LearnersTableModel(self)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        self.status = QLabel()
        self.status.setObjectName("muted")
        self.status.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.status)
        self.loaded_path: Path | None = None

    def open_add_student(self):
        dialog = AddStudentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.add_student_requested.emit(
                dialog.name_input.text().strip(),
                dialog.sex_combo.currentData(),
                dialog.grade_input.text().strip(),
                dialog.section_input.text().strip(),
            )

    def delete_selected_student(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self, "No learner selected", "Select a learner to delete."
            )
            return

        source_index = self.proxy.mapToSource(selected_rows[0])
        name = self.model.rows[source_index.row()].get("Learners", "").strip()
        if not name:
            QMessageBox.warning(
                self, "Invalid learner", "The selected row has no learner name."
            )
            return
        answer = QMessageBox.question(
            self,
            "Delete Learner",
            f"Delete {name} and all of their records from the local database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.delete_student_requested.emit(name)

    def refresh(self):
        try:
            headers, rows = self.repository.load_learners()
        except (OSError, ValueError, sqlite3.Error) as error:
            self.model.set_table([], [])
            self.status.setText(str(error))
            self.count.setText("Learner records unavailable")
            return

        self.model.set_table(headers, rows)
        self.status.setText(f"Local database: {self.repository.database_path}")
        self.count.setText(f"{len(rows):,} learners")


class AddStudentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add a Student")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setVerticalSpacing(12)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Student name")
        self.sex_combo = QComboBox()
        self.sex_combo.addItem("Female (F)", "F")
        self.sex_combo.addItem("Male (M)", "M")
        self.grade_input = QLineEdit()
        self.grade_input.setPlaceholderText("e.g. 8")
        self.section_input = QLineEdit()
        self.section_input.setPlaceholderText("e.g. Rafflesia")
        form.addRow("Name", self.name_input)
        form.addRow("Sex", self.sex_combo)
        form.addRow("Grade", self.grade_input)
        form.addRow("Section", self.section_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate_and_accept(self):
        if not all(
            field.text().strip()
            for field in (self.name_input, self.grade_input, self.section_input)
        ):
            QMessageBox.warning(
                self, "Missing information", "Enter a name, grade, and section."
            )
            return
        self.accept()
