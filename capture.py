"""Find the scrcpy window on macOS and capture its contents via Quartz."""

import logging

import Quartz
import numpy as np
from PIL import Image

logger = logging.getLogger("scanner")


def find_scrcpy_window(title_substr: str = "scrcpy") -> dict | None:
    """Return {x, y, w, h, id} of the first window whose title contains title_substr."""
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    for win in window_list:
        name = win.get(Quartz.kCGWindowName, "")
        owner = win.get(Quartz.kCGWindowOwnerName, "")
        if title_substr.lower() in (name or "").lower() or title_substr.lower() in (owner or "").lower():
            bounds = win.get(Quartz.kCGWindowBounds)
            wid = win.get(Quartz.kCGWindowNumber)
            if bounds and wid:
                return {
                    "x": int(bounds["X"]),
                    "y": int(bounds["Y"]),
                    "w": int(bounds["Width"]),
                    "h": int(bounds["Height"]),
                    "id": int(wid),
                }
    return None


def capture_window(window_info: dict) -> np.ndarray | None:
    """Capture a specific window by its ID using Quartz, return BGR numpy array.

    This captures the window contents even if it's behind other windows.
    """
    wid = window_info["id"]

    # Capture the specific window by ID
    cg_image = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull,  # use the window's own bounds
        Quartz.kCGWindowListOptionIncludingWindow,
        wid,
        Quartz.kCGWindowImageBoundsIgnoreFraming,
    )

    if cg_image is None:
        logger.warning("Failed to capture window (id=%d)", wid)
        return None

    width = Quartz.CGImageGetWidth(cg_image)
    height = Quartz.CGImageGetHeight(cg_image)
    bpr = Quartz.CGImageGetBytesPerRow(cg_image)

    provider = Quartz.CGImageGetDataProvider(cg_image)
    data = Quartz.CGDataProviderCopyData(provider)

    # CGImage data is BGRA (on macOS)
    arr = np.frombuffer(data, dtype=np.uint8).reshape((height, bpr // 4, 4))
    # Trim to actual width (bpr may include padding)
    arr = arr[:, :width, :]
    # BGRA → BGR
    return arr[:, :, :3].copy()


def capture_scrcpy(title_substr: str = "scrcpy") -> tuple[np.ndarray | None, dict | None]:
    """Convenience: find window + capture in one call."""
    info = find_scrcpy_window(title_substr)
    if info is None:
        logger.warning("scrcpy window not found")
        return None, None
    frame = capture_window(info)
    return frame, info
