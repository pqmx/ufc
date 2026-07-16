"""Perception via a LOCAL VLM (Ollama on this machine).

The "eyes" of the system, fully on-device. Batches of frames go to the local vision
model, which reports what it sees as structured JSON observations. It does NOT judge.
"""

from __future__ import annotations

import asyncio
import base64
import json

import httpx

import config

_SYSTEM = """You are a combat-sports vision analyst watching a UFC/MMA broadcast.
You are given still frames captured a couple of seconds apart. Report ONLY what
you can actually see. Do not score the fight or pick a winner. Be conservative: if
unsure, leave a field empty or use "unknown". Read the on-screen graphics (round
number, fight clock, fighter name overlays) when visible. Respond with JSON only."""

_INSTRUCTION = """From these frames, report what happened in this short window.
Identify each fighter as "red" or "blue" corner where possible. Report significant
actions only (clean/hard strikes, knockdowns, takedowns, slams, submission attempts,
sustained control/ground-and-pound, clear aggression). Call out when a fighter looks
visibly HURT, wobbled, or dropped, and note ground CONTROL (top position, back mount,
grinding ground-and-pound). Ignore routine footwork and misses."""

# Ollama accepts a JSON Schema object as `format`.
_SCHEMA = {
    "type": "object",
    "properties": {
        "round": {"type": "integer"},
        "clock": {"type": "string"},
        "fighters": {
            "type": "object",
            "properties": {"red": {"type": "string"}, "blue": {"type": "string"}},
        },
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "corner": {"type": "string", "enum": ["red", "blue", "unknown"]},
                    "actor": {"type": "string"},
                    "action": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["strike", "combo", "takedown", "knockdown", "submission", "control"],
                    },
                    "significance": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["action", "kind", "significance"],
            },
        },
        "control": {
            "type": "object",
            "properties": {
                "corner": {"type": "string", "enum": ["red", "blue", "none"]},
                "position": {"type": "string"},
            },
        },
    },
    "required": ["round", "events"],
}


async def _analyze(client: httpx.AsyncClient, frames: list[bytes]) -> dict | None:
    images = [base64.b64encode(f).decode("ascii") for f in frames]
    body = {
        "model": config.VLM_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _INSTRUCTION, "images": images},
        ],
        "format": _SCHEMA,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        r = await client.post(f"{config.OLLAMA_URL}/api/chat", json=body)
        r.raise_for_status()
        content = r.json().get("message", {}).get("content", "")
    except Exception as exc:  # pragma: no cover
        print(f"[vision] VLM error: {exc}")
        return None
    return _parse_json(content)


def _parse_json(text: str) -> dict | None:
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


async def vision_loop(
    frame_queue: "asyncio.Queue[bytes]",
    obs_queue: "asyncio.Queue[dict]",
) -> None:
    print(f"[vision] local VLM {config.VLM_MODEL} @ {config.OLLAMA_URL}, "
          f"batch={config.VISION_BATCH_SIZE} every {config.VISION_INTERVAL}s")
    async with httpx.AsyncClient(timeout=config.VLM_TIMEOUT) as client:
        while True:
            await asyncio.sleep(config.VISION_INTERVAL)
            frames = _drain_latest(frame_queue, config.VISION_BATCH_SIZE)
            if not frames:
                continue
            obs = await _analyze(client, frames)
            if not obs:
                continue
            if config.DEBUG:
                print(f"[vision] {json.dumps(obs)[:300]}")
            await obs_queue.put(obs)


def _drain_latest(q: "asyncio.Queue[bytes]", n: int) -> list[bytes]:
    items: list[bytes] = []
    while not q.empty():
        try:
            items.append(q.get_nowait())
        except asyncio.QueueEmpty:
            break
    return items[-n:]
