from __future__ import annotations
from typing import Optional, Dict, List
from .models import Features, RecHistory, RiskResult
from .utils import clamp


def compute_risk(f: Features, rec: Optional[RecHistory]) -> RiskResult:
    w, notes = {}, []

    if f.sleep_h is not None:
        debt = max(0.0, 7.5 - f.sleep_h)
        w["sleep_debt"] = clamp(debt/4.0, 0, 1)
        if debt >= 1.5: notes.append(f"Недосып {debt:.1f}ч.")
    else:
        w["sleep_debt"] = 0.3; notes.append("Нет данных о сне")

    if f.steps is not None:
        w["low_activity"] = 1.0 if f.steps < 3000 else (0.4 if f.steps < 8000 else 0.1)
        if f.steps < 3000: notes.append("Низкая активность (<3k шагов)")
    else:
        w["low_activity"] = 0.2; notes.append("Нет данных о шагах")

    over_h = max(0, f.work_minutes - 9*60)/60
    w["overtime"] = clamp(over_h/3.0, 0, 1)
    if over_h >= 1.0: notes.append(f"Овертайм {over_h:.1f}ч.")

    w["long_stretch"] = clamp((f.longest_stretch_no_break_min - 90)/90, 0, 1)
    if f.longest_stretch_no_break_min >= 120: notes.append(f"Без перерыва {f.longest_stretch_no_break_min} мин.")

    w["meeting_load"] = clamp((f.meet_ratio - 0.3)/0.3, 0, 1)
    if f.meet_ratio >= 0.5: notes.append("Доля встреч высокая")
    w["back_to_back"] = clamp(f.back_to_back_count/4, 0, 1)
    if f.back_to_back_count >= 3: notes.append("Много back-to-back")

    w["context_switches"] = clamp(f.context_switches/20, 0, 1)
    if f.context_switches >= 15: notes.append("Частые переключения")
    w["distractions"] = clamp(f.distractions_minutes/60, 0, 1)
    if f.distractions_minutes >= 30: notes.append("Отвлечений >30 мин")

    if f.stress_self is not None:  w["stress_self"] = clamp((f.stress_self-5)/5, 0, 1)
    if f.fatigue_self is not None: w["fatigue_self"] = clamp((f.fatigue_self-5)/5, 0, 1)
    if f.burnout_self is not None: w["burnout_self"] = clamp((f.burnout_self-5)/5, 0, 1)

    if f.avg_hr is not None and f.avg_hr >= 90: w["elevated_hr"] = 1.0; notes.append("Повышенный средний пульс")
    if f.hrv_ms is not None and f.hrv_ms <= 35: w["low_hrv"] = 1.0

    if rec:
        total = rec.accepted + rec.ignored + rec.snoozed
        acc_rate = (rec.accepted/total) if total else 0.0
        w["low_adherence"] = clamp((0.6 - acc_rate)/0.6, 0, 1)

    weights = {
        "sleep_debt": 16, "low_activity": 8, "overtime": 12, "long_stretch": 10,
        "meeting_load": 10, "back_to_back": 6, "context_switches": 8, "distractions": 6,
        "stress_self": 8, "fatigue_self": 6, "burnout_self": 10,
        "elevated_hr": 6, "low_hrv": 4, "low_adherence": 4
    }
    score = sum(weights.get(k,0)*v for k, v in w.items())
    max_score = sum(weights.values()) if w else 1
    risk = clamp(100.0*score/max_score, 0, 100)
    return RiskResult(risk_score=round(risk,1), factors=w, notes=notes)


