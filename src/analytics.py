from dataclasses import dataclass
from statistics import mean, median, pstdev

from .data import Dataset, week_number


@dataclass
class WeekStatistics:
    label: str
    count: int
    average: float
    median: float
    deviation: float
    values: list[float]
    present: int = 0
    absent: int = 0


@dataclass
class CategorySummary:
    category: str
    weeks: list[WeekStatistics]
    values: list[float]
    learner_count: int

    @property
    def average(self) -> float:
        return mean(self.values) if self.values else 0.0

    @property
    def median(self) -> float:
        return median(self.values) if self.values else 0.0

    @property
    def deviation(self) -> float:
        return pstdev(self.values) if len(self.values) > 1 else 0.0

    @property
    def attendance_rate(self) -> float:
        if self.category != "Attendance" or not self.values:
            return 0.0
        return mean(self.values) * 100


def summarize(dataset: Dataset) -> CategorySummary:
    weeks: list[WeekStatistics] = []
    all_values: list[float] = []
    learner_count = sum(bool(row.get("Learners", "").strip()) for row in dataset.rows)

    for column in dataset.week_columns:
        values: list[float] = []
        present = 0
        absent = 0
        for row in dataset.rows:
            raw_value = (row.get(column) or "").strip()
            if not raw_value:
                continue
            try:
                value = float(raw_value)
            except ValueError:
                continue
            values.append(value)
            if dataset.category == "Attendance":
                if value == 1:
                    present += 1
                else:
                    absent += 1

        weeks.append(
            WeekStatistics(
                label=f"Week {week_number(column)}",
                count=len(values),
                average=mean(values) if values else 0.0,
                median=median(values) if values else 0.0,
                deviation=pstdev(values) if len(values) > 1 else 0.0,
                values=values,
                present=present,
                absent=absent,
            )
        )
        all_values.extend(values)

    return CategorySummary(dataset.category, weeks, all_values, learner_count)
