# pc-judge

The **judge** service. Runs on the PC, wraps a local text LLM via Ollama, and
scores the fight over HTTP. The Mac (`m4-vision`) POSTs observations here and gets
back scores + curated feed lines. No cloud, no API keys.

## Setup (on the PC)

1. Install [Ollama](https://ollama.com/download).
2. Pull a judging model:
   ```
   ollama pull qwen2.5:7b-instruct
   ```
   (Alternatives: `llama3.1:8b`, `mistral-nemo`. Bigger = better judging, slower.)
3. Make Ollama reachable if you want, but the Mac talks to **this service**, not
   Ollama directly — so you only need Ollama on localhost here.
4. `pip install -r requirements.txt`
5. `cp .env.example .env` (defaults are fine for a first run).

## Run

```
python judge_service.py
```

It listens on `0.0.0.0:8100`. Find the PC's LAN IP (`ipconfig` → IPv4, e.g.
`192.168.1.50`) and allow port **8100** through the firewall for your local
network. On the Mac, set `JUDGE_SERVICE_URL=http://192.168.1.50:8100`.

## Check it

```
curl http://localhost:8100/health
```
Should report `ollama_up: true` and `model_pulled: true`.

## Notes

- Smaller local models are weaker judges than a frontier cloud model — expect a
  rougher "vibe" score. Step up the model size if judging is sloppy.
- Judging is event-driven (a handful of calls per fight), so a few seconds of
  latency per call on CPU is fine.
