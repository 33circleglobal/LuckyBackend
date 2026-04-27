import hashlib
import hmac
import json
import logging

import aiohttp

from config import DJANGO_API_URL, DJANGO_API_SECRET, POOL_ID_HEX

logger = logging.getLogger(__name__)


def _sign(payload: str) -> str:
    return hmac.new(
        DJANGO_API_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


async def _post(endpoint: str, data: dict):
    payload = json.dumps(data)
    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.post(
                f"{DJANGO_API_URL}{endpoint}",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature": _sign(payload),
                },
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if resp.status != 200:
                body = await resp.text()
                logger.error(f"[DJANGO] POST {endpoint} → {resp.status} | {body}")
            else:
                logger.info(f"[DJANGO] POST {endpoint} → 200 OK")
    except Exception as e:
        logger.error(f"[DJANGO] POST {endpoint} failed: {e}")


async def post_round_started(round_id: int, data: dict):
    await _post(
        "up-vs-down/round-start/webhook/",
        {
            "type": "round_started",
            "pool_id": POOL_ID_HEX,
            "round_id": round_id,
            "round_number": data["round_number"],
            "actual_start_price": data["actual_start_price"],
            "total_up_bets": data["total_up_bets"],
            "total_down_bets": data["total_down_bets"],
            "total_up_wager_wei": data["total_up_wager_wei"],
            "total_down_wager_wei": data["total_down_wager_wei"],
            "up_participants": data["up_participants"],
            "up_amounts": data["up_amounts"],
            "down_participants": data["down_participants"],
            "down_amounts": data["down_amounts"],
            "block": data["block"],
        },
    )


async def post_round_ended(data: dict):
    await _post(
        "up-vs-down/round-end/webhook/",
        {
            "type": "round_ended",
            "pool_id": POOL_ID_HEX,
            "round_number": data["round_number"],
            "actual_end_price": data["actual_end_price"],
            "price_movement": data["price_movement"],
            "total_winners": data["total_winners"],
            "total_losers": data["total_losers"],
            "distributions_processed": data["distributions_processed"],
            "all_distributions_complete": data["all_distributions_complete"],
            "winner_addresses": data["winner_addresses"],
            "winner_original_amounts_wei": data["winner_original_amounts_wei"],
            "winner_total_payouts_wei": data["winner_total_payouts_wei"],
            "winning_amounts_wei": data["winning_amounts_wei"],
            "block": data["block"],
        },
    )
