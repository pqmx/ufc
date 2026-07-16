# UFC Judge Mode (fully local)

Real-time MMA scorecard + significant-shot feed from a screen capture — no cloud APIs.
Two local services, each backed by [Ollama](https://ollama.com):

```
┌────────────── Mac (m4-vision) ──────────────┐        ┌──── PC (pc-judge) ────┐
 screen capture ─▶ local VLM (perception) ─▶ POST /judge ─▶ local LLM (scoring)
                              │                                     │
                              ▼                                     ▼
                    FightState ◀───────────── delta (feed + round score)
                              │
                              ▼
                  dashboard  ·  scorecard (live) + significant-shots feed
```

- **`m4-vision/`** — runs on the machine watching the video. Captures the screen,
  sends frames to a local vision model (Ollama, e.g. `moondream`/`llava`) to detect
  significant strikes, knockdowns/rocked moments, takedowns, and ground control, then
  serves the dashboard. See `m4-vision/README.md`.
- **`pc-judge/`** — a small HTTP service (can be the same box or a LAN PC) that scores
  each round with a local Ollama text model using the 10-point-must system.
  See `pc-judge/README.md`.

## The overlay
- **Scorecard** — completed rounds from the judge, plus a **live** in-progress row for
  the current round derived from the running tallies.
- **Significant Shots feed** — every notable strike/takedown/submission **and ground
  control**, with a **ROCKED** highlight when a fighter is badly hurt or dropped.

## Run
```sh
# PC (or same machine): start the judge
cd pc-judge && pip install -r requirements.txt && python judge_service.py

# Mac: point JUDGE_SERVICE_URL at the judge, then start capture + dashboard
cd m4-vision && pip install -r requirements.txt && python run.py
```
Both read config from a local `.env` (see each folder's `.env.example`). No Gemini or
Anthropic keys are needed — everything runs on Ollama.
