from django.db import models
from django.urls import reverse_lazy

import pghistory

from maintenance.constants import (
    API_ACTION_DELETE,
    API_ACTION_EDIT,
    API_ACTION_HISTORY,
    API_ACTION_PARTIAL_PLUS,
    API_ACTION_READ,
    API_ACTION_RESET,
    DATETIME_FORMAT,
    DPTO_CODIGO_CALLAO,
    DPTO_CODIGO_LIMA,
)


class ManagerOnlyActive(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class CommonModel(models.Model):
    creation_date = models.DateTimeField(
        auto_now_add=True, editable=False, verbose_name="Fecha de creación"
    )
    modify_date = models.DateTimeField(
        auto_now=True, editable=False, verbose_name="Fecha de última modificación"
    )

    class Meta:
        abstract = True

    @classmethod
    def get_name(cls):
        return cls.__name__.lower()

    @property
    def creation_date_str(self):
        return self.creation_date.strftime(DATETIME_FORMAT)


class MaintenanceMixin:
    @property
    def edit_url(self):
        return reverse_lazy(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_EDIT}", args=(self.pk,)
        )

    @property
    def delete_url(self):
        return reverse_lazy(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_DELETE}", args=(self.pk,)
        )

    @property
    def read_url(self):
        return reverse_lazy(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_READ}", args=(self.pk,)
        )

    @property
    def reset_url(self):
        return reverse_lazy(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_RESET}", args=(self.pk,)
        )

    @property
    def history_url(self):
        return reverse_lazy(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_HISTORY}", args=(self.pk,)
        )

    @property
    def partial_plus_url(self):
        return reverse_lazy(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_PARTIAL_PLUS}",
            args=(self.pk,),
        )


class BaseCatalogo(CommonModel, MaintenanceMixin):
    name = models.CharField("Nombre", max_length=250, unique=True)
    is_active = models.BooleanField("Activo", default=True)
    objects = ManagerOnlyActive()
    todos = models.Manager()

    def __str__(self):
        return f"{'' if self.is_active else 'ELIMINADO - '}{self.name}"

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)


@pghistory.track()
class Departamento(BaseCatalogo):
    name = models.CharField(max_length=250, verbose_name="Nombre")
    codigo = models.CharField(max_length=8, primary_key=True, verbose_name="Código")

    def __str__(self):
        return self.name

    @property
    def es_lima_o_callao(self):
        return self.codigo in (DPTO_CODIGO_LIMA, DPTO_CODIGO_CALLAO)


@pghistory.track()
class Provincia(BaseCatalogo):
    name = models.CharField(max_length=250, verbose_name="Nombre")
    codigo = models.CharField(max_length=8, primary_key=True, verbose_name="Código")
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


@pghistory.track()
class Distrito(BaseCatalogo):
    name = models.CharField(max_length=250, verbose_name="Nombre")
    codigo = models.CharField(max_length=8, primary_key=True, verbose_name="Código")
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE)

    def __str__(self):
        return self.name
