"""pc-judge: a tiny HTTP service that judges via a local Ollama text model.

Stateless. The Mac POSTs {current_state, new_observation}; we prompt the local
LLM with the rubric + schema and return the JSON delta. Run this on the PC.

    python judge_service.py
"""

from __future__ import annotations

import json

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

import config
from prompts import JUDGE_SCHEMA, RUBRIC

app = FastAPI(title="pc-judge")


class JudgeRequest(BaseModel):
    current_state: dict
    new_observation: dict


@app.get("/health")
async def health() -> dict:
    """Confirms the service is up and Ollama has the model."""
    info = {"ok": True, "model": config.JUDGE_MODEL, "ollama": config.OLLAMA_URL}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{config.OLLAMA_URL}/api/tags")
            tags = [m["name"] for m in r.json().get("models", [])]
            info["ollama_up"] = True
            info["model_pulled"] = any(config.JUDGE_MODEL.split(":")[0] in t for t in tags)
    except Exception as exc:
        info["ollama_up"] = False
        info["error"] = str(exc)
    return info


@app.post("/judge")
async def judge(req: JudgeRequest) -> dict:
    payload = {"current_state": req.current_state, "new_observation": req.new_observation}
    body = {
        "model": config.JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content": json.dumps(payload)},
        ],
        "format": JUDGE_SCHEMA,   # Ollama structured output
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            r = await client.post(f"{config.OLLAMA_URL}/api/chat", json=body)
            r.raise_for_status()
            content = r.json().get("message", {}).get("content", "")
    except Exception as exc:
        return {"ok": False, "error": f"ollama call failed: {exc}"}

    if config.DEBUG:
        print(f"[judge] {content[:300]}")

    delta = _parse_json(content)
    if delta is None:
        return {"ok": False, "error": "model returned non-JSON", "raw": content[:500]}
    return {"ok": True, "delta": delta}


def _parse_json(text: str) -> dict | None:
    """Tolerant JSON parse — small local models sometimes wrap output in prose."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


if __name__ == "__main__":
    import uvicorn

    print(f"[pc-judge] model={config.JUDGE_MODEL} ollama={config.OLLAMA_URL}")
    print(f"[pc-judge] listening on http://{config.HOST}:{config.PORT}")
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="warning")
