"""Discord webhook posting and ADB open-URL for QR code results."""

import logging
import subprocess
import time
from datetime import datetime, timezone
from threading import Thread

import requests

logger = logging.getLogger("scanner")


def send_discord(webhook_url: str, content: str, qr_type: str = "QR Code"):
    """Post decoded QR content to Discord via webhook embed."""
    if not webhook_url:
        logger.warning("Discord webhook URL not configured, skipping")
        return

    embed = {
        "title": f"🔍 {qr_type} Detected",
        "description": content[:2000],
        "color": 0x07C160,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": "QR Scanner"},
    }
    payload = {"embeds": [embed]}

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            logger.info("Discord message sent")
        else:
            logger.error("Discord webhook failed: %d %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.error("Discord webhook error: %s", e)


def adb_open_url(decoded: str, serial: str = ""):
    """Open the decoded QR content on the phone via ADB.

    If the content is a URL, open it in the browser/app.
    Otherwise, just log it (non-URL QR content can't be "opened").
    """
    # Only open URLs on the phone
    if not decoded.startswith(("http://", "https://")):
        logger.info("QR content is not a URL, skipping ADB open: %s", decoded[:80])
        return

    logger.info("ADB opening URL on phone: %s", decoded[:80])

    try:
        cmd = ["adb"]
        if serial:
            cmd += ["-s", serial]
        cmd += ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", decoded]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("ADB opened URL on phone")
        else:
            logger.error("ADB open URL failed: %s", result.stderr.strip()[:200])
    except subprocess.TimeoutExpired:
        logger.error("ADB command timed out")
    except FileNotFoundError:
        logger.error("adb not found in PATH")
    except Exception as e:
        logger.error("ADB error: %s", e)


def fire_outputs(decoded: str, config: dict):
    """Fire Discord webhook and ADB open-URL concurrently."""
    threads = []

    t1 = Thread(
        target=send_discord,
        args=(config.get("discord_webhook_url", ""), decoded),
    )
    threads.append(t1)

    if config.get("adb_enabled", True):
        t2 = Thread(
            target=adb_open_url,
            args=(decoded,),
            kwargs={"serial": config.get("adb_serial", "")},
        )
        threads.append(t2)

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)
