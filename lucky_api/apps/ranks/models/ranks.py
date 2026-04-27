from django.db import models

from apps.accounts.models import CustomUser


class LuckyRank(models.Model):
    class RankChoice(models.TextChoices):

        ROOKIE = "rookie", "Rookie"
        RANGER = "ranger", "Ranger"
        GUARDIAN = "guardian", "Guardian"
        VANGUARD = "vanguard", "Vanguard"
        COMMANDER = "commander", "Commander"
        EMPEROR = "emperor", "Emperor"

    image = models.ImageField(
        upload_to="uploads/ranks/%Y/%m/%d/", null=True, blank=True
    )
    name = models.CharField(
        max_length=25, choices=RankChoice.choices, default=RankChoice.ROOKIE
    )
