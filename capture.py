"""Capture the phone screen via ADB screencap (lossless) or Quartz (fallback)."""

import logging
import subprocess

import Quartz
import numpy as np
import cv2
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
    """Capture a specific window by its ID using Quartz, return BGR numpy array."""
    wid = window_info["id"]

    cg_image = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull,
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

    arr = np.frombuffer(data, dtype=np.uint8).reshape((height, bpr // 4, 4))
    arr = arr[:, :width, :]
    return arr[:, :, :3].copy()


def capture_adb(serial: str = "") -> np.ndarray | None:
    """Capture a lossless PNG screenshot directly from the phone via ADB."""
    try:
        cmd = ["adb"]
        if serial:
            cmd += ["-s", serial]
        cmd += ["exec-out", "screencap", "-p"]

        result = subprocess.run(cmd, capture_output=True, timeout=5)
        if result.returncode != 0 or not result.stdout:
            return None

        arr = np.frombuffer(result.stdout, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.debug("ADB screencap failed: %s", e)
        return None


def capture_scrcpy(title_substr: str = "scrcpy") -> tuple[np.ndarray | None, dict | None]:
    """Convenience: find window + capture in one call."""
    info = find_scrcpy_window(title_substr)
    if info is None:
        logger.warning("scrcpy window not found")
        return None, None
    frame = capture_window(info)
    return frame, info
