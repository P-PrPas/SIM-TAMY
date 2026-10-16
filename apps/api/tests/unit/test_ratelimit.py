"""T-048: the window is one atomic step, so a burst of threads cannot all slip through."""

import sys
import threading
from collections.abc import Iterator

import pytest

from app.core import ratelimit


@pytest.fixture(autouse=True)
def _fresh() -> Iterator[None]:
    ratelimit._hits.clear()
    yield
    ratelimit._hits.clear()


def test_concurrent_requests_never_exceed_the_limit() -> None:
    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)  # switch threads between nearly every bytecode
    try:
        for round_ in range(60):
            key = ("session", round_)
            barrier = threading.Barrier(8)
            allowed: list[bool] = []

            def worker(key: tuple[str, int] = key, barrier: threading.Barrier = barrier) -> None:
                barrier.wait()
                allowed.append(ratelimit.hit(key, 1)[0])

            threads = [threading.Thread(target=worker) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert allowed.count(True) == 1, f"round {round_}: {allowed.count(True)} allowed"
    finally:
        sys.setswitchinterval(old)


def test_the_window_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(ratelimit, "now", lambda: clock[0])

    assert [ratelimit.hit("k", 2)[0] for _ in range(3)] == [True, True, False]
    clock[0] = 61
    assert ratelimit.hit("k", 2) == (True, 1, 0)
