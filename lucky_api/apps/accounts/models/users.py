from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class MemberType(models.TextChoices):
        CASUAL = "casual", "Casual Player"
        VIP = "vip", "VIP Member"

    wallet_address = models.CharField(
        max_length=42,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    member_type = models.CharField(
        max_length=10, choices=MemberType.choices, default=MemberType.CASUAL
    )

    def __str__(self) -> str:
        return self.username
