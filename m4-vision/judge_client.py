"""Judge client: sends observations to the pc-judge service and applies the delta.

The judging LLM lives on the PC (pc-judge). This module builds the request from
the local FightState, POSTs it, and folds the returned delta back into state.
"""

from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable

import httpx

import config
from state import FightState, RoundScore, ShotEvent

Broadcast = Callable[[], Awaitable[None]]


def _as_int(x, default: int = 0) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def state_summary(s: FightState) -> dict:
    recent = [
        {"round": f.round, "clock": f.clock, "corner": f.corner, "text": f.text}
        for f in s.feed[:8]
    ]
    return {
        "current_round": s.current_round,
        "names": {"red": s.red.name, "blue": s.blue.name},
        "current_round_tally": {
            "red": {
                "sig_strikes": s.red.sig_strikes,
                "takedowns": s.red.takedowns,
                "control_seconds": s.red.control_seconds,
            },
            "blue": {
                "sig_strikes": s.blue.sig_strikes,
                "takedowns": s.blue.takedowns,
                "control_seconds": s.blue.control_seconds,
            },
        },
        "scorecard_so_far": [
            {"round": r.round, "red": r.red, "blue": r.blue} for r in s.scorecard
        ],
        "recent_feed": recent,
    }


def apply_delta(state: FightState, observation: dict, delta: dict) -> None:
    s = state
    clock = str(observation.get("clock") or "")
    if clock:
        s.clock = clock

    # Round rollover FIRST: finalize the previous round, reset tallies, and advance the
    # round number before folding in this batch's tallies/feed. Otherwise a delta that both
    # reports new-round action and completes the previous round would have its tallies wiped
    # by reset_round_tallies() and its feed tagged with the old round.
    rc = delta.get("round_completed")
    if isinstance(rc, dict) and _as_int(rc.get("round")) >= 1:
        s.finalize_round(
            RoundScore(
                round=_as_int(rc.get("round")),
                red=_as_int(rc.get("red")),
                blue=_as_int(rc.get("blue")),
                note=str(rc.get("note") or ""),
            )
        )
        s.reset_round_tallies()

    new_round = _as_int(delta.get("current_round"), s.current_round)
    if new_round > s.current_round:
        s.current_round = new_round

    # Lock names once auto-detect confirms them twice.
    for corner in ("red", "blue"):
        name = ((delta.get("detected_names", {}) or {}).get(corner) or "").strip()
        fighter = s.fighter(corner)
        if name and not fighter.name_locked:
            if fighter.name == name:
                fighter.name_locked = True
            else:
                fighter.name = name

    # Fold in tallies for the (now-current) round.
    for corner in ("red", "blue"):
        d = (delta.get("tally_delta", {}) or {}).get(corner, {}) or {}
        f = s.fighter(corner)
        f.sig_strikes += max(0, _as_int(d.get("sig_strikes")))
        f.takedowns += max(0, _as_int(d.get("takedowns")))
        f.control_seconds += max(0, _as_int(d.get("control_seconds")))

    # Curated feed items, tagged with the current round.
    for item in delta.get("feed", []) or []:
        corner = item.get("corner")
        text = (item.get("text") or "").strip()
        if corner in ("red", "blue") and text:
            s.add_shot(
                ShotEvent(
                    ts=time.time(),
                    round=s.current_round,
                    clock=s.clock,
                    corner=corner,
                    text=text,
                    kind=item.get("kind", "strike"),
                    rocked=bool(item.get("rocked", False)),
                )
            )

    s.touch()


async def judge_loop(
    obs_queue: "asyncio.Queue[dict]",
    state: FightState,
    broadcast: Broadcast,
) -> None:
    url = f"{config.JUDGE_SERVICE_URL}/judge"
    print(f"[judge] using pc-judge at {url}")
    async with httpx.AsyncClient(timeout=config.JUDGE_TIMEOUT) as client:
        while True:
            observation = await obs_queue.get()
            payload = {
                "current_state": state_summary(state),
                "new_observation": observation,
            }
            try:
                r = await client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
            except Exception as exc:  # pragma: no cover
                print(f"[judge] pc-judge unreachable: {exc}")
                await _set_status(state, "error", broadcast)
                continue
            if not data.get("ok"):
                print(f"[judge] pc-judge error: {data.get('error')}")
                await _set_status(state, "error", broadcast)
                continue
            try:
                apply_delta(state, observation, data.get("delta") or {})
            except Exception as exc:  # pragma: no cover
                print(f"[judge] bad delta, skipping: {exc}")
                continue
            state.status = "capturing"
            await broadcast()


async def _set_status(state: FightState, status: str, broadcast: Broadcast) -> None:
    """Push a status change (e.g. judge unreachable) to the dashboard, once."""
    if state.status != status:
        state.status = status
        state.touch()
        await broadcast()
