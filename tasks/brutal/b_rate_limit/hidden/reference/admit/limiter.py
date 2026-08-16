from __future__ import annotations


class Gate:
    def __init__(
        self,
        burst: float = 3,
        refill_per_second: float = 1.0 / 7.0,
        window_seconds: float = 45,
        window_max: int = 8,
    ) -> None:
        self.burst = burst
        self.refill_per_second = refill_per_second
        self.window_seconds = window_seconds
        self.window_max = window_max
        self._tokens = float(burst)
        self._last = 0.0
        self._hits: list[float] = []

    def allow(self, now: float) -> bool:
        elapsed = max(0.0, now - self._last)
        self._tokens = min(self.burst, self._tokens + elapsed * self.refill_per_second)
        self._last = now
        self._hits = [stamp for stamp in self._hits if now - stamp < self.window_seconds]
        if self._tokens < 1.0 or len(self._hits) >= self.window_max:
            return False
        self._tokens -= 1.0
        self._hits.append(now)
        return True
