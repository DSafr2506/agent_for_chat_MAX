from __future__ import annotations
from typing import List, Tuple, Dict, Any
import os
from dataclasses import dataclass
from collections import Counter

from .models import Snapshot, Features, RiskResult, RAGAdvice
from .hf_client import HFClient


def _tokenize(text: str) -> List[str]:
    return [t.strip(".,!?:;()[]«»\"'").lower() for t in text.split() if t.strip()]


def _cosine_sim(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    num = sum(a[t] * b[t] for t in common)
    if num == 0:
        return 0.0
    sa = sum(v * v for v in a.values()) ** 0.5
    sb = sum(v * v for v in b.values()) ** 0.5
    if sa == 0 or sb == 0:
        return 0.0
    return num / (sa * sb)


@dataclass
class _DocChunk:
    text: str
    tokens: Counter
    source: str


class RAGAssistant:
    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = base_dir or os.path.dirname(__file__)
        self.chunks: List[_DocChunk] = []
        self._load_corpus()

    def _load_corpus(self) -> None:
        kb_dir = os.path.join(self.base_dir, "knowledge")
        paths: List[Tuple[str, str]] = []
        if os.path.isdir(kb_dir):
            for name in os.listdir(kb_dir):
                if name.endswith(".md") or name.endswith(".txt"):
                    paths.append((os.path.join(kb_dir, name), name))
        if not paths:
            default_text = (
                "Идеи, как разбавить рабочий день:\n"
                "- Короткая прогулка 10–15 минут между блоками концентрации.\n"
                "- 5 минут растяжки или гимнастики для шеи и спины.\n"
                "- Осознанный перерыв без экрана: чай, вода, несколько глубоких вдохов.\n"
                "- Мини-сессия планирования: записать три приоритета на оставшееся время.\n"
                "- Небольшое творческое занятие: скетч, чтение нескольких страниц книги.\n"
                "Баланс будней:\n"
                "- Запланировать хотя бы одно приятное личное занятие в середине дня.\n"
                "- Выделить «окно без уведомлений» для глубокой работы.\n"
                "- Вечером подвести итоги дня и выбрать один микро-шаг на завтра.\n"
            )
            tokens = Counter(_tokenize(default_text))
            self.chunks = [_DocChunk(text=default_text, tokens=tokens, source="builtin")]
            return

        chunks: List[_DocChunk] = []
        for path, name in paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue
            for block in content.split("\n\n"):
                block_clean = block.strip()
                if not block_clean:
                    continue
                tokens = Counter(_tokenize(block_clean))
                if not tokens:
                    continue
                chunks.append(_DocChunk(text=block_clean, tokens=tokens, source=name))
        if chunks:
            self.chunks = chunks

    def retrieve(self, query: str, top_k: int = 3) -> List[_DocChunk]:
        if not self.chunks:
            return []
        q_tokens = Counter(_tokenize(query))
        scored: List[Tuple[float, _DocChunk]] = []
        for ch in self.chunks:
            score = _cosine_sim(q_tokens, ch.tokens)
            if score > 0:
                scored.append((score, ch))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    def build_advice(self, snapshot: Snapshot, features: Features, risk: RiskResult) -> RAGAdvice:
        day_desc: List[str] = [
            f"Рабочее время: {features.work_minutes // 60}ч {features.work_minutes % 60}мин",
            f"Встречи: {features.meeting_minutes}мин ({features.meet_ratio * 100:.0f}% дня)",
            f"Фокус-время: {features.deepwork_minutes}мин",
            f"Перерывы: {features.break_minutes}мин",
            f"Переключения контекста: {features.context_switches}",
            f"Отвлечения: {features.distractions_minutes}мин",
            f"Риск выгорания (оценка): {risk.risk_score}",
        ]
        if features.steps is not None:
            day_desc.append(f"Шаги: {features.steps}")
        if features.sleep_h is not None:
            day_desc.append(f"Сон: {features.sleep_h:.1f}ч")
        if snapshot.surveys:
            last = snapshot.surveys[-1]
            vals = []
            if last.stress_1_10 is not None:
                vals.append(f"стресс {last.stress_1_10}/10")
            if last.fatigue_1_10 is not None:
                vals.append(f"усталость {last.fatigue_1_10}/10")
            if vals:
                day_desc.append("Самочувствие: " + ", ".join(vals))

        query = ". ".join(day_desc)
        chunks = self.retrieve(query, top_k=6)
        base_suggestions = [c.text for c in chunks] if chunks else []
        sources = [c.source for c in chunks] if chunks else None

        hf = HFClient()
        if not hf.token or not base_suggestions:
            return RAGAdvice(suggestions=base_suggestions, sources=sources)

        context = "\n\n".join(base_suggestions)
        prompt = (
            "У тебя есть контекст с идеями по балансу работы и отдыха.\n"
            "Сформируй 5–7 конкретных советов для пользователя, опираясь на его день и этот контекст.\n\n"
            f"Описание дня:\n{query}\n\n"
            f"Контекст:\n{context}\n\n"
            "Верни только список советов, по одному на строку, без лишнего текста."
        )

        import httpx, os
        headers = {
            "Authorization": f"Bearer {hf.token}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",
        }
        payload = {
            "model": hf.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4,
            "max_tokens": 300,
        }

        try:
            with httpx.Client(timeout=60) as c:
                r = c.post(
                    f"{hf.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                r.raise_for_status()
                data = r.json()
                if isinstance(data, dict) and "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"].get("content", "")
                    lines = [ln.strip("-• ").strip() for ln in content.splitlines() if ln.strip()]
                    if lines:
                        return RAGAdvice(suggestions=lines, sources=sources)
        except Exception:
            return RAGAdvice(suggestions=base_suggestions, sources=sources)

        return RAGAdvice(suggestions=base_suggestions, sources=sources)


