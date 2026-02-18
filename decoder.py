"""Fast QR code decoding: pyzbar first (scans full frame), OpenCV fallback."""

import logging

import cv2
import numpy as np
from pyzbar.pyzbar import decode as pyzbar_decode

logger = logging.getLogger("scanner")

_qr_detector = cv2.QRCodeDetector()

# Sharpening kernel
_sharpen_kernel = np.array([
    [ 0, -1,  0],
    [-1,  5, -1],
    [ 0, -1,  0],
], dtype=np.float32)


def _preprocess(frame: np.ndarray) -> np.ndarray:
    """Upscale small frames and sharpen for better QR detection."""
    h, w = frame.shape[:2]

    # Upscale if either dimension is small
    if h < 300 or w < 300:
        frame = cv2.resize(frame, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

    # Sharpen to recover detail from slight blur
    gray = cv2.filter2D(gray, -1, _sharpen_kernel)

    return gray


def decode_qr_fast(frame: np.ndarray) -> list[str]:
    """Decode ALL QR codes in a frame as fast as possible.

    Returns list of decoded strings (may be empty).
    """
    gray = _preprocess(frame)

    # pyzbar finds all QR/barcodes in the image at once — no extraction needed
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

    # Fallback: OpenCV QR detector
    try:
        retval, decoded_info, points, _ = _qr_detector.detectAndDecodeMulti(gray)
        if retval and decoded_info:
            return [d for d in decoded_info if d]
    except cv2.error:
        pass

    # Last resort: threshold + retry pyzbar (handles low contrast)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
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
