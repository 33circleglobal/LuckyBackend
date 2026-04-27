from django.urls import path

from api.games.views.webhook_up_vs_down import (
    UpVsDownRoundStartedView,
    UpVsDownRoundEndedView,
)

urlpatterns = [
    path("up-vs-down/round-start/webhook/", UpVsDownRoundStartedView.as_view()),
    path("up-vs-down/round-end/webhook/", UpVsDownRoundEndedView.as_view()),
]
