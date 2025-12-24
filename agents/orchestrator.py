from __future__ import annotations
from typing import Dict, Any, List
from .models import Snapshot, Output
from .features import compute_features
from .risk import compute_risk
from .energy import energy_curve
from .planner import propose_plan, to_ics
from .analytics import meeting_hygiene, comm_triage, wellbeing, efficiency_analysis, assess_fatigue_load_llm
from .hf_client import HFClient
from .coach import LLMClient
from .rag import RAGAssistant


async def analyze_async(snapshot_dict: Dict[str, Any]) -> Output:
    snap = Snapshot(**snapshot_dict)
    f = compute_features(snap)
    risk = compute_risk(f, snap.rec_history)
    energy = energy_curve(snap, f)
    plan = propose_plan(snap, f, risk, energy)
    hygiene = meeting_hygiene(snap, f)
    hf = HFClient()
    triage = await comm_triage(snap, f, hf)
    wb = wellbeing(snap, f, risk)
    efficiency = await efficiency_analysis(snap, f, hf)
    fatigue_load = await assess_fatigue_load_llm(snap, f, hf)
    rag = RAGAssistant()
    rag_advice = rag.build_advice(snap, f, risk)
    ics = to_ics(plan)
    coach = await LLMClient().coach(risk, f)
    return Output(risk=risk, energy_curve=energy, plan=plan, meeting_hygiene=hygiene,
                  comm_triage=triage, wellbeing=wb, efficiency_recommendations=efficiency,
                  ics_calendar=ics, coach_message=coach, rag_advice=rag_advice, fatigue_load=fatigue_load)


def analyze(snapshot_dict: Dict[str, Any]) -> Dict[str, Any]:
    import asyncio
    return asyncio.run(analyze_async(snapshot_dict)).model_dump()


async def analyze_text_async(text: str, user_id: str = "user", tz: str | None = None) -> Output:
    from datetime import datetime
    from .models import WorkDay

    today = datetime.utcnow().date().isoformat()
    day = WorkDay(
        work_start=f"{today}T09:00:00",
        work_end=f"{today}T18:00:00",
    )
    snapshot = Snapshot(
        user_id=user_id,
        date=today,
        tz=tz,
        day=day,
        schedule=[],
        biometrics=None,
        surveys=[],
        tasks=[],
        comms=None,
        rec_history=None,
        persona=None,
        inbox_samples=[text],
    )
    return await analyze_async(snapshot.model_dump())


def analyze_text(text: str, user_id: str = "user", tz: str | None = None) -> Dict[str, Any]:
    import asyncio
    return asyncio.run(analyze_text_async(text, user_id=user_id, tz=tz)).model_dump()

def analyze_batch(snapshots: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """
    Анализ массива снапшотов. Возвращает список результатов в том же порядке.
    """
    import asyncio
    async def _run_all():
        outs = []
        for s in snapshots:
            outs.append(await analyze_async(s))
        return outs
    return [o.model_dump() for o in asyncio.run(_run_all())]

def analyze_from_file(path: str):
    """
    Загружает JSON из файла и:
    - если это объект (dict) — анализирует как один снапшот
    - если это массив (list) — анализирует как батч снапшотов
    - если это объект с ключом 'snapshots' (list) — анализирует батч
    """
    import json, os
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return analyze_batch(data)
    if isinstance(data, dict) and "snapshots" in data and isinstance(data["snapshots"], list):
        return analyze_batch(data["snapshots"])
    if isinstance(data, dict):
        return analyze(data)
    raise ValueError("Неподдерживаемый формат JSON: ожидался объект или массив")


