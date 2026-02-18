"""QR code decoding with multi-library, multi-scale pipeline.

Order: zxingcpp (most robust) → pyzbar → OpenCV → threshold retries.
Uses multi-scale decoding to handle small QR codes within large frames.
"""

import logging

import cv2
import numpy as np
from pyzbar.pyzbar import decode as pyzbar_decode
import zxingcpp

logger = logging.getLogger("scanner")

_qr_detector = cv2.QRCodeDetector()

# Sharpening kernel
_sharpen_kernel = np.array([
    [ 0, -1,  0],
    [-1,  5, -1],
    [ 0, -1,  0],
], dtype=np.float32)


def _to_gray(frame: np.ndarray) -> np.ndarray:
    if len(frame.shape) == 3:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return frame


def _try_decode(gray: np.ndarray) -> list[str]:
    """Run the full decode pipeline on a single grayscale image."""
    # zxingcpp — most robust, handles noise and partial damage
    try:
        results = zxingcpp.read_barcodes(gray)
        if results:
            decoded = [r.text for r in results if r.text]
            if decoded:
                return decoded
    except Exception:
        pass

    # pyzbar — fast, good for clean images
    results = pyzbar_decode(gray)
    if results:
        decoded = []
        for r in results:
            try:
                text = r.data.decode("utf-8", errors="replace")
                if text:
                    decoded.append(text)
            except Exception:
                pass
        if decoded:
            return decoded

    # OpenCV QR detector
    try:
        retval, decoded_info, points, _ = _qr_detector.detectAndDecodeMulti(gray)
        if retval and decoded_info:
            return [d for d in decoded_info if d]
    except cv2.error:
        pass

    # Otsu threshold + retry (handles low contrast)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    try:
        results = zxingcpp.read_barcodes(thresh)
        if results:
            decoded = [r.text for r in results if r.text]
            if decoded:
                return decoded
    except Exception:
        pass

    results = pyzbar_decode(thresh)
    if results:
        decoded = []
        for r in results:
            try:
                text = r.data.decode("utf-8", errors="replace")
                if text:
                    decoded.append(text)
            except Exception:
                pass
        if decoded:
            return decoded

    return []


def decode_qr_fast(frame: np.ndarray) -> list[str]:
    """Decode ALL QR codes in a frame using multi-scale attempts.

    Tries at original size first (fast path), then upscales 2x and 3x
    to catch small QR codes that decoders miss at native resolution.

    Returns list of decoded strings (may be empty).
    """
    gray = _to_gray(frame)
    sharpened = cv2.filter2D(gray, -1, _sharpen_kernel)

    # 1) Try at original size (fastest)
    result = _try_decode(sharpened)
    if result:
        return result

    # 2) Try at 2x scale
    h, w = gray.shape[:2]
    up2 = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    up2 = cv2.filter2D(up2, -1, _sharpen_kernel)
    result = _try_decode(up2)
    if result:
        logger.debug("Decoded at 2x scale")
        return result

    # 3) Try at 3x scale
    up3 = cv2.resize(gray, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
    up3 = cv2.filter2D(up3, -1, _sharpen_kernel)
    result = _try_decode(up3)
    if result:
        logger.debug("Decoded at 3x scale")
        return result

    return []
