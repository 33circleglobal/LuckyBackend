from django.db import models
from apps.accounts.models import CustomUser


class UpVsDownGameHistory(models.Model):

    class GameChoice(models.TextChoices):
        UP = "up", "Up"
        DOWN = "down", "Down"

    class GameResult(models.TextChoices):
        WIN = "win", "Win"
        LOSS = "loss", "Loss"

    game_id = models.CharField(max_length=250)

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="up_vs_down_history"
    )

    choice = models.CharField(max_length=20, choices=GameChoice.choices)
    outcome = models.CharField(
        max_length=20, choices=GameChoice.choices, null=True, blank=True
    )
    result = models.CharField(
        max_length=20, choices=GameResult.choices, null=True, blank=True
    )

    game_start_price = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    game_end_price = models.DecimalField(max_digits=19, decimal_places=4, default=0)

    bet_amount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    pnl = models.DecimalField(max_digits=19, decimal_places=4, default=0)

    winning_commission = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    company_earning = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    team_winning_bonus = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    satoshi_pool = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    top_producer_pool = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    jackpot_pool = models.DecimalField(max_digits=19, decimal_places=4, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("game_id", "user")

    def __str__(self):
        return f"{self.user} | {self.game_id} | {self.result}"
