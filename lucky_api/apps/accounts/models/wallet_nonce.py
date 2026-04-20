import secrets
from django.db import models
from django.utils import timezone


class WalletNonce(models.Model):
    address = models.CharField(max_length=42, db_index=True)
    nonce = models.CharField(max_length=64, unique=True, db_index=True)
    message = models.TextField()
    issued_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issued_at"]
        indexes = [
            # Composite index: the verify view always filters on both fields
            models.Index(fields=["nonce", "address"], name="walletnonc_nonce_addr_idx"),
        ]

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @classmethod
    def generate_nonce(cls) -> str:
        return secrets.token_urlsafe(32)

    def __str__(self) -> str:
        return f"{self.address} | {self.nonce}"
