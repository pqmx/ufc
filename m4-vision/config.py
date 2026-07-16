"""m4-vision configuration. Runs on the Mac."""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Local VLM (this machine, via Ollama) -----------------------------------
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
VLM_MODEL = os.environ.get("VLM_MODEL", "moondream")

# --- Judge service (the PC) -------------------------------------------------
# Set to the PC's LAN IP, e.g. http://192.168.1.50:8100. 127.0.0.1 for testing
# both services on this machine.
JUDGE_SERVICE_URL = os.environ.get("JUDGE_SERVICE_URL", "http://127.0.0.1:8100")

# --- Capture pipeline -------------------------------------------------------
CAPTURE_INTERVAL = float(os.environ.get("CAPTURE_INTERVAL", "2.0"))
VISION_INTERVAL = float(os.environ.get("VISION_INTERVAL", "6.0"))
VISION_BATCH_SIZE = int(os.environ.get("VISION_BATCH_SIZE", "3"))
FRAME_LONG_EDGE = int(os.environ.get("FRAME_LONG_EDGE", "768"))
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY", "70"))

# --- Timeouts ---------------------------------------------------------------
VLM_TIMEOUT = float(os.environ.get("VLM_TIMEOUT", "120"))
JUDGE_TIMEOUT = float(os.environ.get("JUDGE_TIMEOUT", "120"))

# --- Dashboard server -------------------------------------------------------
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
