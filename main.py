"""Main orchestrator: capture → detect change → decode QR → output."""

import logging
import signal
import sys
import time

from capture import capture_scrcpy, capture_adb
from detection import ChangeDetector
from decoder import decode_qr_fast
from output import fire_outputs
from utils import (
    load_config,
    setup_logging,
    JsonLinesLogger,
)

logger = logging.getLogger("scanner")

_running = True


def _sigint_handler(sig, frame):
    global _running
    logger.info("Shutting down...")
    _running = False


def validate_setup(config: dict) -> bool:
    from capture import find_scrcpy_window

    title = config.get("scrcpy_window_title", "scrcpy")
    bounds = find_scrcpy_window(title)
    if bounds is None:
        logger.error("scrcpy window not found. Start scrcpy first.")
        return False

    if config.get("chat_region") is None:
        logger.error("Chat region not calibrated. Run: python calibration.py")
        return False

    if not config.get("discord_webhook_url"):
        logger.warning("Discord webhook URL not set — Discord output disabled")

    return True


def crop_chat_region(frame, region: dict):
    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
    return frame[y : y + h, x : x + w]


def main():
    setup_logging()
    signal.signal(signal.SIGINT, _sigint_handler)

    config = load_config()
    if not validate_setup(config):
        sys.exit(1)

    title = config.get("scrcpy_window_title", "scrcpy")
    region = config["chat_region"]
    adb_serial = config.get("adb_serial", "")
    phone_w = config.get("phone_screen_width", 720)
    phone_h = config.get("phone_screen_height", 1600)
    threshold_pct = config.get("change_threshold_pct", 10.0)

    FAST_INTERVAL = 0.05   # 50ms when watching/active
    IDLE_INTERVAL = 0.5    # 500ms when idle
    IDLE_TIMEOUT = 15      # go idle after 15s no change

    detector = ChangeDetector(threshold_pct=threshold_pct)
    jlog = JsonLinesLogger(config.get("log_file", "scanner.log.jsonl"))

    seen_content: set[str] = set()
    last_change_time = time.time()
    watching = False  # True while waiting for frame to stabilize

    logger.info("Scanner started (fast mode). Press Ctrl+C to stop.")
    jlog.log("start")

    while _running:
        now = time.time()

        # Adaptive sleep: fast when watching for stability, idle otherwise
        idle = now - last_change_time
        if watching:
            time.sleep(FAST_INTERVAL)
        else:
            time.sleep(IDLE_INTERVAL if idle > IDLE_TIMEOUT else FAST_INTERVAL)

        frame, bounds = capture_scrcpy(title)
        if frame is None:
            continue

        chat_frame = crop_chat_region(frame, region)

        changed, stable = detector.detect(chat_frame)

        if changed:
            last_change_time = time.time()
            watching = True
            continue  # don't decode mid-scroll

        if stable:
            watching = False
            # Frame settled — try scrcpy frame first, then ADB lossless
            decoded_list = decode_qr_fast(chat_frame)

            if not decoded_list:
                # Fallback: lossless ADB screencap for better QR quality
                adb_frame = capture_adb(serial=adb_serial)
                if adb_frame is not None:
                    # Crop same chat region, scaled to phone resolution
                    sx = phone_w / (region["w"] + region["x"] * 2)
                    sy = phone_h / (region["h"] + region["y"] * 2)
                    ax = int(region["x"] * sx)
                    ay = int(region["y"] * sy)
                    aw = int(region["w"] * sx)
                    ah = int(region["h"] * sy)
                    ah = min(ah, adb_frame.shape[0] - ay)
                    aw = min(aw, adb_frame.shape[1] - ax)
                    adb_chat = adb_frame[ay:ay+ah, ax:ax+aw]
                    decoded_list = decode_qr_fast(adb_chat)

            for decoded in decoded_list:
                if decoded in seen_content:
                    continue
                seen_content.add(decoded)

                logger.info("=== QR DECODED: %s", decoded[:120])
                jlog.log("qr_decoded", content=decoded)

                fire_outputs(decoded, config)

        if not changed and not stable and watching:
            # Still watching but not yet stable — keep fast-polling
            continue

    jlog.log("stop")
    logger.info("Scanner stopped.")


if __name__ == "__main__":
    main()
