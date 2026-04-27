import logging
from config import POOL_ID_BYTES, PLAYING_CAPACITY
from contract.client import contract_client

logger = logging.getLogger(__name__)


def price_to_int64(price: float) -> int:
    return int(price)


async def start_round(price: float) -> dict | None:
    try:
        int_price = price_to_int64(price)
        fn = contract_client.contract.functions.startRound(POOL_ID_BYTES, int_price)
        result = await contract_client.call(fn)
        receipt = await contract_client.send(fn)

        data = {
            "success": result[0],
            "actual_start_price": result[1],
            "round_number": result[2],
            "total_up_bets": result[3],
            "total_down_bets": result[4],
            "total_up_wager_wei": result[5],
            "total_down_wager_wei": result[6],
            "up_participants": result[7],
            "up_amounts": result[8],
            "down_participants": result[9],
            "down_amounts": result[10],
            "block": receipt["blockNumber"],
        }

        logger.info(
            f"[CONTRACT] startRound | price={int_price} | "
            f"round={data['round_number']} | block={data['block']}"
        )
        return data
    except Exception as e:
        logger.error(f"[CONTRACT] startRound failed: {e}")
        return None


async def end_round(price: float) -> dict | None:
    try:
        int_price = price_to_int64(price)
        fn = contract_client.contract.functions.endRound(
            POOL_ID_BYTES, int_price, PLAYING_CAPACITY
        )
        result = await contract_client.call(fn)
        receipt = await contract_client.send(fn)

        data = {
            "success": result[0],
            "actual_end_price": result[1],
            "round_number": result[2],
            "price_movement": result[3],
            "total_winners": result[4],
            "total_losers": result[5],
            "distributions_processed": result[6],
            "all_distributions_complete": result[7],
            "winner_addresses": result[8],
            "winner_original_amounts_wei": result[9],
            "winner_total_payouts_wei": result[10],
            "winning_amounts_wei": result[11],
            "block": receipt["blockNumber"],
        }

        logger.info(
            f"[CONTRACT] endRound | price={int_price} | "
            f"round={data['round_number']} | movement={data['price_movement']} | "
            f"winners={data['total_winners']} | block={data['block']}"
        )
        return data
    except Exception as e:
        logger.error(f"[CONTRACT] endRound failed: {e}")
        return None
