from __future__ import annotations
from typing import List, Dict, Any
from .models import Snapshot, Features, MeetingHygiene, CommTriageAdvice, WellbeingAdvice, EfficiencyRecommendations, FatigueLoadAssessment
from .utils import to_dt, minutes
import numpy as np


def meeting_hygiene(s: Snapshot, f: Features) -> MeetingHygiene:
    issues, sugg = [], []
    if f.meet_ratio >= 0.5: issues.append("Высокая доля встреч")
    if f.back_to_back_count >= 2: issues.append("Back-to-back без буферов")
    long_meet = any(minutes(to_dt(x.end)-to_dt(x.start)) > 60 for x in s.schedule if x.type=="meeting")
    if long_meet: issues.append("Встречи >60 мин")
    if f.meet_ratio >= 0.5: sugg.append("Свести статусы; часть — в async апдейты")
    if f.back_to_back_count >= 2: sugg.append("Добавить 5–10 мин буфера между слотами")
    if long_meet: sugg.append("Резать встречи до 25–45 мин с повесткой")
    if not sugg: sugg.append("Гигиена встреч в норме")
    return MeetingHygiene(issues=issues, suggestions=sugg)


class HFClientProtocol:
    async def summarize(self, text: str, max_new_tokens: int = 120) -> str: ...
    async def generate_efficiency_recommendations(self, day_summary: str, features_summary: str, max_tokens: int = 300) -> str: ...
    async def assess_fatigue_load(self, day_summary: str, features_summary: str, max_tokens: int = 220) -> str: ...


async def comm_triage(s: Snapshot, f: Features, hf: HFClientProtocol) -> CommTriageAdvice:
    actions = []
    if s.comms:
        if s.comms.chat_msgs_count >= 120: actions.append("Читать чаты пакетно 2–3 раза/день по 15–20 мин")
        if s.comms.email_threads >= 15:   actions.append("Почта пакетно после фокус-блока (10–15 мин)")
        if s.comms.calls_minutes >= 90:   actions.append("Перевести часть созвонов в async")
        if not actions: actions = ["Коммуникационная нагрузка в пределах нормы"]
        summary_counts = f"Чаты:{s.comms.chat_msgs_count}, email threads:{s.comms.email_threads}, звонки:{s.comms.calls_minutes} мин"
    else:
        summary_counts = "Нет данных по коммуникациям"

    inbox_text = "\n".join(s.inbox_samples or [])[:4000]
    inbox_summary, inbox_priority = None, None
    if inbox_text:
        inbox_summary = await hf.summarize(inbox_text)
        inbox_priority = None  # классификация отключена; можно реализовать правила/фильтры вручную

    return CommTriageAdvice(summary=summary_counts, actions=actions, inbox_summary=inbox_summary, inbox_priority=inbox_priority)


def wellbeing(s: Snapshot, f: Features, risk) -> WellbeingAdvice:
    acts = []
    if (f.steps or 0) < 4000: acts.append("Челлендж: +3–5k шагов (прогулка 15–20 мин)")
    if (f.sleep_h or 0) < 7:  acts.append("Цель: сон ≥7 ч; подготовка ко сну за 45 мин до отбоя")
    if risk.risk_score >= 60: acts.append("Дыхание 4-7-8 2–3 раза/день и Pomodoro 55/5")
    if not acts: acts = ["Держи микропаузирование, воду и 15-мин winddown"]
    return WellbeingAdvice(actions=acts)


async def efficiency_analysis(s: Snapshot, f: Features, hf: HFClientProtocol) -> EfficiencyRecommendations:
    """
    Анализирует эффективность дня и генерирует рекомендации через модель.
    Сначала создает саммари дня, затем отправляет его в модель для генерации рекомендаций.
    """
    # Формируем саммари дня
    day_parts = []
    
    # Расписание
    if s.schedule:
        meetings = [x for x in s.schedule if x.type == "meeting"]
        focus_blocks = [x for x in s.schedule if x.type == "focus"]
        day_parts.append(f"Встреч: {len(meetings)}, фокус-блоков: {len(focus_blocks)}")
        if meetings:
            meeting_titles = [m.title for m in meetings[:5]]  # Первые 5
            day_parts.append(f"Встречи: {', '.join(meeting_titles)}")
    
    # Биометрия
    if s.biometrics:
        if s.biometrics.steps and s.biometrics.steps.get("total"):
            day_parts.append(f"Шаги: {s.biometrics.steps['total']}")
        if s.biometrics.sleep:
            sleep_h = s.biometrics.sleep.get("duration_hours")
            sleep_q = s.biometrics.sleep.get("quality", "неизвестно")
            if sleep_h:
                day_parts.append(f"Сон: {sleep_h:.1f}ч, качество: {sleep_q}")
    
    # Коммуникации
    if s.comms:
        day_parts.append(
            f"Коммуникации: {s.comms.chat_msgs_count} сообщений, "
            f"{s.comms.email_threads} email, {s.comms.calls_minutes} мин звонков"
        )
    
    # Задачи
    if s.tasks:
        total_switches = sum(t.context_switches or 0 for t in s.tasks)
        total_distractions = sum(t.distractions_minutes or 0 for t in s.tasks)
        if total_switches > 0 or total_distractions > 0:
            day_parts.append(f"Переключения контекста: {total_switches}, отвлечений: {total_distractions} мин")
    
    # Опросы
    if s.surveys:
        last_survey = s.surveys[-1]
        stress = last_survey.stress_1_10
        fatigue = last_survey.fatigue_1_10
        if stress is not None or fatigue is not None:
            parts_survey = []
            if stress is not None:
                parts_survey.append(f"стресс {stress}/10")
            if fatigue is not None:
                parts_survey.append(f"усталость {fatigue}/10")
            if parts_survey:
                day_parts.append(f"Самочувствие: {', '.join(parts_survey)}")
    
    day_summary = ". ".join(day_parts) if day_parts else "Минимальные данные о дне"
    
    
    features_parts = [
        f"Рабочее время: {f.work_minutes // 60}ч {f.work_minutes % 60}мин",
        f"Встречи: {f.meeting_minutes}мин ({f.meet_ratio * 100:.0f}% дня)",
        f"Фокус-время: {f.deepwork_minutes}мин",
        f"Перерывы: {f.break_minutes}мин",
    ]
    
    if f.back_to_back_count > 0:
        features_parts.append(f"Back-to-back встреч: {f.back_to_back_count}")
    
    if f.longest_stretch_no_break_min > 90:
        features_parts.append(f"Самый длинный период без перерыва: {f.longest_stretch_no_break_min}мин")
    
    if f.context_switches > 0:
        features_parts.append(f"Переключения контекста: {f.context_switches}")
    
    if f.distractions_minutes > 0:
        features_parts.append(f"Время отвлечений: {f.distractions_minutes}мин")
    
    features_summary = ". ".join(features_parts)

    recommendations = await hf.generate_efficiency_recommendations(day_summary, features_summary)
    
    if not recommendations:
        recommendations = (
            "Рекомендации недоступны (модель не ответила). "
            "Проверьте настройки API или попробуйте позже."
        )
    
    return EfficiencyRecommendations(
        recommendations=recommendations,
        day_summary=day_summary
    )


async def assess_fatigue_load_llm(s: Snapshot, f: Features, hf: HFClientProtocol) -> FatigueLoadAssessment:
    day_parts: List[str] = []
    if s.schedule:
        meetings = [x for x in s.schedule if x.type == "meeting"]
        focus_blocks = [x for x in s.schedule if x.type == "focus"]
        day_parts.append(f"Встреч: {len(meetings)}, фокус-блоков: {len(focus_blocks)}")
    if s.biometrics and s.biometrics.sleep:
        sleep_h = s.biometrics.sleep.get("duration_hours")
        if sleep_h:
            day_parts.append(f"Сон: {sleep_h:.1f}ч")
    if s.surveys:
        last = s.surveys[-1]
        vals = []
        if last.stress_1_10 is not None:
            vals.append(f"стресс {last.stress_1_10}/10")
        if last.fatigue_1_10 is not None:
            vals.append(f"усталость {last.fatigue_1_10}/10")
        if vals:
            day_parts.append("Самочувствие: " + ", ".join(vals))
    day_summary = ". ".join(day_parts) if day_parts else "Минимальные данные о дне"

    features_parts: List[str] = [
        f"Рабочее время: {f.work_minutes // 60}ч {f.work_minutes % 60}мин",
        f"Встречи: {f.meeting_minutes}мин ({f.meet_ratio * 100:.0f}% дня)",
        f"Фокус-время: {f.deepwork_minutes}мин",
        f"Перерывы: {f.break_minutes}мин",
        f"Переключения контекста: {f.context_switches}",
        f"Отвлечения: {f.distractions_minutes}мин",
    ]
    if f.steps is not None:
        features_parts.append(f"Шаги: {f.steps}")
    if f.sleep_h is not None:
        features_parts.append(f"Сон (оценка): {f.sleep_h:.1f}ч")
    features_summary = ". ".join(features_parts)

    raw = await hf.assess_fatigue_load(day_summary, features_summary)
    if not raw:
        return FatigueLoadAssessment(
            fatigue_score=0.0,
            load_score=0.0,
            level="low",
            explanation="Модель не ответила, оценка усталости недоступна."
        )

    import json
    try:
        data = json.loads(raw)
        fatigue = float(data.get("fatigue_score", 0.0))
        load = float(data.get("load_score", 0.0))
        level = data.get("level", "low")
        if level not in ("low", "medium", "high"):
            level = "low"
        explanation = str(data.get("explanation", "")).strip() or "Оценка от модели без подробного объяснения."
        return FatigueLoadAssessment(
            fatigue_score=fatigue,
            load_score=load,
            level=level,
            explanation=explanation
        )
    except Exception:
        return FatigueLoadAssessment(
            fatigue_score=0.0,
            load_score=0.0,
            level="low",
            explanation="Не удалось разобрать ответ модели, оценка усталости недоступна."
        )


