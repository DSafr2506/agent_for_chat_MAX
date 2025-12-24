from __future__ import annotations

from typing import Any, Dict

import asyncio
from fastapi import FastAPI
from pydantic import BaseModel

from agents import Snapshot, Output, analyze_async, analyze_text_async


class TextRequest(BaseModel):
    user_id: str = "user"
    text: str
    tz: str | None = None


app = FastAPI(title="Personal Load Agent", version="1.0.0")


@app.post("/analyze", response_model=Output)
async def analyze_endpoint(snapshot: Snapshot) -> Output:
    data: Dict[str, Any] = snapshot.model_dump()
    return await analyze_async(data)


@app.post("/analyze-text", response_model=Output)
async def analyze_text_endpoint(req: TextRequest) -> Output:
    return await analyze_text_async(text=req.text, user_id=req.user_id, tz=req.tz)


def run() -> None:
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()


