# m4-vision

The **vision + dashboard** app. Runs on the Mac. Captures the fight off your
screen, runs a **local VLM** (Ollama) for perception, sends observations to the
**pc-judge** service for scoring, and shows a live dashboard. No cloud, no keys.

## Setup (on the Mac)

1. Install [Ollama](https://ollama.com/download) and pull a vision model:
   ```
   ollama pull moondream        # tiny + fast, coarse
   # or: ollama pull minicpm-v  # bigger, better, needs more RAM
   ```
2. Grant **Screen Recording** permission to your terminal
   (System Settings → Privacy & Security → Screen Recording).
3. `pip install -r requirements.txt`
4. `cp .env.example .env` and set:
   - `VLM_MODEL` — the model you pulled.
   - `JUDGE_SERVICE_URL` — the PC's LAN IP, e.g. `http://192.168.1.50:8100`
     (use `http://127.0.0.1:8100` if you're running `pc-judge` on this same Mac
     for testing).

## Run

Make sure `pc-judge` is already running (on the PC or locally), then:

```
python run.py
```

- Drag a box over the fight video (or **Esc** for full screen).
- Open http://127.0.0.1:8000 in your browser.

## How it fits together

```
[screen] -> capture -> local VLM (Ollama) -> observations
                                              |
                                     HTTP to pc-judge (PC)
                                              |
                                   scores + feed -> dashboard
```

## Tuning (`.env`)

- Small VLMs handle **one image at a time** best — try `VISION_BATCH_SIZE=1` if
  multi-frame batches produce junk.
- Raise `VISION_INTERVAL` to reduce load; lower `CAPTURE_INTERVAL` + raise
  `VISION_BATCH_SIZE` to sample denser without more calls.
- `DEBUG=1` logs the raw VLM output so you can see what it's actually reporting.

## Reality check

A small local VLM is coarse — good at "someone's down / ground / standing / big
motion", weak at precise strike counts. Treat scores as a vibe read. If it's too
rough, step up `VLM_MODEL` (RAM permitting) or move vision back to a cloud VLM.
