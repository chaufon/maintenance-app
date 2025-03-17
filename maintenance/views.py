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
from django.urls import reverse
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

logger = logging.getLogger(__name__)


class MaintenanceLoginView(LoginView):
    template_name = "maintenance/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        user.clear_other_sessions()
        return super().form_valid(form)


class MaintenanceLogoutView(LogoutView):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):  # Needed to launch this custom LogoutView
        return self.post(request, *args, **kwargs)


class MaintenanceAPIView(TemplateView):
    model = None
    action = ""
    app = ""
    model_name = ""
    nombre = ""
    nombre_plural = ""
    search_formclass = SearchForm
    edit_formclass = None
    reset_formclass = None
    import_formclass = ImportForm
    order_by = ("-is_active", "name")
    search_placeholder = "Buscar por nombre"
    event_delete_error = "ObjectNotDeleted"
    events_name = {
        API_ACTION_ADD: "ObjectAdded",
        API_ACTION_DELETE: "ObjectDeleted",
        API_ACTION_EDIT: "ObjectEdited",
        API_ACTION_IMPORT: "ObjectsImported",
        API_ACTION_RESET: "PasswordUpdated",
    }
    events_msg = {
        API_ACTION_ADD: "{} creado correctamente",
        API_ACTION_DELETE: "{} eliminado correctamente",
        API_ACTION_EDIT: "{} actualizado correctamente",
        API_ACTION_IMPORT: "ObjectsImported",
        API_ACTION_RESET: "Contraseña reseteada correctamente",
    }
    field_list = {
        API_ACTION_EXPORT: ["id", "name"],
        API_ACTION_LIST: ["id", "name", "create_date", "modify_date", "is_active"],
    }
    select_related = tuple()
    title = "Project"
    event = {}
    object = None
    object_pk = None
    paginator = None
    page = 1
    objects_per_page = 20
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
        API_ACTION_RESET,
        API_ACTION_HISTORY,
        API_ACTION_COMMENT,
    )
    user = None

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        if self.user.is_superuser:
            return HttpResponseForbidden()
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

        base_url = f"{self.app}:{self.model_name}"
        self.urls = {
            API_ACTION_ADD: reverse(f"{base_url}:{API_ACTION_ADD}"),
            API_ACTION_LIST: reverse(f"{base_url}:{API_ACTION_LIST}"),
            API_ACTION_EXPORT: reverse(f"{base_url}:{API_ACTION_EXPORT}"),
            API_ACTION_IMPORT: reverse(f"{base_url}:{API_ACTION_IMPORT}"),
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
        context["user"] = self.user
        context["object"] = self.object
        if self.action == API_ACTION_LIST:
            fields_list = self.field_list[self.action]
            context["header_list"] = self.model.get_headers_list(fields_list)
            context["data_list"] = self.get_data_list(fields_list, add_obj=True)

        context.update(self.update_context())
        return self.render_to_response(context, **kwargs)

    def _render_no_html(self):
        if self.action in [API_ACTION_ADD, API_ACTION_EDIT, API_ACTION_RESET]:
            event = {
                self.events_name[self.action]: self.events_msg[self.action].format(
                    self.nombre.title()
                )
            }
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
        elif self.action == API_ACTION_EXPORT:
            return self.render_xlsx()
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
            self.event = {
                self.events_name[self.action]: self.events_msg[self.action].format(
                    self.nombre.title()
                )
            }
        return self._render_no_html()

    def form_valid_search(self, qs: QuerySet, cleaned_data: dict) -> QuerySet:
        param = cleaned_data["param"]
        qs = qs.filter(name__icontains=param) if param else qs
        return self.apply_order_by(qs)

    def get_data_list(
        self, fields_list: list, paginated: bool = True, add_obj: bool = True
    ) -> list:
        data = list()
        object_list = list()
        if paginated:
            page_obj = self.paginator.get_page(self.page) if self.paginator else None
            if page_obj:
                object_list = page_obj.object_list
        else:
            object_list = self._get_queryset()

        for obj in object_list:
            data.append(obj.get_row_data(fields_list, add_obj))
        return data

    def render_xlsx(self):
        filename = f"{self.nombre_plural}_{timezone.now().strftime(XLSX_DATETIME_FORMAT)}.xlsx"
        fields_list = self.field_list[self.action]  # API_ACTION_EXPORT
        headers_list = self.model.get_headers_list(fields_list)
        data_list = self.get_data_list(fields_list, paginated=False, add_obj=False)
        dataset = Dataset()
        dataset.headers = headers_list
        for data in data_list:
            dataset.append([i["value"].upper() for i in data])
        dataset.title = self.nombre_plural.upper()
        response = HttpResponse(dataset.xlsx, content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    def import_xlsx(self):
        msg_error = f"Error al importar {self.model_name}s"
        file_to_import = self.form.cleaned_data["file"]
        dataset = Dataset().load(file_to_import, format="xlsx")

        if not dataset.headers:
            raise ValidationError("Error con el archivo")
        clean_headers = [h for h in dataset.headers if h is not None]

        new = 0
        empty = 0
        for data in dataset.dict:
            cleaned_data = {k: v for k, v in data.items() if k in clean_headers}
            if not any(cleaned_data.values()):
                empty += 1
                continue

            try:
                self.form_valid_import(cleaned_data)
            except Exception as e:  # NOQA
                logger.error(f"{msg_error}. Error: {e}")
                continue
            else:
                new += 1

        if empty > 10:
            logger.error(f"{msg_error}. Empty lines: {empty}")

        self.event = {
            self.events_name[self.action]: (
                f"{new} {self.nombre.title() if new == 1 else self.nombre_plural.title()} "
                f"importado{'' if new == 1 else 's'} correctamente"
            )
        }
        return self._render_no_html()

    def form_valid_import(self, cleaned_data: dict) -> None:
        _ = self.model.objects.create(**cleaned_data)

    def form_valid_edit(self):
        if self.action == API_ACTION_IMPORT:
            return self.import_xlsx()
        _ = self.form.save()

    def get_modal_size(self):
        return (
            self.MODAL_SIZE_SM
            if self.action in (API_ACTION_RESET, API_ACTION_IMPORT)
            else self.MODAL_SIZE_LG
        )

    def update_context(self):
        return {}


class RelatedMaintenanceAPIView(MaintenanceAPIView):
    model = None
    parent_model = None
    parent_model_name = ""
    edit_formclass = None
    select_related = tuple()
    order_by = ("-is_active", "name")
    actions_with_perms = (
        API_ACTION_ADD,
        API_ACTION_DELETE,
        API_ACTION_EDIT,
        API_ACTION_LIST,
        API_ACTION_HISTORY,
        API_ACTION_PARTIAL,
        API_ACTION_READ,
    )
    parent_pk = None
    parent_object = None

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        if self.user.is_superuser:
            return HttpResponseForbidden()
        self.action = request.path.split("/")[5] or API_ACTION_LIST
        self.object_pk = kwargs.pop("object_pk", None)
        self.parent_pk = kwargs.pop("parent_pk", None)
        if self.parent_pk:
            try:
                self.parent_object = self.parent_model.objects.get(pk=self.parent_pk)
            except self.parent_model.ObjectDoesNotExist:
                return HttpResponseNotFound()
            else:
                if self.object_pk:
                    try:
                        self.object = self.model.todos.get(pk=self.object_pk)
                    except self.model.ObjectDoesNotExist:
                        return HttpResponseNotFound()

        self.parent_model_name = self.parent_model._meta.model_name
        self.model_name = self.model._meta.model_name

        for action in self.actions_with_perms:
            if action in (API_ACTION_ADD, API_ACTION_DELETE, API_ACTION_EDIT, API_ACTION_PARTIAL):
                perm = self.user.eval_perm(API_ACTION_EDIT, self.parent_model_name)
            elif action in (API_ACTION_LIST, API_ACTION_READ):
                perm = self.user.eval_perm(API_ACTION_LIST, self.parent_model_name)
            elif action == API_ACTION_HISTORY:
                perm = self.user.eval_perm(API_ACTION_HISTORY, self.parent_model_name)
            else:
                perm = False
            self.user_can[action] = perm

        if not self.user_can[self.action]:
            return HttpResponseForbidden()

        self.app = self.model._meta.app_label
        self.nombre = self.model._meta.verbose_name.title()
        self.nombre_plural = self.model._meta.verbose_name_plural.title()

        base_url = f"{self.app}:{self.parent_model_name}:{self.model_name}"
        self.urls = {
            API_ACTION_ADD: reverse(f"{base_url}:{API_ACTION_ADD}", args=(self.parent_pk,)),
            API_ACTION_LIST: reverse(f"{base_url}:{API_ACTION_LIST}", args=(self.parent_pk,)),
        }
        self.template_name = (
            f"{self.app}/{self.parent_model_name}/{self.model_name}/{self.action}.html"
        )
        # Default
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    def update_context(self):
        return {
            "subtitle": f"Listado de {self.nombre_plural.title()}",
            "is_related": True,
            "related_length": len(self.field_list[API_ACTION_LIST]) + 1,
        }


class DepartamentoAPIView(MaintenanceAPIView):
    model = Departamento
    edit_formclass = DepartamentoEditForm
    field_list = {
        API_ACTION_EXPORT: ["codigo", "name"],
        API_ACTION_LIST: ["codigo", "name", "create_date", "modify_date", "is_active"],
    }


class ProvinciaAPIView(MaintenanceAPIView):
    model = Provincia
    edit_formclass = ProvinciaEditForm
    select_related = ("departamento",)
    order_by = ("-is_active", "codigo")
    field_list = {
        API_ACTION_EXPORT: ["codigo", "name", "departamento"],
        API_ACTION_LIST: [
            "codigo",
            "name",
            "departamento",
            "create_date",
            "modify_date",
            "is_active",
        ],
    }


class DistritoAPIView(MaintenanceAPIView):
    model = Distrito
    edit_formclass = DistritoEditForm
    select_related = ("provincia", "provincia__departamento")
    order_by = ("-is_active", "codigo")
    field_list = {
        API_ACTION_EXPORT: ["codigo", "name", "provincia", "departamento"],
        API_ACTION_LIST: [
            "codigo",
            "name",
            "provincia",
            "departamento",
            "create_date",
            "modify_date",
            "is_active",
        ],
    }
