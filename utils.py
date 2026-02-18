"""Shared helpers: perceptual hashing, rolling cache, config, logging."""

import json
import time
import logging
from pathlib import Path
from collections import OrderedDict

import numpy as np
import imagehash
from PIL import Image

logger = logging.getLogger("scanner")

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def phash(image: np.ndarray) -> str:
    """Compute perceptual hash of a numpy BGR image."""
    pil = Image.fromarray(image[..., ::-1])  # BGR → RGB
    return str(imagehash.phash(pil))


class RollingHashCache:
    """Dedup cache with max size and TTL expiry."""

    def __init__(self, max_entries: int = 500, ttl_s: int = 3600):
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._max = max_entries
        self._ttl = ttl_s

    def seen(self, h: str) -> bool:
        """Return True if hash was already seen (and still fresh)."""
        self._evict()
        if h in self._cache:
            return True
        self._cache[h] = time.time()
        if len(self._cache) > self._max:
            self._cache.popitem(last=False)
        return False

    def _evict(self):
        cutoff = time.time() - self._ttl
        while self._cache:
            key, ts = next(iter(self._cache.items()))
            if ts < cutoff:
                self._cache.popitem(last=False)
            else:
                break


class JsonLinesLogger:
    """Append structured JSON lines to a log file."""

    def __init__(self, path: str):
        self._path = Path(path)

    def log(self, event: str, **data):
        entry = {"ts": time.time(), "event": event, **data}
        with open(self._path, "a") as f:
            f.write(json.dumps(entry) + "\n")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
