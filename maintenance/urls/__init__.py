from django.urls import include, path

app_name = "common"

urlpatterns = [
    path("departamento/", include("apps.common.urls.departamento", namespace="departamento")),
    path("provincia/", include("apps.common.urls.provincia", namespace="provincia")),
    path("distrito/", include("apps.common.urls.distrito", namespace="distrito")),
]
