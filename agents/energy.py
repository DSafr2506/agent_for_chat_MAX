from __future__ import annotations
from typing import List, Dict, Any
from datetime import timedelta
import numpy as np
from .models import Snapshot, Features
from .utils import to_dt, clamp, minutes
from datetime import datetime


def energy_curve(s: Snapshot, f: Features, step_min: int = 30) -> List[Dict[str, Any]]:
    ws, we = to_dt(s.day.work_start), to_dt(s.day.work_end)
    total = minutes(we - ws)
    n = max(1, total // step_min)

    def chrono_base(hour: float, typ: str) -> float:
        if typ == "lark":   val = -0.04*(hour-10)**2 + 1.0
        elif typ == "owl":  val = -0.04*(hour-17)**2 + 1.0
        else:               val = -0.04*(hour-14)**2 + 1.0
        return clamp(0.4 + 0.6*val, 0.4, 1.0)

    chrono = s.persona.chronotype if s.persona else "neutral"
    sleep_penalty = 0.0 if f.sleep_h is None else clamp((7.5 - f.sleep_h)/3.0, 0, 0.35)

    points = []
    for i in range(n+1):
        t = ws + timedelta(minutes=i*step_min)
        base = chrono_base(t.hour + t.minute/60, chrono)
        if 13.5 <= (t.hour + t.minute/60) <= 15.5: base -= 0.12
        base -= sleep_penalty
        points.append({"ts": t.isoformat(), "energy": round(clamp(base, 0.2, 1.0), 3)})
    return points


