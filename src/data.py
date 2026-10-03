import re
from dataclasses import dataclass


@dataclass
class Dataset:
    category: str
    headers: list[str]
    rows: list[dict[str, str]]
    week_columns: list[str]


def week_number(column: str) -> int:
    match = re.search(r"\d+\s*$", column)
    return int(match.group()) if match else 999999


def category_columns(category: str, headers: list[str]) -> list[str]:
    if category == "Attendance":
        pattern = re.compile(r"Week\s+\d+", re.IGNORECASE)
    else:
        pattern = re.compile(rf"{re.escape(category)}\s*\d+", re.IGNORECASE)
    return sorted(
        (header for header in headers if pattern.fullmatch(header.strip())),
        key=week_number,
    )
