import json
import logging

from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import QuerySet
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from tablib import Dataset

from maintenance.constants import (
    API_ACTION_ADD,
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
    API_ACTION_REACTIVATE,
    API_ACTION_READ,
    API_ACTION_RESET,
    CONTENT_TYPE_XLSX,
    MENU_MANTENIMIENTOS,
    RELATED_NAME,
    RELATED_TAG,
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
from maintenance.utils import validar_si_bool

logger = logging.getLogger(__name__)


class WebEvents:
    events_name = {
        API_ACTION_ADD: "ObjectAdded",
        API_ACTION_DELETE: "ObjectDeleted",
        API_ACTION_REACTIVATE: "ObjectReactivated",
        API_ACTION_EDIT: "ObjectEdited",
        API_ACTION_IMPORT: "ObjectsImported",
        API_ACTION_RESET: "PasswordUpdated",
    }
    events_msg = {
        API_ACTION_ADD: "{} creado correctamente",
        API_ACTION_DELETE: "{} eliminado correctamente",
        API_ACTION_REACTIVATE: "{} reactivado correctamente",
        API_ACTION_EDIT: "{} actualizado correctamente",
        API_ACTION_IMPORT: "Importación correcta. {}",
        API_ACTION_RESET: "Contraseña reseteada correctamente",
    }
    events_fail_name = {
        API_ACTION_ADD: "ObjectAddedFail",
        API_ACTION_DELETE: "ObjectDeletedFail",
        API_ACTION_REACTIVATE: "ObjectReactivatedFail",
        API_ACTION_EDIT: "ObjectEditedFail",
        API_ACTION_IMPORT: "ObjectsImportedFail",
        API_ACTION_RESET: "PasswordUpdatedFail",
    }
    events_fail_msg = {
        API_ACTION_ADD: "Se encontraron errores. {}",
        API_ACTION_DELETE: "No se pudo eliminar. {}",
        API_ACTION_REACTIVATE: "No se pudo reactivar {}",
        API_ACTION_EDIT: "Se encontraron errores. {}",
        API_ACTION_IMPORT: "Se encontraron errores. {}",
        API_ACTION_RESET: "No se actualizó contraseña",
    }
    related = False

    def __init__(self, action: str, related: bool = False):
        self.action = action
        self.related = related
        if self.related:
            for k, v in self.events_name.items():
                if not v.endswith(RELATED_NAME):  # TODO to avoid multiple adding, why?
                    self.events_name[k] = f"{v}{RELATED_NAME}"
                    self.events_fail_name[k] = f"{v}Fail{RELATED_NAME}"

    def get_name(self):
        return self.events_name.get(self.action)

    def get_msg(self):
        return self.events_msg.get(self.action)

    def get_fail_name(self):
        return self.events_fail_name.get(self.action)

    def get_fail_msg(self):
        return self.events_fail_msg.get(self.action)

    def get_event(self, success: bool, msg: str = "") -> dict:
        return self.get_success_event(msg) if success else self.get_fail_event(msg)

    def get_success_event(self, msg: str) -> dict:
        title = self.get_msg().format(msg)
        return {self.get_name(): ({"title": title} if self.related else title)}

    def get_fail_event(self, msg: str) -> dict:
        fail_title = self.get_fail_msg().format(msg)
        return {self.get_fail_name(): ({"title": fail_title} if self.related else fail_title)}


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
    field_list = {
        API_ACTION_EXPORT: ["id", "name"],
        API_ACTION_LIST: ["id", "name", "create_date", "modify_date", "is_active"],
    }
    select_related = tuple()
    title = "Project"
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
    actions_with_no_template = (API_ACTION_DELETE, API_ACTION_REACTIVATE)
    actions_get = (
        API_ACTION_HOME,
        API_ACTION_LIST,
        API_ACTION_ADD,
        API_ACTION_EDIT,
        API_ACTION_PARTIAL,
        API_ACTION_EXPORT,
        API_ACTION_IMPORT,
        API_ACTION_READ,
        API_ACTION_RESET,
        API_ACTION_HISTORY,
    )
    actions_post = (
        API_ACTION_ADD,
        API_ACTION_EDIT,
        API_ACTION_REACTIVATE,
        API_ACTION_IMPORT,
        API_ACTION_RESET,
    )
    actions_delete = (API_ACTION_DELETE,)
    user = None
    is_related = False
    upload_files = False
    button_no_text = False
    events = None
    constraints = dict()

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

        self.user_can = {
            action: self.user.eval_perm(action, self.model_name, self.object)
            for action in set(self.actions_get + self.actions_post + self.actions_delete)
        }
        if not self.user_can[self.action]:
            return HttpResponseForbidden()

        self.app = self.model._meta.app_label
        self.nombre = self.model._meta.verbose_name.title()
        self.nombre_plural = self.model._meta.verbose_name_plural.title()

        base_url = f"{self.app}:{self.model_name}"
        self.urls = {  # TODO programmatically
            API_ACTION_ADD: reverse(f"{base_url}:{API_ACTION_ADD}"),
            API_ACTION_LIST: reverse(f"{base_url}:{API_ACTION_LIST}"),
            API_ACTION_EXPORT: reverse(f"{base_url}:{API_ACTION_EXPORT}"),
            API_ACTION_IMPORT: reverse(f"{base_url}:{API_ACTION_IMPORT}"),
        }

        if not self.upload_files:  # if not explicitly enabled, check if action is import
            self.upload_files = self.action == API_ACTION_IMPORT
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        template_suffix = (
            API_ACTION_HOME if self.action in self.actions_with_no_template else self.action
        )
        return [f"{self.app}/{self.model_name}/{template_suffix}.html"]

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

    def get_queryset(self):
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
        context["upload_files"] = self.upload_files
        context["modal_readonly"] = self.action in (API_ACTION_READ, API_ACTION_HISTORY)
        context["user_can"] = self.user_can
        context["urls"] = self.urls
        context["user"] = self.user
        context["object"] = self.object
        if self.action == API_ACTION_LIST:
            fields_list = self.field_list[self.action]
            context["header_list"] = self.model.get_headers_list(fields_list)
            context["row_list"] = self.get_row_list(fields_list)
            context["related_length"] = len(fields_list) + 1
            context["is_related"] = self.is_related
            context["button_no_text"] = self.button_no_text
            context["related_tag"] = RELATED_TAG if self.is_related else ""

        context.update(self.update_context())
        return self.render_to_response(context, **kwargs)

    def render_no_html(self, success, msg):
        events = WebEvents(self.action)
        return HttpResponse(
            status=204, headers={"HX-Trigger": json.dumps(events.get_event(success, msg))}
        )

    def get(self, request, *args, **kwargs):
        if self.action not in self.actions_get:
            return HttpResponseBadRequest()

        if self.action == API_ACTION_HOME:
            self.form = self.search_formclass(**self.get_form_kwargs())
        elif self.action == API_ACTION_PARTIAL_SEARCH:
            kwargs.update({"headers": {"HX-Trigger": "ForceSearch"}})  # TODO is still being used?
            self.form = self.search_formclass(request.GET, **self.get_form_kwargs())
        elif self.action == API_ACTION_LIST:
            self.paginator = Paginator(self.get_queryset(), self.objects_per_page)
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
        if self.action not in self.actions_post:
            return HttpResponseBadRequest()

        if self.action in (API_ACTION_ADD, API_ACTION_EDIT):
            self.form = self.edit_formclass(
                request.POST, request.FILES, instance=self.object, **self.get_form_kwargs()
            )
        elif self.action == API_ACTION_RESET:
            self.form = self.reset_formclass(
                request.POST, instance=self.object, **self.get_form_kwargs()
            )
        elif self.action == API_ACTION_IMPORT:
            self.form = self.import_formclass(request.POST, request.FILES, **self.get_form_kwargs())
        elif self.action == API_ACTION_REACTIVATE:
            return self.reactivate(request, *args, **kwargs)
        else:
            return HttpResponseBadRequest()

        if self.form.is_valid():
            if self.action == API_ACTION_IMPORT:
                return self.import_xlsx()
            try:
                self.form_valid_edit()
            except ValidationError:
                pass
            else:
                return self.render_no_html(success=True, msg=self.nombre.title())
        self.form.format_errors()
        return self._render_html(**kwargs)

    def reactivate(self, request, *args, **kwargs):
        try:
            self.object.reactivate()
        except ValidationError as e:
            success = False
            msg = ", ".join(e.messages)
        else:
            msg = self.nombre.title()
            success = True
        return self.render_no_html(success, msg)

    def delete(self, request, *args, **kwargs):
        if self.action not in self.actions_delete:
            return HttpResponseBadRequest()

        try:
            self.object.delete()
        except (ValidationError, IntegrityError) as e:
            success = False
            msg = ", ".join(e.messages) if hasattr(e, "messages") else str(e)
        else:
            msg = self.nombre.title()
            success = True
        return self.render_no_html(success, msg)

    def form_valid_search(self, qs: QuerySet, cleaned_data: dict) -> QuerySet:
        param = cleaned_data["param"]
        qs = qs.filter(name__icontains=param) if param else qs
        return self.apply_order_by(qs)

    def get_row_list(self, fields_list: list, paginated: bool = True) -> list:
        data = list()
        object_list = list()
        if paginated:
            page_obj = self.paginator.get_page(self.page) if self.paginator else None
            if page_obj:
                object_list = page_obj.object_list
        else:
            object_list = self.get_queryset()

        for obj in object_list:
            data.append(obj.get_row_data(fields_list))

        return data

    def render_xlsx(self):
        filename = f"{self.nombre_plural}_{timezone.now().strftime(XLSX_DATETIME_FORMAT)}.xlsx"
        fields_list = self.field_list[self.action]  # API_ACTION_EXPORT
        headers_list = self.model.get_headers_list(fields_list)
        row_list = self.get_row_list(fields_list, paginated=False)
        dataset = Dataset()
        dataset.headers = headers_list
        for row in row_list:
            dataset.append([validar_si_bool(i["value"]) for i in row.data])
        dataset.title = self.nombre_plural.upper()
        response = HttpResponse(dataset.xlsx, content_type=CONTENT_TYPE_XLSX)
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    def import_xlsx(self):
        file_to_import = self.form.cleaned_data["file"]
        dataset = Dataset().load(file_to_import, format="xlsx")

        if not dataset.headers:
            return self.render_no_html(success=False, msg="Error con el archivo")

        clean_headers = [h for h in dataset.headers if h is not None]

        new = 0
        empty = 0
        errors = 0
        msg_error = ""
        for data in dataset.dict:
            cleaned_data = {k: v for k, v in data.items() if k in clean_headers}
            if not any(cleaned_data.values()):
                empty += 1
                continue

            try:
                self.form_valid_import(cleaned_data)
            except Exception as e:  # NOQA
                errors += 1
                msg_error += ", ".join(e.messages) if hasattr(e, "messages") else str(e)
                logger.error(f"{msg_error}. Error: {e}")
                continue
            else:
                new += 1

        if empty > 10:
            logger.error(f"{msg_error}. Empty lines: {empty}")

        success = errors == 0
        msg = (
            (
                f"{new} {self.nombre.title() if new == 1 else self.nombre_plural.title()} "
                f"importado{'' if new == 1 else 's'} correctamente"
            )
            if success
            else msg_error
        )
        return self.render_no_html(success, msg)

    def form_valid_import(self, cleaned_data: dict) -> None:
        _ = self.model.objects.create(**cleaned_data)

    def form_valid_edit(self):
        try:
            _ = self.form.save()
        except IntegrityError as e:
            msg = str(e)
            match = False
            for c, txt in self.constraints.items():
                if c in msg:
                    match = True
                    self.form.add_error(None, txt)
            if not match:
                self.form.add_error(None, msg)
            logger.error(f"Error al guardar {self.nombre.title()}: {e}")
            raise ValidationError(msg)
        except ValidationError as e:
            self.form.add_error(None, ", ".join(e.messages))
            raise

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
    actions_get = (
        API_ACTION_HOME,
        API_ACTION_LIST,
        API_ACTION_ADD,
        API_ACTION_EDIT,
        API_ACTION_PARTIAL,
        API_ACTION_READ,
        API_ACTION_HISTORY,
    )
    actions_post = (API_ACTION_ADD, API_ACTION_EDIT, API_ACTION_REACTIVATE)
    parent_pk = None
    parent_object = None
    is_related = True
    button_no_text = True

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        if self.user.is_superuser:
            return HttpResponseForbidden()
        self.action = request.path.split("/")[5] or API_ACTION_LIST
        self.object_pk = kwargs.pop("object_pk", None)
        self.parent_pk = kwargs.pop("parent_pk")
        if self.parent_pk:
            try:
                self.parent_object = self.parent_model.todos.get(pk=self.parent_pk)
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

        for action in set(self.actions_get + self.actions_post + self.actions_delete):
            if action in (
                API_ACTION_ADD,
                API_ACTION_DELETE,
                API_ACTION_EDIT,
                API_ACTION_PARTIAL,
                API_ACTION_REACTIVATE,
            ):
                parent_action = API_ACTION_EDIT
            elif action in (API_ACTION_LIST, API_ACTION_READ):
                parent_action = API_ACTION_LIST
            else:
                parent_action = action
            self.user_can[action] = self.user.eval_perm(
                parent_action, self.parent_model_name, self.parent_object
            )

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

        # Default
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    def get_template_names(self):
        template_suffix = (
            API_ACTION_HOME if self.action in self.actions_with_no_template else self.action
        )
        return [f"{self.app}/{self.parent_model_name}/{self.model_name}/{template_suffix}.html"]

    def update_context(self):
        return {
            "list_template": f"{self.app}/{self.parent_model_name}/{self.model_name}/{API_ACTION_LIST}.html",  # NOQA
            "subtitle": f"Listado de {self.nombre_plural.title()}",
            "parent_object": self.parent_object,
        }

    def get_queryset(self):
        filters = {self.parent_model_name: self.parent_object}
        qs = self.model.todos.select_related(*self.get_select_related()).filter(**filters)
        return self.apply_order_by(qs)

    def render_no_html(self, success, msg):
        events = WebEvents(self.action, related=True)
        if self.action in (
            API_ACTION_ADD,
            API_ACTION_EDIT,
            API_ACTION_DELETE,
            API_ACTION_REACTIVATE,
        ):
            related_event_data = events.get_event(success, msg)
            for k in related_event_data.keys():
                related_event_data[k].update({"pk": str(self.parent_pk)})
            return HttpResponse(status=204, headers={"HX-Trigger": json.dumps(related_event_data)})
        raise ImproperlyConfigured("Evento mal configurado")

    def form_valid_edit(self):
        obj = self.form.save(commit=False)
        setattr(obj, self.parent_model_name, self.parent_object)
        try:
            obj.save()
        except IntegrityError as e:
            msg = str(e)
            match = False
            for c, txt in self.constraints.items():
                if c in msg:
                    match = True
                    self.form.add_error(None, txt)
            if not match:
                self.form.add_error(None, msg)
            logger.error(f"Error al guardar {self.nombre.title()}: {e}")
            raise ValidationError(msg)
        except ValidationError as e:
            self.form.add_error(None, ", ".join(e.messages))
            raise


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
