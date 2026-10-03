import math
import sqlite3
from statistics import median

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGridLayout, QLabel, QTabWidget, QVBoxLayout, QWidget

from ..analytics import CategorySummary, summarize
from ..constants import CATEGORIES
from ..storage import SQLiteRepository


class SummaryCharts(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.summary: CategorySummary | None = None
        self.dark = False
        self.setMinimumHeight(300)

    def set_summary(self, summary: CategorySummary, dark: bool):
        self.summary = summary
        self.dark = dark
        self.update()

    def paintEvent(self, event):
        if not self.summary:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = QColor("#172321" if self.dark else "#fbfcfa")
        foreground = QColor("#ecf3ef" if self.dark else "#24332f")
        muted = QColor("#a4b5ae" if self.dark else "#687972")
        grid = QColor("#354742" if self.dark else "#dce5e0")
        primary = QColor("#71c4a1" if self.dark else "#3d8a70")
        secondary = QColor("#e49a84" if self.dark else "#d87861")
        painter.fillRect(self.rect(), background)

        gap = 24
        panel_width = max(1, (self.width() - gap - 32) / 2)
        left = QRectF(16, 8, panel_width, self.height() - 16)
        right = QRectF(left.right() + gap, 8, panel_width, self.height() - 16)
        if self.summary.category == "Attendance":
            self.draw_attendance(
                painter, left, right, foreground, muted, grid, primary, secondary
            )
        else:
            self.draw_scores(
                painter, left, right, foreground, muted, grid, primary, secondary
            )
        painter.end()

    def draw_frame(
        self, painter, bounds, title, maximum, foreground, muted, grid, suffix=""
    ):
        painter.setPen(foreground)
        painter.drawText(QRectF(bounds.x(), bounds.y(), bounds.width(), 24), title)
        plot = QRectF(
            bounds.x() + 42, bounds.y() + 38, bounds.width() - 50, bounds.height() - 82
        )
        painter.setFont(self.font())
        for tick in range(5):
            ratio = tick / 4
            y = plot.bottom() - ratio * plot.height()
            painter.setPen(QPen(grid, 1))
            painter.drawLine(plot.left(), y, plot.right(), y)
            painter.setPen(muted)
            value = maximum * ratio
            label = (
                f"{value:.0f}{suffix}"
                if suffix
                else f"{value:.1f}".rstrip("0").rstrip(".")
            )
            painter.drawText(
                QRectF(bounds.x(), y - 9, 36, 18), Qt.AlignmentFlag.AlignRight, label
            )
        painter.setPen(QPen(grid, 1))
        painter.drawLine(plot.left(), plot.top(), plot.left(), plot.bottom())
        painter.drawLine(plot.left(), plot.bottom(), plot.right(), plot.bottom())
        return plot

    def draw_x_labels(self, painter, plot, labels, muted):
        count = len(labels)
        if not count:
            return
        slot = plot.width() / count
        painter.setPen(muted)
        for index, label in enumerate(labels):
            painter.drawText(
                QRectF(plot.left() + index * slot, plot.bottom() + 7, slot, 28),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label,
            )

    def draw_attendance(
        self, painter, left, right, foreground, muted, grid, present_color, absent_color
    ):
        weeks = self.summary.weeks
        labels = [week.label.replace("Week ", "W") for week in weeks]
        maximum = max(1, max((week.present + week.absent for week in weeks), default=0))
        maximum = math.ceil(maximum / 4) * 4
        plot = self.draw_frame(
            painter, left, "Attendance by week", maximum, foreground, muted, grid
        )
        slot = plot.width() / max(1, len(weeks))
        bar_width = min(34, slot * 0.58)
        for index, week in enumerate(weeks):
            x = plot.left() + index * slot + (slot - bar_width) / 2
            present_height = week.present / maximum * plot.height()
            absent_height = week.absent / maximum * plot.height()
            painter.fillRect(
                QRectF(x, plot.bottom() - present_height, bar_width, present_height),
                present_color,
            )
            painter.fillRect(
                QRectF(
                    x,
                    plot.bottom() - present_height - absent_height,
                    bar_width,
                    absent_height,
                ),
                absent_color,
            )
        self.draw_x_labels(painter, plot, labels, muted)

        rate_plot = self.draw_frame(
            painter, right, "Attendance rate", 100, foreground, muted, grid, "%"
        )
        rate_slot = rate_plot.width() / max(1, len(weeks))
        points = []
        for index, week in enumerate(weeks):
            rate = week.present / week.count * 100 if week.count else 0
            points.append(
                (
                    rate_plot.left() + (index + 0.5) * rate_slot,
                    rate_plot.bottom() - rate / 100 * rate_plot.height(),
                )
            )
        painter.setPen(QPen(present_color, 2.2))
        for start, end in zip(points, points[1:]):
            painter.drawLine(*start, *end)
        painter.setBrush(present_color)
        for x, y in points:
            painter.drawEllipse(QRectF(x - 3, y - 3, 6, 6))
        self.draw_x_labels(painter, rate_plot, labels, muted)

    def draw_scores(
        self, painter, left, right, foreground, muted, grid, line_color, spread_color
    ):
        weeks = self.summary.weeks
        labels = [week.label.replace("Week ", "W") for week in weeks]
        maximum = max(
            1.0,
            max((week.average + week.deviation for week in weeks), default=0) * 1.15,
        )
        plot = self.draw_frame(
            painter, left, "Weekly mean and spread", maximum, foreground, muted, grid
        )
        slot = plot.width() / max(1, len(weeks))
        points = []
        painter.setPen(QPen(spread_color, 1.5))
        for index, week in enumerate(weeks):
            x = plot.left() + (index + 0.5) * slot
            high = (
                plot.bottom()
                - min(maximum, week.average + week.deviation) / maximum * plot.height()
            )
            low = (
                plot.bottom()
                - max(0, week.average - week.deviation) / maximum * plot.height()
            )
            painter.drawLine(x, high, x, low)
            painter.drawLine(x - 4, high, x + 4, high)
            painter.drawLine(x - 4, low, x + 4, low)
            points.append((x, plot.bottom() - week.average / maximum * plot.height()))
        painter.setPen(QPen(line_color, 2.2))
        for start, end in zip(points, points[1:]):
            painter.drawLine(*start, *end)
        painter.setBrush(line_color)
        for x, y in points:
            painter.drawEllipse(QRectF(x - 3, y - 3, 6, 6))
        self.draw_x_labels(painter, plot, labels, muted)

        box_plot = self.draw_frame(
            painter, right, "Score distribution", maximum, foreground, muted, grid
        )
        box_slot = box_plot.width() / max(1, len(weeks))
        for index, week in enumerate(weeks):
            values = sorted(week.values)
            if not values:
                continue
            middle = len(values) // 2
            lower_half = values[:middle]
            upper_half = values[middle + (len(values) % 2) :]
            lower_quartile = median(lower_half) if lower_half else values[0]
            upper_quartile = median(upper_half) if upper_half else values[-1]
            x = box_plot.left() + (index + 0.5) * box_slot

            def y_for(value):
                return box_plot.bottom() - value / maximum * box_plot.height()

            painter.setPen(QPen(muted, 1.4))
            painter.drawLine(x, y_for(values[0]), x, y_for(values[-1]))
            painter.drawLine(x - 5, y_for(values[0]), x + 5, y_for(values[0]))
            painter.drawLine(x - 5, y_for(values[-1]), x + 5, y_for(values[-1]))
            top = y_for(upper_quartile)
            bottom = y_for(lower_quartile)
            painter.fillRect(QRectF(x - 8, top, 16, max(2, bottom - top)), spread_color)
            painter.setPen(QPen(line_color, 2))
            painter.drawLine(x - 8, y_for(median(values)), x + 8, y_for(median(values)))
        self.draw_x_labels(painter, box_plot, labels, muted)


class CategorySummaryPanel(QWidget):
    def __init__(self, category, repository: SQLiteRepository, parent=None):
        super().__init__(parent)
        self.category = category
        self.repository = repository
        self.dark = None
        self.is_loaded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(14)

        self.metrics = []
        metric_layout = QGridLayout()
        metric_layout.setHorizontalSpacing(12)
        metric_layout.setVerticalSpacing(10)
        for index in range(4):
            value = QLabel("--")
            value.setObjectName("metricValue")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label = QLabel()
            label.setObjectName("muted")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            metric_layout.addWidget(value, 0, index)
            metric_layout.addWidget(label, 1, index)
            self.metrics.append((value, label))
        layout.addLayout(metric_layout)

        self.status = QLabel()
        self.status.setObjectName("muted")
        layout.addWidget(self.status)

        self.charts = SummaryCharts(self)
        layout.addWidget(self.charts, 1)

    def refresh(self, dark):
        try:
            dataset = self.repository.load(self.category)
        except (OSError, ValueError, sqlite3.Error) as error:
            self.status.setText(str(error))
            for value, label in self.metrics:
                value.setText("--")
                label.setText("")
            return

        summary = summarize(dataset)
        self.is_loaded = True
        self.status.setText(
            f"Local database  |  {summary.learner_count} learners  |  "
            f"{len(dataset.week_columns)} reporting periods"
        )
        self.update_metrics(summary)
        self.charts.set_summary(summary, dark)

    def update_metrics(self, summary: CategorySummary):
        if summary.category == "Attendance":
            values = (
                str(summary.learner_count),
                f"{summary.attendance_rate:.1f}%",
                str(sum(week.present for week in summary.weeks)),
                str(sum(week.absent for week in summary.weeks)),
            )
            labels = (
                "Learners",
                "Overall attendance",
                "Present records",
                "Absent records",
            )
        else:
            values = (
                str(summary.learner_count),
                f"{summary.average:.2f}" if summary.values else "--",
                f"{summary.median:.2f}" if summary.values else "--",
                f"{summary.deviation:.2f}" if summary.values else "--",
            )
            labels = ("Learners", "Mean score", "Median score", "Score deviation")
        for (value_label, caption), value, label in zip(self.metrics, values, labels):
            value_label.setText(value)
            caption.setText(label)


class SummaryView(QWidget):
    def __init__(self, repository: SQLiteRepository, parent=None):
        super().__init__(parent)
        self.dark = False
        self.panels = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        for category in CATEGORIES:
            panel = CategorySummaryPanel(category, repository)
            self.panels[category] = panel
            self.tabs.addTab(panel, category)
        self.tabs.currentChanged.connect(self.refresh_current)
        layout.addWidget(self.tabs)

    def refresh(self, dark):
        self.dark = dark
        self.refresh_current(force=True)

    def refresh_current(self, _index=None, force=False):
        category = CATEGORIES[self.tabs.currentIndex()]
        panel = self.panels[category]
        if force or not panel.is_loaded or panel.dark != self.dark:
            panel.dark = self.dark
            panel.refresh(self.dark)

    def invalidate(self):
        for panel in self.panels.values():
            panel.is_loaded = False
