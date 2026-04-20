from django.urls import path
from api.authentication.views.auth import (
    RequestNonceView,
    VerifySignatureView,
    AdminLoginAPIView,
)

urlpatterns = [
    path("nonce/", RequestNonceView.as_view(), name="auth-nonce"),
    path("verify/", VerifySignatureView.as_view(), name="auth-verify"),
    path(
        "admin/login/",
        AdminLoginAPIView.as_view(),
        name="auth-admin-login",
    ),
]
