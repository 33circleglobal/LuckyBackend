import logging

from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework import generics, status
from rest_framework_simplejwt.tokens import RefreshToken

from api.authentication.serializers.auth import (
    NonceRequestSerializer,
    VerifySignatureSerializer,
    AdminLoginSerializer,
)
from api.authentication.serializers.users import (
    AdminUserSerializer,
    CustomUserSerializer,
)
from api.authentication.services.siwe import (
    AuthError,
    create_nonce,
    verify_signature_and_issue_tokens,
)
from api.utils.custom_response import (
    failed_response,
    success_response,
    validation_failed_response,
)

logger = logging.getLogger(__name__)


class RequestNonceView(APIView):
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "custom"

    def post(self, request):
        try:
            serializer = NonceRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            address = serializer.validated_data["address"]

            result = create_nonce(address)

            return success_response(
                message="Nonce generated.",
                data={
                    "nonce": result.nonce,
                    "message": result.message,
                },
            )

        except ValidationError as e:
            return validation_failed_response(e)

        except Exception as e:
            logger.exception("Nonce generation failed: %s", str(e))
            return failed_response("Something went wrong. Please try again.")


class VerifySignatureView(APIView):
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "custom"

    def post(self, request):
        try:
            serializer = VerifySignatureSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            vd = serializer.validated_data

            result = verify_signature_and_issue_tokens(
                address=vd["address"],
                nonce=vd["nonce"],
                signature=vd["signature"],
            )

            return success_response(
                message="Authenticated.",
                data={
                    "user": CustomUserSerializer(result.user).data,
                    "access": result.access,
                    "refresh": result.refresh,
                },
            )

        except ValidationError as e:
            return validation_failed_response(e)

        except AuthError as exc:
            logger.info(
                "Auth failure address=%s reason=%s",
                request.data.get("address"),
                str(exc),
            )
            return failed_response(message=str(exc))

        except Exception as e:
            logger.exception("Signature verification failed: %s", str(e))
            return failed_response("Authentication failed. Please try again.")


class AdminLoginAPIView(generics.GenericAPIView):
    serializer_class = AdminLoginSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = serializer.validated_data["user"]

            tokens = RefreshToken.for_user(user)

            return success_response(
                message="Login successful",
                data={
                    "user": AdminUserSerializer(user).data,
                    "refresh": str(tokens),
                    "access": str(tokens.access_token),
                },
                status_code=status.HTTP_200_OK,
            )

        except AuthenticationFailed as e:
            return failed_response(
                message=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        except ValidationError as e:
            return validation_failed_response(error=e)

        except Exception as e:
            logger.exception("Unexpected error during login: %s", str(e))
            return failed_response(
                message="An unexpected error occurred. Please try again later.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
