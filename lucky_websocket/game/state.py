from config import POOL_ID_HEX


class GameState:
    def __init__(self):
        self.pool_id: str = POOL_ID_HEX
        self.cycle_start: int | None = None
        self.start_price: float | None = None
        self.end_price: float | None = None
        self.result: str | None = None

    def reset_cycle(self, cycle_start: int):
        self.cycle_start = cycle_start
        self.start_price = None
        self.end_price = None
        self.result = None
        # pool_id intentionally never reset

    def set_start(self, price: float):
        self.start_price = price

    def set_end(self, price: float):
        self.end_price = price
        if self.start_price is None:
            self.result = "no_result"
        elif price > self.start_price:
            self.result = "up"
        elif price < self.start_price:
            self.result = "down"
        else:
            self.result = "same"

    def to_ws2_snapshot(self) -> list[dict]:
        """Current state to send on fresh ws2 connection."""
        messages = []
        if self.start_price is not None:
            messages.append(
                {
                    "type": "start_price",
                    "price": self.start_price,
                    "pool_id": self.pool_id,
                }
            )
        if self.end_price is not None:
            messages.append(
                {"type": "end_price", "price": self.end_price, "pool_id": self.pool_id}
            )
        if self.result is not None:
            messages.append(
                {
                    "type": "result",
                    "result": self.result,
                    "start_price": self.start_price,
                    "end_price": self.end_price,
                    "pool_id": self.pool_id,
                }
            )
        return messages


# Singleton
game_state = GameState()
