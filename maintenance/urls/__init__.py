from django.urls import include, path

app_name = "ubigeo"

urlpatterns = [
    path("departamento/", include("maintenance.urls.departamento", namespace="departamento")),
    path("provincia/", include("maintenance.urls.provincia", namespace="provincia")),
    path("distrito/", include("maintenance.urls.distrito", namespace="distrito")),
]
