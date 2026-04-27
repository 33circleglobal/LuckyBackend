import hmac
import hashlib
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction

from apps.games.models import AllGameHistory, UpVsDownGameHistory
from apps.accounts.models import CustomUser

# Contract uses 18 decimal ERC20
WEI_DECIMALS = Decimal("1000000000000000000")  # 10**18

logger = logging.getLogger(__name__)


def verify_signature(body: bytes, signature: str) -> bool:
    secret = settings.DJANGO_API_SECRET.encode()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def wei_to_usdt(wei_value) -> Decimal:
    """Convert raw contract wei amount to USDT (18 decimals)."""
    return Decimal(str(wei_value)) / WEI_DECIMALS


@method_decorator(csrf_exempt, name="dispatch")
class UpVsDownRoundStartedView(View):

    def post(self, request):
        try:
            sig = request.headers.get("X-Signature", "")
            if not verify_signature(request.body, sig):
                return JsonResponse({"error": "Unauthorized"}, status=401)

            data = json.loads(request.body)
            logger.info(f"[ROUND STARTED] {data}")

            up_participants = data.get("up_participants", [])
            down_participants = data.get("down_participants", [])
            up_amounts = data.get("up_amounts", [])
            down_amounts = data.get("down_amounts", [])
            round_number = data.get("round_number")
            start_price = data.get("actual_start_price")

            if not round_number:
                return JsonResponse({"error": "Missing round_number"}, status=400)

            if len(up_participants) != len(up_amounts):
                return JsonResponse({"error": "Mismatch in up data"}, status=400)

            if len(down_participants) != len(down_amounts):
                return JsonResponse({"error": "Mismatch in down data"}, status=400)

            all_addresses = {
                addr.strip().lower()
                for addr in (up_participants + down_participants)
                if addr
            }

            users = CustomUser.objects.filter(wallet_address__in=all_addresses)
            user_map = {u.wallet_address.lower(): u for u in users}

            game_entries = []
            total_up_bet = Decimal("0")
            total_down_bet = Decimal("0")

            for addr, amt_wei in zip(up_participants, up_amounts):
                user = user_map.get(addr.strip().lower())
                if not user:
                    logger.warning(f"[ROUND STARTED] User not found: {addr}")
                    continue

                amt = wei_to_usdt(
                    amt_wei
                )  # e.g. 1000000000000000000 → 1.000000000000000000
                total_up_bet += amt

                game_entries.append(
                    UpVsDownGameHistory(
                        game_id=round_number,
                        user=user,
                        choice=UpVsDownGameHistory.GameChoice.UP,
                        game_start_price=start_price,
                        bet_amount=amt,
                    )
                )

            for addr, amt_wei in zip(down_participants, down_amounts):
                user = user_map.get(addr.strip().lower())
                if not user:
                    logger.warning(f"[ROUND STARTED] User not found: {addr}")
                    continue

                amt = wei_to_usdt(amt_wei)
                total_down_bet += amt

                game_entries.append(
                    UpVsDownGameHistory(
                        game_id=round_number,
                        user=user,
                        choice=UpVsDownGameHistory.GameChoice.DOWN,
                        game_start_price=start_price,
                        bet_amount=amt,
                    )
                )

            total_bet = total_up_bet + total_down_bet
            total_participants = len(game_entries)

            # no registered users in this round — skip DB writes entirely
            if not game_entries:
                logger.info(
                    f"[ROUND STARTED] No registered users in round {round_number}, skipping."
                )
                return JsonResponse({"status": "ok", "skipped": True})

            with transaction.atomic():
                UpVsDownGameHistory.objects.bulk_create(game_entries)

                AllGameHistory.objects.get_or_create(
                    game_id=round_number,
                    type=AllGameHistory.GameType.UP_VS_DOWN,
                    defaults={
                        "no_of_participation": total_participants,
                        "participation_on_true": len(up_participants),
                        "participation_on_false": len(down_participants),
                        "total_bet": total_bet,
                        "bet_on_true": total_up_bet,
                        "bet_on_false": total_down_bet,
                    },
                )

            return JsonResponse({"status": "ok"})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception:
            logger.exception("[ROUND STARTED] Unhandled error")
            return JsonResponse({"error": "Internal Server Error"}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class UpVsDownRoundEndedView(View):

    def post(self, request):
        try:
            sig = request.headers.get("X-Signature", "")
            if not verify_signature(request.body, sig):
                return JsonResponse({"error": "Unauthorized"}, status=401)

            data = json.loads(request.body)
            logger.info(f"[ROUND ENDED] {data}")

            winner_addresses = data.get("winner_addresses", [])
            winner_original_amounts = data.get(
                "winner_original_amounts_wei", []
            )  # original bet
            winner_total_payouts = data.get(
                "winner_total_payouts_wei", []
            )  # bet + profit
            winning_amounts = data.get("winning_amounts_wei", [])  # profit only
            round_number = data.get("round_number")
            end_price = data.get("actual_end_price")
            price_movement = data.get("price_movement")  # "UP" or "DOWN"

            total_winners = data.get("total_winners", 0)
            total_losers = data.get("total_losers", 0)
            all_distributions_complete = data.get("all_distributions_complete", False)

            if not round_number:
                return JsonResponse({"error": "Missing round_number"}, status=400)

            if len(winner_addresses) != len(winning_amounts):
                return JsonResponse({"error": "Mismatch in winner data"}, status=400)

            game_qs = UpVsDownGameHistory.objects.filter(game_id=round_number)
            if not game_qs.exists():
                return JsonResponse({"error": "Game not found"}, status=404)

            winner_addresses = [addr.strip().lower() for addr in winner_addresses]
            users = CustomUser.objects.filter(wallet_address__in=winner_addresses)
            user_map = {u.wallet_address.lower(): u for u in users}

            # ----------------------------
            # Build winners lookup by user id
            # winner_original_amounts_wei = what they bet
            # winner_total_payouts_wei    = what they receive back (bet + profit - fee)
            # winning_amounts_wei         = profit only
            # ----------------------------
            winners_map = {}
            total_winning_usdt = Decimal("0")
            total_commission = Decimal("0")

            for addr, orig_wei, payout_wei, profit_wei in zip(
                winner_addresses,
                winner_original_amounts,
                winner_total_payouts,
                winning_amounts,
            ):
                user = user_map.get(addr.strip().lower())
                if not user:
                    logger.warning(f"[ROUND ENDED] Winner not found: {addr}")
                    continue

                original_usdt = wei_to_usdt(orig_wei)  # e.g. 1.0 USDT
                payout_usdt = wei_to_usdt(payout_wei)  # e.g. 1.8 USDT (after fee)
                profit_usdt = wei_to_usdt(profit_wei)  # e.g. 0.8 USDT

                # Commission = gross_profit - net_profit
                # The contract already deducted its fee before sending payout.
                # winning_amount is net profit after fee.
                # To get commission: total loser pot - total winner net profit
                # Per winner: we store the net profit they actually received.
                pnl = profit_usdt  # net profit received
                commission = original_usdt - (payout_usdt - profit_usdt)
                # Simpler: commission is what the contract kept from the loser pot
                # We calculate total commission at the AllGameHistory level below.

                total_winning_usdt += payout_usdt

                winners_map[user.id] = {
                    "pnl": pnl,
                    "original": original_usdt,
                    "payout": payout_usdt,
                }

            # ----------------------------
            # Total commission from AllGameHistory total_bet
            # 10% of total loser pot goes to fees
            # ----------------------------
            all_game = AllGameHistory.objects.filter(
                game_id=round_number,
                type=AllGameHistory.GameType.UP_VS_DOWN,
            ).first()

            if all_game:
                total_bet = all_game.total_bet  # already in USDT
                loser_pot = (
                    all_game.bet_on_false
                    if price_movement == "UP"
                    else all_game.bet_on_true
                )
                # 10% fee taken from loser pot
                total_commission = loser_pot * Decimal("0.10")
                company_earning = total_commission * Decimal("0.50")
                team_bonus = total_commission * Decimal("0.20")
                jackpot = total_commission * Decimal("0.20")
                top_producer = total_commission * Decimal("0.05")
                satoshi = total_commission * Decimal("0.05")
            else:
                total_commission = company_earning = team_bonus = Decimal("0")
                jackpot = top_producer = satoshi = Decimal("0")

            # ----------------------------
            # Update game entries
            # ----------------------------
            with transaction.atomic():
                updated_entries = []

                for entry in game_qs.select_related("user"):
                    entry.game_end_price = end_price
                    entry.outcome = (
                        UpVsDownGameHistory.GameChoice.UP
                        if price_movement == "UP"
                        else UpVsDownGameHistory.GameChoice.DOWN
                    )

                    winner_data = winners_map.get(entry.user_id)
                    if winner_data:
                        entry.pnl = winner_data["pnl"]
                        entry.result = UpVsDownGameHistory.GameResult.WIN
                        entry.winning_commission = Decimal("0")  # fee kept by contract
                    else:
                        entry.pnl = -entry.bet_amount  # lost full bet
                        entry.result = UpVsDownGameHistory.GameResult.LOSS
                        entry.winning_commission = Decimal("0")

                    updated_entries.append(entry)

                UpVsDownGameHistory.objects.bulk_update(
                    updated_entries,
                    [
                        "pnl",
                        "result",
                        "winning_commission",
                        "game_end_price",
                        "outcome",
                    ],
                )

                AllGameHistory.objects.filter(
                    game_id=round_number,
                    type=AllGameHistory.GameType.UP_VS_DOWN,
                ).update(
                    outcome=(
                        AllGameHistory.GameResult.UP
                        if price_movement == "UP"
                        else AllGameHistory.GameResult.DOWN
                    ),
                    total_winning_amount=total_winning_usdt,
                    winning_commission=total_commission,
                    company_earning=company_earning,
                    team_winning_bonus=team_bonus,
                    jackpot_pool=jackpot,
                    top_producer_pool=top_producer,
                    satoshi_pool=satoshi,
                )

            return JsonResponse({"status": "ok"})

        except Exception:
            logger.exception("[ROUND ENDED] Unhandled error")
            return JsonResponse({"error": "Internal Server Error"}, status=500)
