"""Sliding-window rate limit, in process (T-048, API_DESIGN 8): N requests per minute per key."""

import time
from collections import deque
from collections.abc import Hashable

WINDOW_S = 60.0
_MAX_KEYS = 10_000
_hits: dict[Hashable, deque[float]] = {}
now = time.monotonic  # tests replace it


def hit(key: Hashable, limit: int) -> tuple[bool, int, int]:
    """Count one request: (allowed, remaining, retry_after_s). A refused one is not counted."""
    t = now()
    if len(_hits) > _MAX_KEYS:  # ponytail: one instance; a shared store (Redis) if we scale out
        for k in [k for k, q in _hits.items() if not q or q[-1] <= t - WINDOW_S]:
            del _hits[k]
    window = _hits.setdefault(key, deque())
    while window and window[0] <= t - WINDOW_S:
        window.popleft()
    if len(window) >= limit:
        return False, 0, max(1, int(window[0] + WINDOW_S - t) + 1)
    window.append(t)
    return True, limit - len(window), 0
