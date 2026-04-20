import re

from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

ADDR_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
# Hex signature: 0x + 130 hex chars (65 bytes: r + s + v)
SIG_RE = re.compile(r"^0x[a-fA-F0-9]{130}$")


def _validate_address(value: str) -> str:
    value = value.strip()
    if not ADDR_RE.match(value):
        raise serializers.ValidationError("Invalid Ethereum address.")
    return value.lower()


class NonceRequestSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=42)

    def validate_address(self, value: str) -> str:
        return _validate_address(value)


class VerifySignatureSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=42)
    nonce = serializers.CharField(max_length=64)
    signature = serializers.RegexField(
        regex=SIG_RE,
        max_length=132,
        error_messages={
            "invalid": "Signature must be a 0x-prefixed 65-byte hex string."
        },
    )

    def validate_address(self, value: str) -> str:
        return _validate_address(value)


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=username,
            password=password,
        )

        if not user:
            raise AuthenticationFailed("Invalid username or password.")

        if not user.is_active:
            raise AuthenticationFailed("User account is disabled")

        if not user.is_staff:
            raise AuthenticationFailed("You are not authorized to access admin")

        attrs["user"] = user
        return attrs
