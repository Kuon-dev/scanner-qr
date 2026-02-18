"""Frame differencing to detect new messages in the chat area."""

import logging

import cv2
import numpy as np

logger = logging.getLogger("scanner")


class ChangeDetector:
    """Detect significant pixel changes in the chat area with stability tracking."""

    def __init__(self, threshold_pct: float = 10.0, stable_pct: float = 3.0):
        self._prev_frame: np.ndarray | None = None
        self._threshold_pct = threshold_pct
        self._stable_pct = stable_pct
        self._changing = False  # True while frames are actively changing
        self._stable_count = 0  # consecutive frames below stable_pct

    def detect(self, frame: np.ndarray) -> tuple[bool, bool]:
        """Compare the full chat frame against previous.

        Returns (changed, stable):
            changed — True if pixel diff exceeds threshold_pct
            stable  — True if frame was changing and has now settled
                      (2 consecutive frames below stable_pct)
        """
        if self._prev_frame is None or self._prev_frame.shape != frame.shape:
            self._prev_frame = frame.copy()
            return False, False

        cur = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        prev = cv2.cvtColor(self._prev_frame, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(cur, prev)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

        changed_pct = (np.count_nonzero(thresh) / thresh.size) * 100
        self._prev_frame = frame.copy()

        changed = changed_pct > self._threshold_pct
        below_stable = changed_pct < self._stable_pct

        if changed:
            logger.info("Change detected: %.1f%% pixels changed", changed_pct)
            self._changing = True
            self._stable_count = 0
            return True, False

        if self._changing and below_stable:
            self._stable_count += 1
            if self._stable_count >= 2:
                logger.info("Frame stabilized after changes")
                self._changing = False
                self._stable_count = 0
                return False, True

        return False, False

    def reset(self):
        self._prev_frame = None
        self._changing = False
        self._stable_count = 0
