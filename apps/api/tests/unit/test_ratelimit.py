"""T-048: the window is one atomic step, so a burst of threads cannot all slip through."""

import threading
import time
from collections import deque
from collections.abc import Iterator

import pytest

from app.core import ratelimit


class SlowAppend(deque[float]):
    """Widens the gap between 'is there room?' and 'take it', where an unlocked check races."""

    def append(self, x: float) -> None:
        time.sleep(0.005)
        super().append(x)


@pytest.fixture(autouse=True)
def _fresh() -> Iterator[None]:
    ratelimit._hits.clear()
    yield
    ratelimit._hits.clear()


def test_concurrent_requests_never_exceed_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ratelimit, "deque", SlowAppend)
    barrier = threading.Barrier(8)
    allowed: list[bool] = []

    def worker() -> None:
        barrier.wait()
        allowed.append(ratelimit.hit("session", 1)[0])

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert allowed.count(True) == 1


def test_the_window_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(ratelimit, "now", lambda: clock[0])

    assert [ratelimit.hit("k", 2)[0] for _ in range(3)] == [True, True, False]
    clock[0] = 61
    assert ratelimit.hit("k", 2) == (True, 1, 0)
