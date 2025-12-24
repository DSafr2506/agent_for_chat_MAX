from __future__ import annotations
from typing import List, Optional, Literal, Dict, Tuple, Any
from pydantic import BaseModel, field_validator
from .utils import to_dt


class ScheduleItem(BaseModel):
    id: Optional[str] = None
    title: str
    start: str
    end: str
    type: Literal["meeting","focus","break","personal","deadline","other"] = "other"
    importance: Optional[Literal["low","medium","high"]] = "medium"
    source: Optional[str] = None

    @field_validator("start","end")
    @classmethod
    def _iso(cls, v: str) -> str:
        _ = to_dt(v); return v


class WorkDay(BaseModel):
    work_start: str
    work_end: str
    lunch_start: Optional[str] = None
    lunch_end: Optional[str] = None
    microbreak_minutes_every: int = 55
    microbreak_len: int = 5
    day_type: Literal["workday","vacation","sick","weekend"] = "workday"


class Biometrics(BaseModel):
    steps: Optional[Dict[str, Any]] = None
    activity_minutes: Optional[int] = None
    sleep: Optional[Dict[str, Any]] = None
    heart: Optional[Dict[str, Any]] = None


class SurveyEntry(BaseModel):
    ts: str
    stress_1_10: Optional[int] = None
    mood_1_10: Optional[int] = None
    fatigue_1_10: Optional[int] = None
    satisfaction_1_10: Optional[int] = None
    burnout_1_10: Optional[int] = None
    source: Optional[str] = None


class TaskBlock(BaseModel):
    start: str
    end: str
    kind: Literal["focus","routine","creative","comms"]
    context_switches: Optional[int] = 0
    distractions_minutes: Optional[int] = 0
    source: Optional[str] = None


class Comms(BaseModel):
    calls_count: int = 0
    calls_minutes: int = 0
    meetings_count: int = 0
    chat_msgs_count: int = 0
    email_threads: int = 0
    source: Optional[str] = None


class RecHistory(BaseModel):
    accepted: int = 0
    ignored: int = 0
    snoozed: int = 0
    events: Optional[List[Dict[str, Any]]] = None


class Persona(BaseModel):
    chronotype: Optional[Literal["lark","owl","neutral"]] = "neutral"
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    hard_constraints: List[str] = []


class Snapshot(BaseModel):
    schema_version: str = "1.0"
    user_id: str
    date: str
    tz: Optional[str] = None
    day: WorkDay
    schedule: List[ScheduleItem] = []
    biometrics: Optional[Biometrics] = None
    surveys: List[SurveyEntry] = []
    tasks: List[TaskBlock] = []
    comms: Optional[Comms] = None
    rec_history: Optional[RecHistory] = None
    persona: Optional[Persona] = None
    inbox_samples: Optional[List[str]] = None


class Features(BaseModel):
    work_minutes: int
    meeting_minutes: int
    meetings_count: int
    deepwork_minutes: int
    break_minutes: int
    back_to_back_count: int
    longest_stretch_no_break_min: int
    context_switches: int
    distractions_minutes: int
    steps: Optional[int] = None
    sleep_h: Optional[float] = None
    sleep_quality_score: Optional[float] = None
    avg_hr: Optional[int] = None
    hrv_ms: Optional[int] = None
    stress_self: Optional[float] = None
    fatigue_self: Optional[float] = None
    satisfaction_self: Optional[float] = None
    burnout_self: Optional[float] = None
    calls_minutes: int = 0
    chats_count: int = 0
    meet_ratio: float


class RiskResult(BaseModel):
    risk_score: float
    factors: Dict[str, float]
    notes: List[str]


class PlanItem(BaseModel):
    start: str
    end: str
    kind: Literal["microbreak","walk","breathing","focus","reschedule_hint","winddown","hydrate","no_notifications"]
    title: str
    reason: str


class MeetingHygiene(BaseModel):
    issues: List[str]
    suggestions: List[str]


class CommTriageAdvice(BaseModel):
    summary: str
    actions: List[str]
    inbox_summary: Optional[str] = None
    inbox_priority: Optional[Dict[str, float]] = None


class WellbeingAdvice(BaseModel):
    actions: List[str]


class EfficiencyRecommendations(BaseModel):
    recommendations: str
    day_summary: Optional[str] = None


class RAGAdvice(BaseModel):
    suggestions: List[str]
    sources: Optional[List[str]] = None


class FatigueLoadAssessment(BaseModel):
    fatigue_score: float
    load_score: float
    level: Literal["low", "medium", "high"]
    explanation: str


class Output(BaseModel):
    risk: RiskResult
    energy_curve: List[Dict[str, Any]]
    plan: List[PlanItem]
    meeting_hygiene: MeetingHygiene
    comm_triage: CommTriageAdvice
    wellbeing: WellbeingAdvice
    ics_calendar: str
    coach_message: str
    efficiency_recommendations: EfficiencyRecommendations
    rag_advice: Optional[RAGAdvice] = None
    fatigue_load: Optional[FatigueLoadAssessment] = None


