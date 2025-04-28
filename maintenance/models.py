from django.db import models
from django.urls import reverse

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


class BaseModel(models.Model):
    DELETED_TEXT = "ELIMINADO"
    create_date = models.DateTimeField(
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
    def create_date_str(self):
        return self.create_date.strftime(DATETIME_FORMAT)

    @property
    def modify_date_str(self):
        return self.modify_date.strftime(DATETIME_FORMAT)


class MaintenanceMixin:
    @property
    def edit_url(self):
        return reverse(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_EDIT}", args=(self.pk,)
        )

    @property
    def delete_url(self):
        return reverse(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_DELETE}", args=(self.pk,)
        )

    @property
    def read_url(self):
        return reverse(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_READ}", args=(self.pk,)
        )

    @property
    def reset_url(self):
        return reverse(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_RESET}", args=(self.pk,)
        )

    @property
    def history_url(self):
        return reverse(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_HISTORY}", args=(self.pk,)
        )

    @property
    def partial_plus_url(self):
        return reverse(
            f"{self._meta.app_label}:{self._meta.model_name}:{API_ACTION_PARTIAL_PLUS}",
            args=(self.pk,),
        )

    @classmethod
    def get_headers_list(cls, fields_list: list) -> list:
        headers = list()
        for field_name in fields_list:
            try:
                headers.append(cls._meta.get_field(field_name).verbose_name.title())
            except Exception:  # NOQA
                headers.append(field_name.title())
        return headers

    def get_row_data(self, fields_list: tuple) -> dict:
        data = list()
        for field_name in fields_list:
            field_str = getattr(self, field_name + "_str", None)
            data.append(
                {
                    "value": str(field_str if field_str else getattr(self, field_name, "")),
                    "class": "",  # TODO
                }
            )
        return {"object": self, "data": data}


class BaseCatalogo(BaseModel, MaintenanceMixin):
    name = models.CharField("Nombre", max_length=250, unique=True)
    is_active = models.BooleanField("Activo", default=True)
    objects = ManagerOnlyActive()
    todos = models.Manager()

    def __str__(self):
        return f"{'' if self.is_active else self.DELETED_TEXT + ' - '}{self.name}"

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_active = False
        return self.save(*args, **kwargs)

    def reactivate(self, *args, **kwargs):
        self.is_active = True
        return self.save(*args, **kwargs)


@pghistory.track()
class Departamento(BaseCatalogo):
    name = models.CharField(max_length=250, verbose_name="Nombre")  # not unique
    codigo = models.CharField(max_length=8, primary_key=True, verbose_name="Código")

    def save(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)

    @property
    def es_lima_o_callao(self):
        return self.codigo in (DPTO_CODIGO_LIMA, DPTO_CODIGO_CALLAO)


@pghistory.track()
class Provincia(BaseCatalogo):
    name = models.CharField(max_length=250, verbose_name="Nombre")  # not unique
    codigo = models.CharField(max_length=8, primary_key=True, verbose_name="Código")
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)


@pghistory.track()
class Distrito(BaseCatalogo):
    name = models.CharField(max_length=250, verbose_name="Nombre")  # not unique
    codigo = models.CharField(max_length=8, primary_key=True, verbose_name="Código")
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)

    @property
    def departamento_str(self):
        return self.provincia.departamento
