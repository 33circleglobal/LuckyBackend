from django.contrib import admin
from apps.games.models import AllGameHistory, UpVsDownGameHistory

# Register your models here.


@admin.register(AllGameHistory)
class AdminAllGameHistory(admin.ModelAdmin):
    list_display = [
        "game_id",
        "type",
        "no_of_participation",
        "participation_on_true",
        "participation_on_false",
        "total_bet",
        "winning_commission",
        "company_earning",
        "team_winning_bonus",
        "satoshi_pool",
        "top_producer_pool",
        "jackpot_pool",
        "created_at",
        "updated_at",
    ]


@admin.register(UpVsDownGameHistory)
class AdminUpVsDownGameHistory(admin.ModelAdmin):
    list_display = [
        "game_id",
        "user",
        "game_start_price",
        "game_end_price",
        "choice",
        "outcome",
        "result",
        "pnl",
    ]
