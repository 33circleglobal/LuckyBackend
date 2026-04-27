import asyncio
import json
import logging
import time
import websockets
from config import BINANCE_WS_URL, PRICE_BROADCAST_INTERVAL_MS
from price.buffer import price_buffer
from ws.manager import ws_manager

logger = logging.getLogger(__name__)


async def binance_listener():
    reconnect_delay = 1
    max_delay = 60

    while True:
        try:
            logger.info(f"[BINANCE] Connecting to {BINANCE_WS_URL}")
            async with websockets.connect(
                BINANCE_WS_URL,
                ping_interval=180,
                ping_timeout=600,
                close_timeout=10,
            ) as ws:
                logger.info("[BINANCE] Connected")
                reconnect_delay = 1
                connection_start = time.time()

                async for message in ws:
                    if time.time() - connection_start > 23.5 * 3600:
                        logger.info("[BINANCE] Approaching 24h limit, reconnecting")
                        break
                    try:
                        data = json.loads(message)
                        price_buffer.push(int(data["T"]), float(data["p"]))
                    except Exception as e:
                        logger.warning(f"[BINANCE] Message parse error: {e}")

        except Exception as e:
            logger.error(f"[BINANCE] Connection error: {e}")

        logger.info(f"[BINANCE] Reconnecting in {reconnect_delay}s")
        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, max_delay)


async def price_broadcaster():
    from game.state import game_state

    while True:
        start = time.time()
        price = price_buffer.latest_price

        if price is not None:
            import time as t

            await ws_manager.broadcast_price(
                {
                    "price": price,
                    "timestamp": int(t.time() * 1000),
                    "pool_id": game_state.pool_id,
                }
            )

        elapsed_ms = (time.time() - start) * 1000
        await asyncio.sleep(max(0, (PRICE_BROADCAST_INTERVAL_MS - elapsed_ms) / 1000))
