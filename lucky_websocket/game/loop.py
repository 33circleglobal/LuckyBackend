import asyncio
import logging
import time

from config import CYCLE_DURATION_MS
from contract import helpers as contract
from django_client.poster import post_round_started, post_round_ended
from game.state import game_state
from price.buffer import price_buffer
from ws.manager import ws_manager

logger = logging.getLogger(__name__)

round_id_counter = 0


def _ms() -> int:
    return int(time.time() * 1000)


async def _sleep_until(target_ms: int):
    delay = (target_ms - _ms()) / 1000
    if delay > 0:
        await asyncio.sleep(delay)


async def game_loop():
    global round_id_counter

    logger.info("[GAME] Waiting for first price from Binance...")
    while price_buffer.latest_price is None:
        await asyncio.sleep(0.5)
    logger.info("[GAME] Price received — starting game loop")

    while True:
        now_ms = _ms()
        cycle_start = now_ms - (now_ms % CYCLE_DURATION_MS)
        t_start = cycle_start + 40_000
        t_end = cycle_start + 55_000
        t_next = cycle_start + CYCLE_DURATION_MS

        round_id_counter += 1
        current_round_id = round_id_counter

        game_state.reset_cycle(cycle_start)

        # ── 40s: start round ──
        await _sleep_until(t_start)

        start_price = price_buffer.get_at(t_start)
        game_state.set_start(start_price)

        await ws_manager.broadcast_game(
            {
                "type": "start_price",
                "price": start_price,
                "pool_id": game_state.pool_id,
            }
        )

        start_data = None
        if start_price is not None:
            start_data = await contract.start_round(start_price)
            if start_data:
                await post_round_started(current_round_id, start_data)
        else:
            logger.warning("[GAME] No start price — skipping startRound")

        # ── 55s: end round ──
        await _sleep_until(t_end)

        end_price = price_buffer.get_at(t_end)
        game_state.set_end(end_price)

        await ws_manager.broadcast_game(
            {
                "type": "end_price",
                "price": end_price,
                "pool_id": game_state.pool_id,
            }
        )

        end_data = None
        if start_price is not None and end_price is not None:
            end_data = await contract.end_round(end_price)
            if end_data:
                await post_round_ended(end_data)
        else:
            logger.warning("[GAME] Missing prices — skipping endRound")

        await ws_manager.broadcast_game(
            {
                "type": "result",
                "result": game_state.result,
                "start_price": start_price,
                "end_price": end_price,
                "pool_id": game_state.pool_id,
            }
        )

        # ── 60s: next cycle ──
        await _sleep_until(t_next)
