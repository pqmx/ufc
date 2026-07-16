"""pc-judge configuration. Runs on the PC."""

import os

from dotenv import load_dotenv

load_dotenv()

# Ollama on this (PC) machine.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "qwen2.5:7b-instruct")
# Keep the judge resident for the whole fight; bound context/output for steady latency.
OLLAMA_KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "30m")
JUDGE_NUM_CTX = int(os.environ.get("JUDGE_NUM_CTX", "4096"))
JUDGE_NUM_PREDICT = int(os.environ.get("JUDGE_NUM_PREDICT", "512"))

# Bind 0.0.0.0 so the Mac can reach us over the LAN.
HOST = os.environ.get("JUDGE_HOST", "0.0.0.0")
PORT = int(os.environ.get("JUDGE_PORT", "8100"))

REQUEST_TIMEOUT = float(os.environ.get("JUDGE_TIMEOUT", "120"))
DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
