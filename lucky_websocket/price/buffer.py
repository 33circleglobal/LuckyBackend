from typing import Optional
from config import MAX_PRICE_BUFFER


class PriceBuffer:
    def __init__(self):
        self._buffer: list[tuple[int, float]] = []

    def push(self, timestamp_ms: int, price: float):
        self._buffer.append((timestamp_ms, price))
        if len(self._buffer) > MAX_PRICE_BUFFER:
            self._buffer.pop(0)

    def get_at(self, target_ts: int) -> Optional[float]:
        if not self._buffer:
            return None
        return min(self._buffer, key=lambda x: abs(x[0] - target_ts))[1]

    def snapshot(self) -> list[tuple[int, float]]:
        return list(self._buffer)

    @property
    def latest_price(self) -> Optional[float]:
        return self._buffer[-1][1] if self._buffer else None


# Singleton
price_buffer = PriceBuffer()
