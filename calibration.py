"""Interactive region selector: click-drag to define the chat message area."""

import logging
import sys

import cv2
import numpy as np

from capture import capture_scrcpy
from utils import load_config, save_config

logger = logging.getLogger("scanner")

_drawing = False
_start = (0, 0)
_end = (0, 0)
_done = False


def _mouse_cb(event, x, y, flags, param):
    global _drawing, _start, _end, _done
    if event == cv2.EVENT_LBUTTONDOWN:
        _drawing = True
        _start = (x, y)
        _end = (x, y)
    elif event == cv2.EVENT_MOUSEMOVE and _drawing:
        _end = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        _drawing = False
        _end = (x, y)
        _done = True


def run_calibration():
    """Capture scrcpy, let user select chat region, save to config."""
    frame, bounds = capture_scrcpy()
    if frame is None:
        print("ERROR: Could not find scrcpy window. Make sure scrcpy is running.")
        sys.exit(1)

    print("Select the chat message area by clicking and dragging.")
    print("Press ENTER to confirm, ESC to cancel.")

    win_name = "Calibration - Select Chat Area"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win_name, _mouse_cb)

    global _done, _start, _end
    while True:
        display = frame.copy()
        if _drawing or _done:
            cv2.rectangle(display, _start, _end, (0, 255, 0), 2)
        cv2.imshow(win_name, display)

        key = cv2.waitKey(30) & 0xFF
        if key == 27:  # ESC
            print("Cancelled.")
            cv2.destroyAllWindows()
            sys.exit(0)
        if key == 13 and _done:  # ENTER
            break

    cv2.destroyAllWindows()

    x1 = min(_start[0], _end[0])
    y1 = min(_start[1], _end[1])
    x2 = max(_start[0], _end[0])
    y2 = max(_start[1], _end[1])

    if x2 - x1 < 10 or y2 - y1 < 10:
        print("ERROR: Selected region too small. Please try again.")
        sys.exit(1)

    # Store as relative coordinates within the scrcpy window
    region = {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}
    cfg = load_config()
    cfg["chat_region"] = region
    save_config(cfg)
    print(f"Chat region saved: {region}")
    print("You can re-run calibration.py if the scrcpy window size changes.")


if __name__ == "__main__":
    from utils import setup_logging
    setup_logging()
    run_calibration()
