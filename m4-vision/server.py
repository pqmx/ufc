"""FastAPI server (Mac): wires the local pipeline and pushes state to the browser.

    capture_loop -> frame_queue
    vision_loop  -> obs_queue    (local VLM via Ollama)
    judge_loop   -> FightState   (calls pc-judge on the PC) -> broadcast()
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

import config
from capture import capture_loop
from judge_client import judge_loop
from state import FightState
from vision import vision_loop

REGION: dict | None = None   # set by run.py before startup
FRONTEND_DIR = Path(__file__).parent / "frontend"

state = FightState()
_clients: set[WebSocket] = set()
_tasks: list[asyncio.Task] = []


async def broadcast() -> None:
    if not _clients:
        return
    msg = json.dumps({"type": "state", "state": state.to_dict()})
    dead = []
    for ws in list(_clients):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    if REGION is None:
        raise RuntimeError("server.REGION must be set before startup")
    frame_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=config.VISION_BATCH_SIZE * 4)
    obs_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=16)

    state.status = "capturing"
    _tasks.append(asyncio.create_task(capture_loop(REGION, frame_queue)))
    _tasks.append(asyncio.create_task(vision_loop(frame_queue, obs_queue)))
    _tasks.append(asyncio.create_task(judge_loop(obs_queue, state, broadcast)))
    print(f"[server] http://{config.HOST}:{config.PORT}")
    try:
        yield
    finally:
        for t in _tasks:
            t.cancel()
        await asyncio.gather(*_tasks, return_exceptions=True)


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    await ws.send_text(json.dumps({"type": "state", "state": state.to_dict()}))
    try:
        while True:
            raw = await ws.receive_text()
            await _handle_client_message(raw)
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)


async def _handle_client_message(raw: str) -> None:
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return
    if msg.get("type") == "set_name":
        corner = msg.get("corner")
        name = (msg.get("name") or "").strip()
        # Ignore blank submissions — otherwise we'd lock an empty name and permanently
        # disable broadcast-graphic auto-detection for this corner.
        if corner in ("red", "blue") and name:
            f = state.fighter(corner)
            f.name = name
            f.name_locked = True
            state.touch()
            await broadcast()


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
