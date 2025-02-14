from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.safestring import mark_safe

from pghistory.models import Events

from maintenance.constants import (
    ACCORDION_CSS_DISABLED,
    API_ACTION_ADD_STR,
    API_ACTION_DELETE_STR,
    API_ACTION_EDIT_STR,
    API_ACTION_RESET_STR,
    DATETIME_FORMAT,
    HISTORY_EDITOR,
    HISTORY_EDITOR_CANCEL,
)

User = get_user_model()


class History:
    def __init__(self, event, obj):
        self.event = event
        self.obj = obj
        self.diffs = event.pgh_diff
        self.show_accordion = True
        self.accordion_body = bool(self.diffs)
        self.accion = self.get_accion()
        self.datetime = self.event.pgh_created_at
        self.context = self.event.pgh_context
        self.user = self._get_user()
        self.id = str(self.event.pgh_id)
        self.empty = "-"

    def get_accordion_item(self, parent_id) -> str:
        html = ""
        if self.show_accordion:
            child = f"collapse-{self.id}"
            html += f"""
            <div class="accordion-item">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed
                        {'' if self.accordion_body else ACCORDION_CSS_DISABLED}"
                        type="button" data-bs-toggle="collapse"
                        data-bs-target="#{child}" aria-expanded="false" aria-controls="{child}">
                {self.accion.upper()} - {self.user or self.empty} -
                {self.datetime.strftime(DATETIME_FORMAT)}
                </button>
              </h2>
            """
            if self.diffs and self.accordion_body:
                html += f"""
                    <div id="{child}" class="accordion-collapse collapse"
                       data-bs-parent="#{parent_id}">
                    <div class="accordion-body">
                    <table class="table table-sm border-1">
                    <thead>
                    <tr>
                    <th>#</th>
                    <th>Atributo modificado</th>
                    <th>Antes</th>
                    <th>Después</th>
                    </tr>
                    </thead>
                    <tbody>
                    """
                counter = 1
                for k, v in self.diffs.items():
                    if k not in "password":  # force to hide sensitive info
                        name, before, after = self._process_field(k, v)
                        html += f"""
                            <tr>
                            <td>{counter}</td>
                            <td class="align-middle">{name.title()}</td>
                            <td class="align-middle">{before}</td>
                            <td class="align-middle">{after}</td>
                            </tr>
                        """
                        counter += 1

                html += """
                    </tbody>
                    </table>
                    </div>
                  </div>
                """
            html += "</div>"
        return html

    def _process_field(self, key: str, value: list) -> tuple[str, str, str]:
        field = self.obj._meta.get_field(key)
        name = field.verbose_name
        before = value[0]
        after = value[1]
        if isinstance(field, (models.DateTimeField, models.DateField, models.TimeField)):
            before = (
                timezone.datetime.fromisoformat(before).strftime(DATETIME_FORMAT)
                if before
                else self.empty
            )
            after = (
                timezone.datetime.fromisoformat(after).strftime(DATETIME_FORMAT)
                if after
                else self.empty
            )
        elif isinstance(field, models.ForeignKey):
            related_model = field.related_model
            before = str(related_model.todos.get(pk=before)) if before else self.empty
            after = str(related_model.todos.get(pk=after)) if after else self.empty
        elif field.choices:
            if before:
                display_value = next((label for val, label in field.choices if val == before), None)
                before = display_value or before
            else:
                before = self.empty
            if after:
                display_value = next((label for val, label in field.choices if val == after), None)
                after = display_value or after
            else:
                after = self.empty
        else:
            before = before or self.empty
            after = after or self.empty
        return name, before, after

    def _get_user(self) -> User | None:
        user = None
        if self.context and "user" in self.context:
            try:
                user = User.todos.select_related("rol").get(pk=self.context.get("user"))
            except User.DoesNotExist:
                pass
        return user

    def get_accion(self) -> str:
        label = self.event.pgh_label
        if label == "delete":
            accion = API_ACTION_DELETE_STR
        elif label == "insert":
            accion = API_ACTION_ADD_STR
        else:  # label == "update":
            accion = API_ACTION_EDIT_STR
            if len(self.diffs) == 1:
                if "password" in self.diffs:
                    self.accordion_body = False
                    accion = API_ACTION_RESET_STR
                elif "last_login" in self.diffs:
                    self.show_accordion = False
            elif len(self.diffs) == 2:
                if all(
                    [i in self.diffs for i in ("current_editor_id", "current_editor_fecha")]
                ):  # TODO project related
                    self.accordion_body = False
                    accion = (
                        HISTORY_EDITOR_CANCEL
                        if self.diffs["current_editor_id"][0]
                        else HISTORY_EDITOR
                    )
        return accion


class HistoryList:
    def __init__(self, history_object):
        self.history_object = history_object
        self.items = self._get_items()

    def _get_items(self) -> list:
        items = list()
        try:
            events = Events.objects.tracks(self.history_object)
        except Events.DoesNotExist:
            pass
        else:
            for event in events:
                items.append(History(event, self.history_object))
        return items

    def get_accordion(self) -> str:
        parent_id = f"parent_{self.history_object.pk}"
        html = f'<div class="accordion" id="{parent_id}">'
        for item in self.items:
            html += item.get_accordion_item(parent_id)
        html += "</div>"
        return mark_safe(html)
