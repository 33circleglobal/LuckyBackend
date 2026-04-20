from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone
from eth_account import Account
from eth_account.messages import encode_defunct
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser, WalletNonce

logger = logging.getLogger(__name__)


# ── SIWE message builder ──────────────────────────────────────────────────────


def build_siwe_message(
    *,
    domain: str,
    uri: str,
    address: str,
    statement: str,
    nonce: str,
    issued_at_iso: str,
    chain_id: int,
) -> str:
    """Build a minimal EIP-4361 compliant message string."""
    return (
        f"{domain} wants you to sign in with your Ethereum account:\n"
        f"{address}\n\n"
        f"{statement}\n\n"
        f"URI: {uri}\n"
        f"Version: 1\n"
        f"Chain ID: {chain_id}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at_iso}"
    )


# ── Nonce creation ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NonceResult:
    nonce: str
    message: str


def create_nonce(address: str) -> NonceResult:
    """
    Create (or replace) a WalletNonce for the given address.

    Old unused/unexpired nonces for the same address are invalidated first
    to prevent nonce-stuffing: an attacker cannot farm many valid nonces
    and replay them later.
    """
    ttl = int(getattr(settings, "SIWE_TTL_SECONDS", 300))
    domain = getattr(settings, "SIWE_DOMAIN", "localhost")
    uri = getattr(settings, "SIWE_URI", "http://localhost")
    statement = getattr(settings, "SIWE_STATEMENT", "Sign in")
    chain_id = int(getattr(settings, "SIWE_CHAIN_ID", 1))

    WalletNonce.objects.filter(
        address=address,
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).update(expires_at=timezone.now())

    nonce = WalletNonce.generate_nonce()
    issued_at = timezone.now()
    issued_at_iso = issued_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    message = build_siwe_message(
        domain=domain,
        uri=uri,
        address=address,
        statement=statement,
        nonce=nonce,
        issued_at_iso=issued_at_iso,
        chain_id=chain_id,
    )

    WalletNonce.objects.create(
        address=address,
        nonce=nonce,
        message=message,
        issued_at=issued_at,
        expires_at=issued_at + timezone.timedelta(seconds=ttl),
    )

    return NonceResult(nonce=nonce, message=message)


# ── Signature verification ────────────────────────────────────────────────────


class AuthError(Exception):
    """Raised for any auth failure. Message is safe to surface to the client."""


@dataclass(frozen=True)
class AuthResult:
    user: CustomUser
    access: str
    refresh: str


def verify_signature_and_issue_tokens(
    address: str,
    nonce: str,
    signature: str,
) -> AuthResult:
    """
    Full SIWE verification pipeline:
      1. Fetch the nonce record
      2. Check used / expired
      3. Recover signer from signature
      4. Match signer against claimed address
      5. Mark nonce used
      6. get_or_create the user
      7. Issue JWT pair
    Raises AuthError on any failure — callers map this to a 401.
    """
    try:
        rec = WalletNonce.objects.get(nonce=nonce, address=address)
    except WalletNonce.DoesNotExist:
        raise AuthError("Invalid nonce or address.")

    if rec.is_used:
        raise AuthError("Nonce already used.")

    if rec.is_expired:
        raise AuthError("Nonce expired.")

    # Signature recovery — eth_account raises ValueError on malformed input
    try:
        msg = encode_defunct(text=rec.message)
        recovered = Account.recover_message(msg, signature=signature)
    except Exception as exc:
        logger.warning("Signature recovery failed for address=%s: %s", address, exc)
        raise AuthError("Invalid signature.") from exc

    if recovered.lower() != address.lower():
        raise AuthError("Signature does not match address.")

    # Mark used *before* issuing tokens — prevents a tiny race window
    rec.used_at = timezone.now()
    rec.save(update_fields=["used_at"])

    user, created = CustomUser.objects.get_or_create(
        wallet_address=address,
        defaults={"username": address},
    )
    if created or not user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=["password"])

    refresh_token = RefreshToken.for_user(user)
    return AuthResult(
        user=user,
        access=str(refresh_token.access_token),
        refresh=str(refresh_token),
    )
