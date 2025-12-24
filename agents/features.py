from __future__ import annotations
from typing import List, Tuple, Any
from .models import Snapshot, Features
from .utils import to_dt, minutes, clamp
import numpy as np


def compute_features(s: Snapshot) -> Features:
    ws, we = to_dt(s.day.work_start), to_dt(s.day.work_end)
    work_minutes = minutes(we - ws)

    meetings = [(to_dt(it.start), to_dt(it.end)) for it in s.schedule if it.type == "meeting"]
    meetings.sort()
    back_to_back = sum(1 for i in range(1, len(meetings)) if minutes(meetings[i][0] - meetings[i-1][1]) < 5)

    meeting_minutes = sum(minutes(e - st) for st, e in meetings)
    meetings_count = len(meetings)
    deepwork_minutes = sum(minutes(to_dt(it.end) - to_dt(it.start)) for it in s.schedule if it.type == "focus")
    break_minutes = sum(minutes(to_dt(it.end) - to_dt(it.start)) for it in s.schedule if it.type == "break")

    longest_stretch = 0
    last_break_end = ws
    for it in sorted([it for it in s.schedule if it.type == "break"], key=lambda x: to_dt(x.start)):
        st, en = to_dt(it.start), to_dt(it.end)
        longest_stretch = max(longest_stretch, minutes(st - last_break_end))
        last_break_end = en
    longest_stretch = max(longest_stretch, minutes(we - last_break_end))

    context_switches = sum(t.context_switches or 0 for t in s.tasks)
    distractions_minutes = sum(t.distractions_minutes or 0 for t in s.tasks)

    steps_total = s.biometrics.steps.get("total") if (s.biometrics and s.biometrics.steps) else None
    sleep_h = s.biometrics.sleep.get("duration_hours") if (s.biometrics and s.biometrics.sleep) else None
    sleep_q_map = {"poor":0.25,"ok":0.5,"good":0.75,"great":1.0}
    sleep_quality_score = sleep_q_map.get(s.biometrics.sleep.get("quality"), None) if (s.biometrics and s.biometrics.sleep) else None
    avg_hr = s.biometrics.heart.get("avg_bpm") if (s.biometrics and s.biometrics.heart) else None
    hrv_ms = s.biometrics.heart.get("hrv_ms") if (s.biometrics and s.biometrics.heart) else None

    if s.surveys:
        def mean_or_none(vals):
            vals = [v for v in vals if v is not None]
            return float(np.nanmean(vals)) if vals else None
        stress_self = mean_or_none([x.stress_1_10 for x in s.surveys])
        fatigue_self = mean_or_none([x.fatigue_1_10 for x in s.surveys])
        satisfaction_self = mean_or_none([x.satisfaction_1_10 for x in s.surveys])
        burnout_self = mean_or_none([x.burnout_1_10 for x in s.surveys])
    else:
        stress_self = fatigue_self = satisfaction_self = burnout_self = None

    calls_minutes = s.comms.calls_minutes if s.comms else 0
    chats_count = s.comms.chat_msgs_count if s.comms else 0
    meet_ratio = meeting_minutes / max(1, work_minutes)

    return Features(
        work_minutes=work_minutes, meeting_minutes=meeting_minutes, meetings_count=meetings_count,
        deepwork_minutes=deepwork_minutes, break_minutes=break_minutes, back_to_back_count=back_to_back,
        longest_stretch_no_break_min=longest_stretch, context_switches=context_switches,
        distractions_minutes=distractions_minutes, steps=steps_total, sleep_h=sleep_h,
        sleep_quality_score=sleep_quality_score, avg_hr=avg_hr, hrv_ms=hrv_ms,
        stress_self=stress_self, fatigue_self=fatigue_self, satisfaction_self=satisfaction_self, burnout_self=burnout_self,
        calls_minutes=calls_minutes, chats_count=chats_count, meet_ratio=meet_ratio
    )


