"""Isolate image bubbles from the chat area via contour detection."""

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from utils import phash

logger = logging.getLogger("scanner")


@dataclass
class ExtractedImage:
    image: np.ndarray
    x: int
    y: int
    w: int
    h: int


def extract_images(
    frame: np.ndarray,
    min_w: int = 80,
    min_h: int = 80,
) -> list[ExtractedImage]:
    """Find rectangular image-like regions in the chat frame.

    Returns a list of ExtractedImage with crop and position within the frame.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    # Dilate to close gaps in edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    results = []
    frame_h, frame_w = frame.shape[:2]

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        # Size filters
        if w < min_w or h < min_h:
            continue

        # Skip if nearly full-frame (probably background)
        if w > frame_w * 0.95 and h > frame_h * 0.95:
            continue

        # Aspect ratio filter: skip very elongated shapes (likely text)
        aspect = w / h
        if aspect > 4.0 or aspect < 0.25:
            continue

        crop = frame[y : y + h, x : x + w]
        results.append(ExtractedImage(image=crop, x=x, y=y, w=w, h=h))

    logger.info("Extracted %d candidate image regions", len(results))
    return results


def deduplicate(images: list[ExtractedImage], cache) -> list[ExtractedImage]:
    """Filter out images whose perceptual hash has been seen before."""
    unique = []
    for ei in images:
        h = phash(ei.image)
        if not cache.seen(h):
            unique.append(ei)
        else:
            logger.debug("Skipping duplicate image (hash=%s)", h)
    return unique
