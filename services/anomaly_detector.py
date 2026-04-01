"""
Detects anomalous entries by comparing against 7-day average.
Threshold is configurable via config.ANOMALY_THRESHOLD (default 30%).
"""
from __future__ import annotations

from config import ANOMALY_THRESHOLD
from services.google_api import GoogleSheetsService


class AnomalyDetector:
    def __init__(self, sheets: GoogleSheetsService) -> None:
        self._sheets = sheets

    async def check(
        self, funnel_type: str, field: str, value: float
    ) -> tuple[bool, float, float]:
        """
        Returns (is_anomaly, avg_7d, deviation_pct).
        """
        history = await self._sheets.get_last_7_days(funnel_type, field)
        if len(history) < 3:
            # Not enough history to judge
            return False, 0.0, 0.0

        avg = sum(history) / len(history)
        if avg == 0:
            return False, 0.0, 0.0

        deviation = abs(value - avg) / avg
        return deviation > ANOMALY_THRESHOLD, round(avg, 2), round(deviation * 100, 1)
