import json
import logging

from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
)
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from tablib import Dataset

from maintenance.constants import (
    API_ACTION_ADD,
    API_ACTION_COMMENT,
    API_ACTION_DELETE,
    API_ACTION_EDIT,
    API_ACTION_EXPORT,
    API_ACTION_HISTORY,
    API_ACTION_HOME,
    API_ACTION_IMPORT,
    API_ACTION_IMPORT_DEMO,
    API_ACTION_LIST,
    API_ACTION_MODAL_TITLE,
    API_ACTION_PARTIAL,
    API_ACTION_PARTIAL_PLUS,
    API_ACTION_PARTIAL_SEARCH,
    API_ACTION_READ,
    API_ACTION_RESET,
    MENU_MANTENIMIENTOS,
    XLSX_CONTENT_TYPE,
    XLSX_DATETIME_FORMAT,
)
from maintenance.forms import (
    DepartamentoEditForm,
    DistritoEditForm,
    ImportForm,
    ProvinciaEditForm,
    SearchForm,
)
from maintenance.history import HistoryList
from maintenance.models import Departamento, Distrito, Provincia
from maintenance.resources import DepartamentoResource, DistritoResource, ProvinciaResource

logger = logging.getLogger(__name__)


class MaintenanceLoginView(LoginView):
    template_name = "maintenance/common/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        user.clear_other_sessions()
        return super().form_valid(form)

    def get_success_url(self):
        user = self.request.user
        if user.es_root or (not user.can_list_venta and not user.es_op_invitado):
            return reverse("users:user:home")
        else:
            app = "renovacion" if user.es_renovacion else "portabilidad"
            model = "reporte" if user.es_op_invitado else "venta"
            return reverse(f"{app}:{model}:home")


class MaintenanceLogoutView(LogoutView):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):  # Needed to launch our own LogoutView
        return self.post(request, *args, **kwargs)


class MaintenanceAPIView(TemplateView):
    model = None
    app = ""
    model_name = ""
    search_formclass = SearchForm
    resource = None
    resource_demo = None
    edit_formclass = None
    reset_formclass = None
    import_formclass = ImportForm
    order_by = ("-is_active", "name")
    search_placeholder = "Buscar por nombre"
    event_deleted = "ObjectDeleted"
    event_added = "ObjectAdded"
    event_edited = "ObjectEdited"
    event_delete_error = "ObjectNotDeleted"
    event_reset = "PasswordUpdated"
    event_imported = "ObjectsImported"
    select_related = tuple()
    title = "Partner"
    event = {}
    action = ""
    object = None
    object_pk = None
    paginator = None
    page = 1
    objects_per_page = 20
    nombre = ""
    nombre_plural = ""
    form = None
    user_can = dict()
    urls = dict()
    menu_active = MENU_MANTENIMIENTOS
    MODAL_SIZE_SM = "modal-sm"
    MODAL_SIZE_LG = "modal-lg"
    MODAL_SIZE_XL = "modal-xl"
    actions_with_perms = (
        API_ACTION_ADD,
        API_ACTION_DELETE,
        API_ACTION_EDIT,
        API_ACTION_LIST,
        API_ACTION_EXPORT,
        API_ACTION_IMPORT,
        API_ACTION_IMPORT_DEMO,
        API_ACTION_RESET,
        API_ACTION_HISTORY,
        API_ACTION_COMMENT,
    )
    user = None
    rol = None

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.rol = self.user.rol
        self.action = request.path.split("/")[3] or API_ACTION_HOME
        self.object_pk = kwargs.pop("object_pk", None)
        if self.object_pk:
            try:
                self.object = self.model.todos.select_related(*self.get_select_related()).get(
                    pk=self.object_pk
                )
            except self.model.ObjectDoesNotExist:
                return HttpResponseNotFound()
        self.page = self.request.GET.get("page", 1)
        self.model_name = self.model._meta.model_name
        if not self.user.eval_perm(self.action, self.model_name, self.object):
            return HttpResponseForbidden()
        self.user_can = {  # TODO remove
            action: self.user.eval_perm(action, self.model_name)
            for action in self.actions_with_perms
        }
        self.app = self.model._meta.app_label
        self.nombre = self.model._meta.verbose_name.title()
        self.nombre_plural = self.model._meta.verbose_name_plural.title()
        self.urls = {
            API_ACTION_ADD: reverse_lazy(f"{self.app}:{self.model_name}:{API_ACTION_ADD}"),
            API_ACTION_LIST: reverse_lazy(f"{self.app}:{self.model_name}:{API_ACTION_LIST}"),
            API_ACTION_EXPORT: reverse_lazy(f"{self.app}:{self.model_name}:{API_ACTION_EXPORT}"),
            API_ACTION_IMPORT: reverse_lazy(f"{self.app}:{self.model_name}:{API_ACTION_IMPORT}"),
        }
        self.template_name = f"{self.app}/{self.model_name}/{self.action}.html"
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict:
        kwargs = {"user": self.user}
        if self.action == API_ACTION_PARTIAL_SEARCH:
            kwargs.update({"hx_get": self.urls.get(API_ACTION_LIST)})
        elif self.action in (API_ACTION_LIST, API_ACTION_HOME):
            kwargs.update(
                {"placeholder": self.search_placeholder, "hx_get": self.urls.get(API_ACTION_LIST)}
            )
        elif self.action == API_ACTION_READ:
            kwargs.update({"readonly": True})
        return kwargs

    def apply_order_by(self, qs: QuerySet) -> QuerySet:
        return qs.order_by(*self.order_by) if self.order_by else qs

    def get_select_related(self) -> tuple:
        return self.select_related or tuple()

    def _get_queryset(self):
        self.form = self.search_formclass(self.request.GET, **self.get_form_kwargs())
        if self.form.is_valid():
            qs = self.form_valid_search(
                self.model.todos.select_related(*self.get_select_related()), self.form.cleaned_data
            )
            return self.apply_order_by(qs)
        return self.model.objects.none()

    def _render_html(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subtitle = f"Mantenimiento de {self.nombre_plural.title()}"
        context["title"] = f"{self.title} | {subtitle}"
        context["subtitle"] = subtitle
        context["menu_active"] = self.menu_active
        context["form"] = self.form
        context["page_obj"] = self.paginator.get_page(self.page) if self.paginator else None
        context["pages"] = self.paginator.get_elided_page_range(self.page) if self.paginator else ()
        context["list_template"] = f"{self.app}/{self.model_name}/{API_ACTION_LIST}.html"
        context["nombre"] = self.nombre.title()
        context["modal_title"] = f"{API_ACTION_MODAL_TITLE.get(self.action)} {self.nombre.title()}"
        context["modal_size"] = self.get_modal_size()
        context["modal_is_import"] = self.action == API_ACTION_IMPORT
        context["modal_readonly"] = self.action in (API_ACTION_READ, API_ACTION_HISTORY)
        context["user_can"] = self.user_can
        context["urls"] = self.urls
        context["rol"] = self.rol
        context["user"] = self.user
        context["object"] = self.object
        context.update(self.update_context())
        return self.render_to_response(context, **kwargs)

    def _render_no_html(self):
        if self.action == API_ACTION_ADD:
            event = {self.event_added: f"{self.nombre.title()} creado correctamente"}
        elif self.action == API_ACTION_EDIT:
            event = {self.event_edited: f"{self.nombre.title()} actualizado correctamente"}
        elif self.action == API_ACTION_RESET:
            event = {self.event_reset: "Contraseña reseteada correctamente"}
        else:
            event = self.event
        return HttpResponse(status=204, headers={"HX-Trigger": json.dumps(event)})

    def get(self, request, *args, **kwargs):
        if self.action == API_ACTION_HOME:
            self.form = self.search_formclass(**self.get_form_kwargs())
        elif self.action == API_ACTION_PARTIAL_SEARCH:
            kwargs.update(
                {"headers": {"HX-Trigger": "ForceSearch"}}
            )  # only for venta supervisor filter
            self.form = self.search_formclass(request.GET, **self.get_form_kwargs())
        elif self.action == API_ACTION_LIST:
            self.paginator = Paginator(self._get_queryset(), self.objects_per_page)
        elif self.action == API_ACTION_READ:
            self.form = self.edit_formclass(instance=self.object, **self.get_form_kwargs())
        elif self.action in (API_ACTION_PARTIAL, API_ACTION_PARTIAL_PLUS):
            self.form = self.edit_formclass(
                request.GET, instance=self.object, **self.get_form_kwargs()
            )
        elif self.action == API_ACTION_IMPORT_DEMO:
            return self._render_xlsx(demo=True)
        elif self.action == API_ACTION_EXPORT:
            return self._render_xlsx()
        elif self.action == API_ACTION_HISTORY:
            self.form = HistoryList(self.object).get_accordion()
        elif self.action == API_ACTION_IMPORT:
            self.form = self.import_formclass(**self.get_form_kwargs())
        elif self.action == API_ACTION_RESET:
            self.form = self.reset_formclass(**self.get_form_kwargs())
        else:
            self.form = self.edit_formclass(instance=self.object, **self.get_form_kwargs())
        return self._render_html(**kwargs)

    def post(self, request, *args, **kwargs):
        if self.action in (API_ACTION_ADD, API_ACTION_EDIT):
            self.form = self.edit_formclass(
                request.POST, instance=self.object, **self.get_form_kwargs()
            )
        elif self.action == API_ACTION_RESET:
            self.form = self.reset_formclass(
                request.POST, instance=self.object, **self.get_form_kwargs()
            )
        elif self.action == API_ACTION_IMPORT:
            self.form = self.import_formclass(request.POST, request.FILES, **self.get_form_kwargs())
        else:
            return HttpResponseNotAllowed(permitted_methods=["get"])

        if self.form.is_valid():
            self.form_valid_edit()
            return self._render_no_html()
        else:
            self.form.format_errors()
            return self._render_html(**kwargs)

    def delete(self, request, *args, **kwargs):
        if self.action != API_ACTION_DELETE:
            return HttpResponseNotAllowed(permitted_methods=["get"])
        try:
            self.object.delete()
        except ValidationError as e:
            self.event = {self.event_delete_error: str(e.message)}
        else:
            self.event = {self.event_deleted: f"{self.nombre.title()} eliminado correctamente"}
        return self._render_no_html()

    def form_valid_search(self, qs: QuerySet, cleaned_data: dict) -> QuerySet:
        param = cleaned_data["param"]
        qs = qs.filter(name__icontains=param) if param else qs
        return self.apply_order_by(qs)

    def _render_xlsx(self, demo: bool = False):
        if demo:
            self.resource = self.resource_demo or self.resource
        filename = f"{self.nombre_plural}_{timezone.now().strftime(XLSX_DATETIME_FORMAT)}.xlsx"
        dataset = self.resource().export(
            queryset=self.model.objects.none() if demo else self._get_queryset()
        )
        dataset.title = self.nombre_plural.upper()
        response = HttpResponse(dataset.xlsx, content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    def _import_xlsx(self):
        msg_error = f"Error al importar {self.model_name}s"
        if self.user.es_root:
            raise ValidationError("Root no puede importar usuarios")

        file_to_import = self.form.cleaned_data["file"]
        dataset = Dataset().load(file_to_import, format="xlsx")

        if not dataset.headers:
            raise ValidationError("Error con el archivo")
        clean_headers = [h for h in dataset.headers if h is not None]

        new = 0
        empty = 0
        for data in dataset.dict:
            clean_data = {k: v for k, v in data.items() if k in clean_headers}
            if not any(clean_data.values()):
                empty += 1
                continue

            try:
                _ = self.model.objects.create(**clean_data)
            except Exception as e:  # NOQA
                logger.error(f"{msg_error}. Error: {e}")
                continue
            else:
                new += 1

        if empty > 10:
            logger.error(f"{msg_error}. Empty lines: {empty}")

        self.event = {
            self.event_imported: (
                f"{new} {self.nombre.title() if new == 1 else self.nombre_plural.title()} "
                f"importado{'' if new == 1 else 's'} correctamente"
            )
        }
        return self._render_no_html()

    def _import_xlsx_antiguo(self):
        file_to_import = self.form.cleaned_data["file"]
        ds = Dataset().load(file_to_import.read())
        self.resource = self.resource_demo or self.resource  # TODO
        resource = self.resource()
        result = resource.import_data(ds, dry_run=True)
        if result.has_errors():
            self.form.add_error(
                None,
                "Importación interrumpida. Se encontraron errores con la data del archivo subido",
            )
            return self._render_html()
        result = resource.import_data(ds, dry_run=False)
        new = result.totals["new"]
        self.event = {
            self.event_imported: (
                f"{new} {self.nombre.title() if new == 1 else self.nombre_plural.title()} "
                f"importado{'' if new == 1 else 's'} correctamente"
            )
        }
        return self._render_no_html()

    def form_valid_edit(self):
        if self.action == API_ACTION_IMPORT:
            return self._import_xlsx()
        _ = self.form.save()

    def get_modal_size(self):
        return (
            self.MODAL_SIZE_SM
            if self.action in (API_ACTION_RESET, API_ACTION_IMPORT)
            else self.MODAL_SIZE_LG
        )

    def update_context(self):
        return {}


class DepartamentoAPIView(MaintenanceAPIView):
    model = Departamento
    resource = DepartamentoResource
    edit_formclass = DepartamentoEditForm
    order_by = ("pk",)


class ProvinciaAPIView(MaintenanceAPIView):
    model = Provincia
    resource = ProvinciaResource
    edit_formclass = ProvinciaEditForm
    order_by = ("pk",)
    select_related = ("departamento",)


class DistritoAPIView(MaintenanceAPIView):
    model = Distrito
    resource = DistritoResource
    edit_formclass = DistritoEditForm
    order_by = ("pk",)
    select_related = ("provincia", "provincia__departamento")
