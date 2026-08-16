from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo("America/Chicago")
UTC = timezone.utc


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        local = value.replace(tzinfo=CHICAGO)
        return local.astimezone(UTC)
    return value.astimezone(UTC)


class Book:
    def __init__(self) -> None:
        self._slots: list[tuple[datetime, datetime]] = []

    def add(self, start: datetime, end: datetime) -> int:
        utc_start, utc_end = to_utc(start), to_utc(end)
        if utc_end <= utc_start:
            raise ValueError("empty interval")
        if self.conflicts(start, end):
            raise ValueError("overlap")
        self._slots.append((utc_start, utc_end))
        return len(self._slots) - 1

    def add_weekly(self, start: datetime, end: datetime, count: int) -> list[int]:
        ids: list[int] = []
        for index in range(count):
            delta = timedelta(days=7 * index)
            occ_start = start + delta
            occ_end = end + delta
            if occ_start.tzinfo is None:
                try:
                    occ_start.replace(tzinfo=CHICAGO)
                except Exception:
                    continue
                # Missing DST hour: fold/gap. zoneinfo raises? On gap, astimezone still works
                # but we must skip times that do not exist locally.
                if not _exists_locally(occ_start):
                    continue
            ids.append(self.add(occ_start, occ_end))
        return ids

    def conflicts(self, start: datetime, end: datetime) -> bool:
        utc_start, utc_end = to_utc(start), to_utc(end)
        for other_start, other_end in self._slots:
            if utc_start < other_end and utc_end > other_start:
                return True
        return False

    def slots(self) -> list[tuple[datetime, datetime]]:
        return list(self._slots)


def _exists_locally(naive: datetime) -> bool:
    local = naive.replace(tzinfo=CHICAGO)
    back = local.astimezone(UTC).astimezone(CHICAGO)
    return back.replace(tzinfo=None) == naive
