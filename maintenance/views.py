import json
import logging

from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
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
    RELATED_TAG,
    XLSX_DATETIME_FORMAT,
)
from maintenance.exceptions import FormIsNotValid
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
from maintenance.webevents import get_webevent

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
    field_list = {
        API_ACTION_EXPORT: ["id", "name"],
        API_ACTION_LIST: ["id", "name", "create_date", "modify_date", "is_active"],
    }
    select_related = tuple()
    title = ""
    subtitle = ""
    object = None
    object_pk = None
    paginator = None
    object_list = None
    page = 1
    objects_per_page = 20
    form = None
    user_can = dict()
    urls = dict()
    menu_active = MENU_MANTENIMIENTOS
    MODAL_SIZE_SM = "modal-sm"
    MODAL_SIZE_LG = "modal-lg"
    MODAL_SIZE_XL = "modal-xl"
    actions_with_no_template = (API_ACTION_DELETE, API_ACTION_REACTIVATE, API_ACTION_EXPORT)
    actions_with_no_object = (
        API_ACTION_HOME,
        API_ACTION_LIST,
        API_ACTION_ADD,
        API_ACTION_EXPORT,
        API_ACTION_IMPORT,
    )
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
    webevent = None
    constraints = dict()
    form_show = True

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.action = request.path.split("/")[3] or API_ACTION_HOME
        self.object_pk = kwargs.pop("object_pk", None)
        if self.object_pk:
            qs = self.model.todos.all()
            if select_related := self.get_select_related():
                qs = qs.select_related(*select_related)

            try:
                self.object = qs.get(pk=self.object_pk)
            except self.model.ObjectDoesNotExist:
                return HttpResponseNotFound()
            else:
                is_active = True if self.object.is_active is None else self.object.is_active
                if self.action == API_ACTION_EDIT and not is_active:
                    return HttpResponseForbidden()
        self.page = self.request.GET.get("page", 1)
        self.model_name = self.model_name or self.model._meta.model_name
        all_actions_allowed = set(self.actions_get + self.actions_post + self.actions_delete)

        for action in all_actions_allowed:
            self.user_can[action] = self.user.eval_perm(action, self.model_name, self.object)

        if not self.user_can[self.action]:
            return HttpResponseForbidden()

        self.app = self.model._meta.app_label
        self.nombre = self.model._meta.verbose_name.title()
        self.nombre_plural = self.model._meta.verbose_name_plural.title()
        self.subtitle = self.subtitle or f"Mantenimiento de {self.nombre_plural.title()}"
        self.title = f"{self.title or 'Project'} | {self.subtitle}"

        base_url = f"{self.app}:{self.model_name}"
        for action in self.actions_with_no_object:
            if action in all_actions_allowed:
                self.urls[action] = reverse(f"{base_url}:{action}")

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

    def get_order_by(self):
        return self.order_by

    def get_select_related(self) -> tuple:
        return self.select_related

    def apply_post_filter(self, qs: QuerySet) -> QuerySet:
        if select_related := self.get_select_related():
            qs = qs.select_related(*select_related)

        if order_by := self.get_order_by():
            qs = qs.order_by(*order_by)
        return qs

    def get_queryset(self):
        self.form = self.search_formclass(self.request.GET, **self.get_form_kwargs())
        if self.form.is_valid():
            qs_filtered = self.form_valid_search(self.model.todos.all(), self.form.cleaned_data)
            return self.apply_post_filter(qs_filtered)
        return self.model.objects.none()

    def _render_html(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["subtitle"] = self.subtitle
        context["menu_active"] = self.menu_active
        context["form"] = self.form
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
        context["form_show"] = self.form_show
        if self.action == API_ACTION_LIST:
            row_list = list()
            fields_list = self.field_list[self.action]
            page_obj = self.paginator.get_page(self.page)
            self.object_list = page_obj.object_list
            for obj in self.object_list:
                row_list.append(obj.get_row_data(fields_list))

            context["header_list"] = self.model.get_headers_list(fields_list)
            context["row_list"] = row_list
            context["page_obj"] = page_obj
            context["pages"] = self.paginator.get_elided_page_range(self.page)
            context["related_length"] = len(fields_list) + 1
            context["is_related"] = self.is_related
            context["button_no_text"] = self.button_no_text
            context["related_tag"] = RELATED_TAG if self.is_related else ""
        elif self.action == API_ACTION_IMPORT:
            context["form_accordion_enable"] = True
            context["form_accordion_show"] = False

        context.update(self.update_context())
        return self.render_to_response(context, **kwargs)

    def render_no_html(self, success, msg):
        if not self.webevent:
            self.webevent = get_webevent(self.action)
        return HttpResponse(
            status=204, headers={"HX-Trigger": json.dumps(self.webevent.get_event(success, msg))}
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
            except FormIsNotValid:
                pass
            else:
                return self.render_no_html(success=True, msg=self.nombre.title())
        self.form.format_errors()
        return self._render_html(**kwargs)

    def reactivate(self, request, *args, **kwargs):
        try:
            self.object.reactivate()
        except Exception as e:
            logger.error(f"Error while reactivating object pk {self.object.pk}: {e}")
            success = False
        else:
            success = True
        return self.render_no_html(success, self.nombre.title())

    def delete(self, request, *args, **kwargs):
        if self.action not in self.actions_delete:
            return HttpResponseBadRequest()

        try:
            self.object.delete()
        except Exception as e:
            logger.error(f"Error while deleting object pk {self.object.pk}: {e}")
            success = False
        else:
            success = True
        return self.render_no_html(success, self.nombre.title())

    def form_valid_search(self, qs: QuerySet, cleaned_data: dict) -> QuerySet:
        param = cleaned_data["param"]
        if param:
            qs = qs.filter(name__icontains=param)
        return qs

    def render_xlsx(self):
        row_list = list()
        filename = f"{self.nombre_plural}_{timezone.now().strftime(XLSX_DATETIME_FORMAT)}.xlsx"
        fields_list = self.field_list[self.action]  # API_ACTION_EXPORT
        headers_list = self.model.get_headers_list(fields_list)
        for obj in self.get_queryset():
            row_list.append(obj.get_row_data(fields_list))

        dataset = Dataset()
        dataset.headers = headers_list
        for row in row_list:
            dataset.append([validar_si_bool(i["value"]) for i in row["data"]])
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
        obj = self.model(**cleaned_data)
        obj.save()

    def form_valid_edit(self, obj=None):
        try:
            if obj:
                obj.save()
            else:
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
            raise FormIsNotValid
        except ValidationError as e:
            self.form.add_error(None, ", ".join(e.messages))
            raise FormIsNotValid

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
    actions_with_no_object = (API_ACTION_LIST, API_ACTION_ADD)
    actions_get = (
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
                    else:
                        is_active = True if self.object.is_active is None else self.object.is_active
                        if self.action == API_ACTION_EDIT and not is_active:
                            return HttpResponseForbidden()

        self.parent_model_name = self.parent_model._meta.model_name
        self.model_name = self.model_name or self.model._meta.model_name
        all_actions_allowed = set(self.actions_get + self.actions_post + self.actions_delete)

        for action in all_actions_allowed:
            self.user_can[action] = self.user.eval_perm_related(
                action, self.parent_model_name, self.parent_object, self.object
            )

        if not self.user_can[self.action]:
            return HttpResponseForbidden()

        self.app = self.model._meta.app_label
        self.nombre = self.model._meta.verbose_name.title()
        self.nombre_plural = self.model._meta.verbose_name_plural.title()
        self.subtitle = self.subtitle or f"Listado de {self.nombre_plural.title()}"
        self.title = f"{self.title or 'Project'} | {self.subtitle}"

        base_url = f"{self.app}:{self.parent_model_name}:{self.model_name}"
        for action in self.actions_with_no_object:
            if action in all_actions_allowed:
                self.urls[action] = reverse(f"{base_url}:{action}", args=(self.parent_pk,))

        # Default
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    def get_template_names(self):
        template_suffix = (
            API_ACTION_LIST if self.action in self.actions_with_no_template else self.action
        )
        return [f"{self.app}/{self.parent_model_name}/{self.model_name}/{template_suffix}.html"]

    def update_context(self):
        return {
            "list_template": f"{self.app}/{self.parent_model_name}/{self.model_name}/{API_ACTION_LIST}.html",  # NOQA
            "parent_object": self.parent_object,
        }

    def get_queryset(self):
        filters = {self.parent_model_name: self.parent_object}
        qs = self.model.todos.filter(**filters)
        return self.apply_post_filter(qs)

    def render_no_html(self, success, msg):
        if not self.webevent:
            self.webevent = get_webevent(self.action, is_related=True)
        related_data = self.webevent.get_event(success, msg)
        for k in related_data.keys():
            related_data[k].update(
                {"parent_pk": str(self.parent_pk), "object_pk": str(self.object_pk)}
            )
        return HttpResponse(status=204, headers={"HX-Trigger": json.dumps(related_data)})

    def form_valid_edit(self, obj=None):
        if not obj:
            obj = self.form.save(commit=False)
            setattr(obj, self.parent_model_name, self.parent_object)
        super().form_valid_edit(obj)


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
