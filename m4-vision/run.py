"""Entrypoint (Mac): pick the screen region, then start the server + pipeline.

    python run.py
"""

from __future__ import annotations

import uvicorn

import config
import server
from region_select import select_region


def main() -> None:
    print(f"Local VLM: {config.VLM_MODEL} @ {config.OLLAMA_URL}")
    print(f"Judge service: {config.JUDGE_SERVICE_URL}")
    print("Select the fight video region (drag a box, or Esc for full screen)...")
    region = select_region()
    server.REGION = region
    uvicorn.run(server.app, host=config.HOST, port=config.PORT, log_level="warning")


if __name__ == "__main__":
    main()
