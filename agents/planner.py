from __future__ import annotations
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
from ics import Calendar, Event
from .models import Snapshot, Features, RiskResult, PlanItem
from .utils import to_dt, minutes, free_windows, slot_with_min_len, clamp


def propose_plan(s: Snapshot, f: Features, risk: RiskResult, energy: List[Dict[str, Any]]) -> List[PlanItem]:
    ws, we = to_dt(s.day.work_start), to_dt(s.day.work_end)
    busy = [(to_dt(x.start), to_dt(x.end)) for x in s.schedule if x.type != "break"]
    free = free_windows(ws, we, busy)
    micro_every = max(25, min(90, s.day.microbreak_minutes_every))
    micro_len = max(3, min(10, s.day.microbreak_len))
    plan: List[PlanItem] = []

    for s0, e0 in free:
        cursor = s0 + timedelta(minutes=micro_every)
        while cursor + timedelta(minutes=micro_len) <= e0:
            plan.append(PlanItem(start=cursor.isoformat(),
                                 end=(cursor+timedelta(minutes=micro_len)).isoformat(),
                                 kind="microbreak", title="Микропауза",
                                 reason=f"Каждые {micro_every} мин — {micro_len}-мин отдых"))
            cursor += timedelta(minutes=micro_every)

    def avg_energy(a: datetime, b: datetime) -> float:
        vals = [p["energy"] for p in energy if to_dt(p["ts"]) >= a and to_dt(p["ts"]) <= b]
        return float(np.mean(vals)) if vals else 0.0

    for s0, e0 in slot_with_min_len(free, 75)[:3]:
        if avg_energy(s0, e0) >= 0.65:
            dur = min(90, minutes(e0 - s0))
            plan.append(PlanItem(start=s0.isoformat(), end=(s0+timedelta(minutes=dur)).isoformat(),
                                 kind="focus", title="Фокус-блок",
                                 reason="Окно высокой энергии; уменьшаем фрагментацию"))

    if risk.risk_score >= 70:
        start_now = max(ws, datetime.utcnow())
        plan += [
            PlanItem(start=start_now.isoformat(), end=(start_now+timedelta(minutes=5)).isoformat(),
                     kind="breathing", title="Дыхательная практика 4-7-8",
                     reason="Высокий риск — снять напряжение"),
            PlanItem(start=(ws+timedelta(minutes=90)).isoformat(), end=(ws+timedelta(minutes=110)).isoformat(),
                     kind="no_notifications", title="Режим ‘Не беспокоить’ 20 мин",
                     reason="Снижение переключений контекста")
        ]
    elif risk.risk_score >= 40:
        plan.append(PlanItem(start=(ws+timedelta(minutes=120)).isoformat(), end=(ws+timedelta(minutes=135)).isoformat(),
                             kind="walk", title="Прогулка 15 мин",
                             reason="Средний риск — добавим активность"))

    plan.append(PlanItem(start=(ws+timedelta(minutes=30)).isoformat(), end=(ws+timedelta(minutes=35)).isoformat(),
                         kind="hydrate", title="Пауза на воду", reason="Профилактика усталости"))
    plan.append(PlanItem(start=(we-timedelta(minutes=20)).isoformat(), end=(we-timedelta(minutes=5)).isoformat(),
                         kind="winddown", title="Завершение дня", reason="Итоги, план на завтра"))

    if f.meet_ratio >= 0.6 or f.back_to_back_count >= 3:
        plan.append(PlanItem(start=ws.isoformat(), end=we.isoformat(),
                             kind="reschedule_hint", title="Сгруппировать/сократить встречи",
                             reason="Встречи >60% дня или много b2b"))
    return plan


def to_ics(items: List[PlanItem]) -> str:
    cal = Calendar()
    for it in items:
        if it.kind in {"microbreak","walk","breathing","focus","winddown","hydrate"}:
            e = Event(); e.name = it.title; e.begin = to_dt(it.start); e.end = to_dt(it.end); e.description = it.reason
            cal.events.add(e)
    return str(cal)


