from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, workbook_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(18)

        workbook_group = QGroupBox("Excel export")
        workbook_form = QFormLayout(workbook_group)
        workbook_form.setContentsMargins(16, 24, 16, 16)
        workbook_form.setHorizontalSpacing(14)
        workbook_form.setVerticalSpacing(14)
        self.workbook_field = QLineEdit(str(workbook_path))
        self.workbook_field.setClearButtonEnabled(True)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_workbook)
        workbook_form.addRow("Output workbook", self.workbook_field)
        workbook_form.addRow("", browse)
        note = QLabel("The workbook is generated from the local database on sync.")
        note.setObjectName("muted")
        workbook_form.addRow("", note)
        layout.addWidget(workbook_group)

        self.notification = QLabel()
        self.notification.setObjectName("notification")
        self.notification.setWordWrap(True)
        self.notification.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.notification)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse_workbook(self):
        current = Path(self.workbook_field.text()).expanduser()
        start = str(current if current.is_dir() else current.parent)
        selected, _ = QFileDialog.getSaveFileName(
            self, "Choose Excel export", str(current), "Excel workbook (*.xlsx)"
        )
        if selected:
            self.workbook_field.setText(selected)

    def workbook_path(self) -> Path:
        workbook_path = Path(self.workbook_field.text()).expanduser()
        if workbook_path.suffix.lower() != ".xlsx":
            workbook_path = workbook_path.with_suffix(".xlsx")
        return workbook_path

    def validate_and_accept(self):
        if not self.workbook_field.text().strip():
            self.notification.setText("Choose a location for the Excel export.")
            return
        self.notification.clear()
        self.accept()
