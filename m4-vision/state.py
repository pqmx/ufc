"""Fight state model shared between the judge client and the dashboard.

`FightState` is the single source of truth pushed to the browser. `judge_client`
mutates it; `server.py` serializes it to JSON over the WebSocket.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Literal

Corner = Literal["red", "blue"]


@dataclass
class Fighter:
    name: str = ""
    name_locked: bool = False
    sig_strikes: int = 0
    takedowns: int = 0
    control_seconds: int = 0


@dataclass
class RoundScore:
    round: int
    red: int
    blue: int
    note: str = ""


@dataclass
class ShotEvent:
    ts: float
    round: int
    clock: str
    corner: Corner
    text: str
    kind: str = "strike"      # strike | combo | takedown | knockdown | submission | control
    rocked: bool = False      # True if this moment badly hurt/dropped a fighter


@dataclass
class FightState:
    status: str = "starting"
    current_round: int = 1
    clock: str = ""
    red: Fighter = field(default_factory=Fighter)
    blue: Fighter = field(default_factory=Fighter)
    scorecard: list[RoundScore] = field(default_factory=list)
    feed: list[ShotEvent] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)

    def fighter(self, corner: Corner) -> Fighter:
        return self.red if corner == "red" else self.blue

    def totals(self) -> dict[str, int]:
        red = sum(r.red for r in self.scorecard)
        blue = sum(r.blue for r in self.scorecard)
        return {"red": red, "blue": blue}

    def add_shot(self, shot: ShotEvent) -> None:
        self.feed.insert(0, shot)
        del self.feed[200:]
        self.touch()

    def finalize_round(self, score: RoundScore) -> None:
        for i, existing in enumerate(self.scorecard):
            if existing.round == score.round:
                self.scorecard[i] = score
                break
        else:
            self.scorecard.append(score)
        self.scorecard.sort(key=lambda r: r.round)
        self.touch()

    def reset_round_tallies(self) -> None:
        for f in (self.red, self.blue):
            f.sig_strikes = 0
            f.takedowns = 0
            f.control_seconds = 0

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["totals"] = self.totals()
        return d
