"""DTOs (Data Transfer Objects) for the application."""
from dataclasses import dataclass


@dataclass
class MetricHistoryRecord:
    """Data Class to represent a Metric History Record."""
    date: str
    name: str
    value: float
    info: str

    def __str__(self):
        return f"""
Name:\t{self.name}
Date:\t{self.date}
Value:\t{self.value}
Info:\t{self.info}
"""  # pylint: disable=line-too-long
