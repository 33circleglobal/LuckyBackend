from django.urls import path, include

urlpatterns = [
    path("api/auth/", include("api.authentication.urls")),
    path("api/games/", include("api.games.urls")),
]
