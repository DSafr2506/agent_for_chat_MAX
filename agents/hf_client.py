from __future__ import annotations
from typing import List, Dict
import os
import httpx


class HFClient:
    """
    Использует OpenRouter API с моделью Google Gemma 2 27B для саммаризации.
    Переменные окружения:
      OPENROUTER_API_KEY      — обязательна для вызовов (по умолчанию используется встроенный ключ)
      OPENROUTER_MODEL        — по умолчанию 'google/gemma-2-27b-it'
    """
    def __init__(self):
    
        self.token = os.getenv("OPENROUTER_API_KEY", "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")
        self.model = os.getenv("OPENROUTER_MODEL", "google/gemma-2-27b-it")
        self.base_url = "https://openrouter.ai/api/v1"

    async def summarize(self, text: str, max_new_tokens: int = 120) -> str:
        if not (self.token and text.strip()):
            return ""
        
        text_input = text[:4000]
        
        
        prompt = (
            f"Сделай краткую выжимку смысловую выдержкуиз текса  (до {max_new_tokens} слов, на русском языке):\n\n"
            f"{text_input}\n\n"
            "Резюме:"
        )
        
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
            "temperature": 0.3,
            "max_tokens": max_new_tokens + 50,  
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
            # Логируем ошибку для отладки
            print(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"OpenRouter API exception: {e}")
        
        return ""

    async def generate_efficiency_recommendations(self, day_summary: str, features_summary: str, max_tokens: int = 300) -> str:
        if not self.token:
            return ""
        
        prompt = (
            "Ты эксперт по продуктивности и управлению временем. "
            "Проанализируй данные рабочего дня и дай конкретные рекомендации по увеличению эффективности.\n\n"
            f"Резюме дня:\n{day_summary}\n\n"
            f"Метрики производительности:\n{features_summary}\n\n"
            "Дай 5-7 конкретных рекомендаций по улучшению эффективности работы. "
            "Фокусируйся на:\n"
            "- Оптимизации расписания и встреч\n"
            "- Улучшении фокуса и концентрации\n"
            "- Снижении переключений контекста\n"
            "- Балансе работы и отдыха\n"
            "- Управлении коммуникациями\n\n"
            "Формат: каждая рекомендация должна быть конкретной и выполнимой. "
            "Начинай каждую рекомендацию с действия (глагол). "
            "Отвечай на русском языке."
        )
        
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
            "temperature": 0.4,  
            "max_tokens": max_tokens,
        }
        
        try:
            async with httpx.AsyncClient(timeout=90) as c:  
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
            print(f"OpenRouter API error (efficiency): {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"OpenRouter API exception (efficiency): {e}")
        
        return ""

    async def assess_fatigue_load(self, day_summary: str, features_summary: str, max_tokens: int = 220) -> str:
        if not self.token:
            return ""

        prompt = (
            "Ты специалист по здоровью и выгоранию. По данным о дне оцени:\n"
            "- усталость (0–100)\n"
            "- загруженность/напряжение дня (0–100)\n"
            "- словесный уровень: low/medium/high\n"
            "- краткое объяснение.\n\n"
            f"Резюме дня:\n{day_summary}\n\n"
            f"Метрики и нагрузка:\n{features_summary}\n\n"
            "Ответ верни строго в JSON-формате без лишнего текста, вида:\n"
            "{"
            "\"fatigue_score\": 0-100 число, "
            "\"load_score\": 0-100 число, "
            "\"level\": \"low\" | \"medium\" | \"high\", "
            "\"explanation\": \"краткий текст\""
            "}"
        )

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
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=90) as c:
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
            print(f"OpenRouter API error (fatigue): {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"OpenRouter API exception (fatigue): {e}")

        return ""




