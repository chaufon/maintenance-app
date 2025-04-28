from django.urls import path

from maintenance.constants import (
    API_ACTION_ADD,
    API_ACTION_DELETE,
    API_ACTION_EDIT,
    API_ACTION_EXPORT,
    API_ACTION_HISTORY,
    API_ACTION_HOME,
    API_ACTION_IMPORT,
    API_ACTION_LIST,
    API_ACTION_PARTIAL,
    API_ACTION_REACTIVATE,
    API_ACTION_READ,
)
from maintenance.views import DistritoAPIView

app_name = "distrito"

urlpatterns = [
    path("", DistritoAPIView.as_view(), name=f"{API_ACTION_HOME}"),
    path(f"{API_ACTION_ADD}/", DistritoAPIView.as_view(), name=f"{API_ACTION_ADD}"),
    path(
        f"{API_ACTION_EDIT}/<str:object_pk>/", DistritoAPIView.as_view(), name=f"{API_ACTION_EDIT}"
    ),
    path(
        f"{API_ACTION_DELETE}/<str:object_pk>/",
        DistritoAPIView.as_view(),
        name=f"{API_ACTION_DELETE}",
    ),
    path(
        f"{API_ACTION_REACTIVATE}/<str:object_pk>/",
        DistritoAPIView.as_view(),
        name=f"{API_ACTION_REACTIVATE}",
    ),
    path(f"{API_ACTION_LIST}/", DistritoAPIView.as_view(), name=f"{API_ACTION_LIST}"),
    path(f"{API_ACTION_PARTIAL}/", DistritoAPIView.as_view(), name=f"{API_ACTION_PARTIAL}"),
    path(f"{API_ACTION_IMPORT}/", DistritoAPIView.as_view(), name=f"{API_ACTION_IMPORT}"),
    path(f"{API_ACTION_EXPORT}/", DistritoAPIView.as_view(), name=f"{API_ACTION_EXPORT}"),
    path(
        f"{API_ACTION_READ}/<str:object_pk>/", DistritoAPIView.as_view(), name=f"{API_ACTION_READ}"
    ),
    path(
        f"{API_ACTION_HISTORY}/<str:object_pk>/",
        DistritoAPIView.as_view(),
        name=f"{API_ACTION_HISTORY}",
    ),
]
