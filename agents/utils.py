from __future__ import annotations
from typing import List, Tuple
from datetime import datetime, timedelta
from dateutil import parser as dtp


def to_dt(x: str) -> datetime:
    return dtp.isoparse(x)


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def minutes(td: timedelta) -> int:
    return int(td.total_seconds() // 60)


def free_windows(work_start: datetime, work_end: datetime, busy: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    cur = work_start
    out = []
    for s, e in sorted(busy, key=lambda z: z[0]):
        if s > cur:
            out.append((cur, s))
        cur = max(cur, e)
    if cur < work_end:
        out.append((cur, work_end))
    return out


def slot_with_min_len(windows: List[Tuple[datetime, datetime]], min_minutes: int) -> List[Tuple[datetime, datetime]]:
    return [(s, e) for s, e in windows if minutes(e - s) >= min_minutes]


