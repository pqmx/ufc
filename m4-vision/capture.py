"""Screen-capture loop.

Grabs the selected region every CAPTURE_INTERVAL seconds, downscales, encodes
JPEG, and drops it on an asyncio queue. mss is synchronous, so grab+encode runs
in a thread executor to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import io
import time

import mss
from PIL import Image

import config


def _grab_and_encode(region: dict) -> bytes:
    with mss.mss() as sct:
        raw = sct.grab(region)
    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    long_edge = max(img.width, img.height)
    if long_edge > config.FRAME_LONG_EDGE:
        scale = config.FRAME_LONG_EDGE / long_edge
        img = img.resize(
            (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
            Image.LANCZOS,
        )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=config.JPEG_QUALITY)
    return buf.getvalue()


async def capture_loop(region: dict, frame_queue: "asyncio.Queue[bytes]") -> None:
    loop = asyncio.get_running_loop()
    print(f"[capture] region={region} every {config.CAPTURE_INTERVAL}s")
    while True:
        start = time.monotonic()
        try:
            jpeg = await loop.run_in_executor(None, _grab_and_encode, region)
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            frame_queue.put_nowait(jpeg)
        except Exception as exc:  # pragma: no cover
            print(f"[capture] error: {exc}")
        elapsed = time.monotonic() - start
        await asyncio.sleep(max(0.0, config.CAPTURE_INTERVAL - elapsed))
