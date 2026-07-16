"""Pick the screen region to capture.

Opens a fullscreen semi-transparent overlay; drag a box over the video. Returns
an mss-style region dict {top, left, width, height}. Falls back to the primary
monitor if tkinter isn't usable.
"""

from __future__ import annotations


def select_region() -> dict:
    try:
        return _tk_drag_select()
    except Exception as exc:  # pragma: no cover
        print(f"[region] drag-select unavailable ({exc}); using full monitor.")
        return _full_monitor()


def _full_monitor() -> dict:
    import mss

    with mss.mss() as sct:
        mon = sct.monitors[1]
    return {
        "top": mon["top"],
        "left": mon["left"],
        "width": mon["width"],
        "height": mon["height"],
    }


def _tk_drag_select() -> dict:
    import tkinter as tk

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.25)
    root.configure(bg="black")
    root.title("Drag over the fight video, then release")

    canvas = tk.Canvas(root, cursor="crosshair", bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    canvas.create_text(
        root.winfo_screenwidth() // 2,
        40,
        text="Drag a box over the fight video, then release.  (Esc to use full screen)",
        fill="white",
        font=("Helvetica", 20),
    )

    sel = {"x0": 0, "y0": 0, "x1": 0, "y1": 0}
    rect_id = {"id": None}
    result: dict = {}

    def on_press(e):
        sel["x0"], sel["y0"] = e.x_root, e.y_root
        if rect_id["id"]:
            canvas.delete(rect_id["id"])
        rect_id["id"] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="#e11", width=3)
        rect_id["cx0"], rect_id["cy0"] = e.x, e.y

    def on_drag(e):
        if rect_id["id"]:
            canvas.coords(rect_id["id"], rect_id["cx0"], rect_id["cy0"], e.x, e.y)

    def on_release(e):
        sel["x1"], sel["y1"] = e.x_root, e.y_root
        root.destroy()

    def on_escape(_):
        result["escape"] = True
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", on_escape)
    # Capture the logical screen width before the window is destroyed; needed to
    # convert the tk-point selection to mss pixels below.
    screen_w = root.winfo_screenwidth()
    root.mainloop()

    if result.get("escape"):
        return _full_monitor()

    left = min(sel["x0"], sel["x1"])
    top = min(sel["y0"], sel["y1"])
    width = abs(sel["x1"] - sel["x0"])
    height = abs(sel["y1"] - sel["y0"])

    if width < 50 or height < 50:
        print("[region] selection too small; using full monitor.")
        return _full_monitor()

    # tkinter reports logical points; mss.grab expects physical pixels. On a Retina
    # display these differ (e.g. 2x), so scale by the monitor pixel/point ratio.
    scale = _screen_scale(screen_w)
    return {
        "top": int(top * scale),
        "left": int(left * scale),
        "width": int(width * scale),
        "height": int(height * scale),
    }


def _screen_scale(screen_w_points: int) -> float:
    """Ratio of physical pixels (what mss captures) to tk points, from the primary
    monitor. Returns 1.0 if it can't be determined (already-pixel platforms)."""
    try:
        import mss

        with mss.mss() as sct:
            pixels_w = sct.monitors[1]["width"]
        if screen_w_points > 0 and pixels_w > 0:
            return pixels_w / screen_w_points
    except Exception:  # pragma: no cover
        pass
    return 1.0


if __name__ == "__main__":
    print(select_region())
