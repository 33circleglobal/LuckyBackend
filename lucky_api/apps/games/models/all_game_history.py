from django.db import models

from apps.accounts.models import CustomUser


class AllGameHistory(models.Model):
    class GameType(models.TextChoices):
        UP_VS_DOWN = "up_vs_down", "Up vs Down"

    class GameResult(models.TextChoices):
        UP = "up", "Up"
        DOWN = "down", "Down"

    game_id = models.CharField(max_length=250)
    type = models.CharField(max_length=50, choices=GameType.choices)
    outcome = models.CharField(
        max_length=20, choices=GameResult.choices, null=True, blank=True
    )
    no_of_participation = models.PositiveBigIntegerField(default=0)
    participation_on_true = models.PositiveBigIntegerField(default=0)
    participation_on_false = models.PositiveBigIntegerField(default=0)
    total_bet = models.DecimalField(decimal_places=4, max_digits=19, default=0)
    bet_on_true = models.DecimalField(decimal_places=4, max_digits=19, default=0)
    bet_on_false = models.DecimalField(decimal_places=4, max_digits=19, default=0)
    total_winning_amount = models.DecimalField(
        decimal_places=4, max_digits=19, default=0
    )
    winning_commission = models.DecimalField(decimal_places=4, max_digits=19, default=0)
    company_earning = models.DecimalField(decimal_places=4, max_digits=19, default=0)
    team_winning_bonus = models.DecimalField(decimal_places=4, max_digits=19, default=0)
    satoshi_pool = models.DecimalField(decimal_places=4, max_digits=19, default=0)
    top_producer_pool = models.DecimalField(decimal_places=4, max_digits=19, default=0)
    jackpot_pool = models.DecimalField(decimal_places=4, max_digits=19, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game_id", "type"], name="unique_game_per_type"
            )
        ]
