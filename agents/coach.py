from __future__ import annotations
import os
import httpx
from .models import RiskResult, Features


class LLMClient:
    """
    Использует OpenRouter API с моделью Google Gemma 2 27B для коучинга.
    Переменные окружения:
      OPENROUTER_API_KEY      — обязательна для вызовов (по умолчанию используется встроенный ключ)
      OPENROUTER_MODEL        — по умолчанию 'google/gemma-2-27b-it'
    """
    def __init__(self):
        
        self.token = os.getenv("OPENROUTER_API_KEY", "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")
        self.model = os.getenv("OPENROUTER_MODEL", "google/gemma-2-27b-it")
        self.base_url = "https://openrouter.ai/api/v1"

    async def coach(self, risk: RiskResult, f: Features) -> str:
        prompt = (
            "Сформируй краткий бриф (до 80 слов) по снижению риска выгорания. "
            "Дай 3–5 конкретных шагов с причинами. "
            f"Риск={risk.risk_score}. Факторы={risk.factors}. "
            f"Сон={f.sleep_h}ч, шаги={f.steps}, митинги={f.meeting_minutes}мин, "
            f"стретч_без_перерыва={f.longest_stretch_no_break_min}мин, переключения={f.context_switches}."
        )
        
        
        if not self.token:
            parts = []
            if risk.risk_score >= 70: parts.append("дыхание 4-7-8 (5 мин) + 20 мин DND")
            if (f.steps or 0) < 3000: parts.append("прогулка 10–15 мин")
            if f.longest_stretch_no_break_min >= 120: parts.append("перерыв 5–10 мин каждые 55–70 мин")
            if f.meet_ratio > 0.5: parts.append("сгруппируй встречи; поставь фокус-блок 60–90 мин")
            if not parts: parts = ["перерывы по расписанию, вода, 15-мин winddown"]
            return "План: " + "; ".join(parts) + "."
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 200,
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                r.raise_for_status()
                data = r.json()
                
                if isinstance(data, dict) and "choices" in data:
                    if data["choices"] and "message" in data["choices"][0]:
                        content = data["choices"][0]["message"].get("content", "")
                        return content.strip()
        except httpx.HTTPStatusError as e:
            print(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"OpenRouter API exception: {e}")
        
        parts = []
        if risk.risk_score >= 70: parts.append("дыхание 4-7-8 (5 мин) + 20 мин DND")
        if (f.steps or 0) < 3000: parts.append("прогулка 10–15 мин")
        if f.longest_stretch_no_break_min >= 120: parts.append("перерыв 5–10 мин каждые 55–70 мин")
        if f.meet_ratio > 0.5: parts.append("сгруппируй встречи; поставь фокус-блок 60–90 мин")
        if not parts: parts = ["перерывы по расписанию, вода, 15-мин winddown"]
        return f"План (fallback): " + "; ".join(parts) + "."


