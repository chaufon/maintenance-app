from django import forms
from django.db.models import QuerySet
from django.forms.renderers import TemplatesSetting

from maintenance.models import Departamento, Distrito, Provincia
from maintenance.validators import is_xlsx


class FloatingFormRenderer(TemplatesSetting):
    field_template_name = "maintenance/forms/floating_field.html"


class SearchInput(forms.TextInput):
    input_type = "search"


class BootstrapFormatMixin:
    radio_template = "maintenance/forms/radio_field.html"
    file_template = "maintenance/forms/file_field.html"

    def format_fields(self, readonly: bool = False) -> None:
        for field_name in self.fields:
            field = self.fields[field_name]
            tipo = "control"

            if isinstance(field, forms.ChoiceField) or isinstance(field, forms.ModelChoiceField):
                tipo = "select"
            elif isinstance(field, forms.BooleanField):
                tipo = "check-input"
                field.template_name = self.radio_template
            elif isinstance(field, forms.FileField):
                field.template_name = self.file_template
            field.widget.attrs = {
                "class": f"form-{tipo}",
                "autocomplete": "off",
                "placeholder": field.label,
                "data-date-picker": ("true" if isinstance(field, forms.DateField) else "false"),
            }
            field.disabled = readonly
            field.label_suffix = ""

    def format_errors(self):
        for field in self.errors:
            if field != "__all__":
                self.fields[field].widget.attrs.update(
                    {"class": f"{self.fields[field].widget.attrs.get('class')} is-invalid"}
                )


class MaintenanceBaseModelForm(forms.ModelForm, BootstrapFormatMixin):
    error_css_class = "is-invalid"
    required_css_class = "fw-bolder"
    default_renderer = FloatingFormRenderer

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        readonly = kwargs.pop("readonly", False)
        super().__init__(*args, **kwargs)
        self.format_fields(readonly)


class SearchForm(forms.Form):
    param = forms.CharField(
        required=False,
        widget=SearchInput(
            attrs={
                "class": "form-control w-100",
                "hx-trigger": (
                    "input changed delay:500ms, load, ObjectEdited from:body, "
                    "ObjectAdded from:body, ObjectDeleted from:body, ObjectsImported from:body, "
                    "ObjectReactivated from:body"
                ),
                "hx-target": "#search-results",
                "hx-indicator": "#search-indicator",
                "hx-swap": "outerHTML",
                "autocomplete": "off",
                "hx-include": "#search-filters",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        placeholder = kwargs.pop("placeholder", "")
        hx_get = kwargs.pop("hx_get", "")
        _ = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["param"].widget.attrs.update({"placeholder": placeholder, "hx-get": hx_get})
        self.fields["param"].label = placeholder

    def clean_param(self):
        param = self.cleaned_data["param"]
        if param and not param.isalnum():
            raise forms.ValidationError("Solo caracteres alfanuméricos son permitidos")
        return param


class ImportForm(forms.Form, BootstrapFormatMixin):
    error_css_class = "is-invalid"
    required_css_class = "fw-bolder"
    default_renderer = FloatingFormRenderer

    file = forms.FileField(label="Archivo", required=True, validators=(is_xlsx,))

    def __init__(self, *args, **kwargs):
        _ = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.format_fields()


class DepartamentoEditForm(MaintenanceBaseModelForm):
    template_name = "maintenance/departamento/departamento_edit_form.html"

    class Meta:
        model = Departamento
        fields = ("name", "codigo")


class ProvinciaEditForm(MaintenanceBaseModelForm):
    template_name = "maintenance/provincia/provincia_edit_form.html"

    class Meta:
        model = Provincia
        fields = ("name", "codigo", "departamento")


class DistritoEditForm(MaintenanceBaseModelForm):
    template_name = "maintenance/distrito/distrito_edit_form.html"

    class Meta:
        model = Distrito
        fields = ("name", "codigo", "provincia")


class UbigeoFormMixin:
    def _get_provincia_queryset(self) -> QuerySet:
        return (
            Provincia.objects.filter(departamento_id=self.data["departamento"])
            if self.is_bound and self.data.get("departamento")
            else Provincia.objects.none()
        )

    def _get_distrito_queryset(self) -> QuerySet:
        return (
            Distrito.objects.filter(provincia_id=self.data["provincia"])
            if self.is_bound and self.data.get("provincia")
            else Distrito.objects.none()
        )


class UbigeoModelFormMixin:
    def _get_provincia_queryset(self) -> QuerySet:
        if self.is_bound and self.data.get("departamento"):
            departamento = self.data["departamento"]
        elif self.instance.pk is not None:
            departamento = self.instance.departamento_id
        else:
            return Provincia.objects.none()
        return Provincia.objects.filter(departamento_id=departamento)

    def _get_distrito_queryset(self) -> QuerySet:
        if self.is_bound and self.data.get("provincia"):
            provincia = self.data["provincia"]
        elif self.instance.pk is not None:
            provincia = self.instance.provincia_id
        else:
            return Distrito.objects.none()
        return Distrito.objects.filter(provincia_id=provincia)
