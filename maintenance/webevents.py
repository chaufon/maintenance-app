from dataclasses import dataclass

from maintenance.constants import (
    API_ACTION_ADD,
    API_ACTION_DELETE,
    API_ACTION_EDIT,
    API_ACTION_IMPORT,
    API_ACTION_REACTIVATE,
    API_ACTION_RESET,
)

EVENTS_NAME = {
    API_ACTION_ADD: "ObjectAdded",
    API_ACTION_DELETE: "ObjectDeleted",
    API_ACTION_REACTIVATE: "ObjectReactivated",
    API_ACTION_EDIT: "ObjectEdited",
    API_ACTION_IMPORT: "ObjectsImported",
    API_ACTION_RESET: "PasswordUpdated",
}
EVENTS_MSG_MASC = {
    API_ACTION_ADD: "{} creado correctamente",
    API_ACTION_DELETE: "{} eliminado correctamente",
    API_ACTION_REACTIVATE: "{} reactivado correctamente",
    API_ACTION_EDIT: "{} actualizado correctamente",
    API_ACTION_IMPORT: "Importación correcta. {}",
    API_ACTION_RESET: "Contraseña reseteada correctamente",
}
EVENTS_MSG_FEM = {
    API_ACTION_ADD: "{} creada correctamente",
    API_ACTION_DELETE: "{} eliminada correctamente",
    API_ACTION_REACTIVATE: "{} reactivada correctamente",
    API_ACTION_EDIT: "{} actualizada correctamente",
    API_ACTION_IMPORT: "Importación correcta. {}",
    API_ACTION_RESET: "Contraseña reseteada correctamente",
}
EVENTS_FAIL_NAME = {
    API_ACTION_DELETE: "ObjectDeletedFail",
    API_ACTION_REACTIVATE: "ObjectReactivatedFail",
    API_ACTION_IMPORT: "ObjectsImportedFail",
    API_ACTION_RESET: "PasswordUpdatedFail",
}
EVENTS_FAIL_MSG = {
    API_ACTION_ADD: "No se pudo crear. {}",
    API_ACTION_DELETE: "No se pudo eliminar. {}",
    API_ACTION_REACTIVATE: "No se pudo reactivar {}",
    API_ACTION_EDIT: "No se pudo editar. {}",
    API_ACTION_IMPORT: "No se pudo importar. {}",
    API_ACTION_RESET: "No se actualizó contraseña",
}

EVENTS_NAME_RELATED = {
    API_ACTION_ADD: "ObjectAddedRelated",
    API_ACTION_DELETE: "ObjectDeletedRelated",
    API_ACTION_REACTIVATE: "ObjectReactivatedRelated",
    API_ACTION_EDIT: "ObjectEditedRelated",
}
EVENTS_FAIL_NAME_RELATED = {
    API_ACTION_DELETE: "ObjectDeletedFailRelated",
    API_ACTION_REACTIVATE: "ObjectReactivatedFailRelated",
}


@dataclass()
class WebEvent:
    action: str
    events_name: dict
    events_msg: dict
    events_fail_name: dict
    events_fail_msg: dict

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
        return {self.get_name(): {"title": title}}

    def get_fail_event(self, msg: str) -> dict:
        fail_title = self.get_fail_msg().format(msg)
        return {self.get_fail_name(): {"title": fail_title}}


def get_webevent(action: str, is_masc: bool = True, is_related: bool = False, **kwargs) -> WebEvent:
    events_name = kwargs.get("events_name") or (
        EVENTS_NAME_RELATED.copy() if is_related else EVENTS_NAME.copy()
    )
    events_msg = kwargs.get("events_msg") or (
        EVENTS_MSG_MASC.copy() if is_masc else EVENTS_MSG_FEM.copy()
    )
    events_fail_name = kwargs.get("events_fail_name") or (
        EVENTS_FAIL_NAME_RELATED.copy() if is_related else EVENTS_FAIL_NAME.copy()
    )
    events_fail_msg = kwargs.get("events_fail_msg") or EVENTS_FAIL_MSG.copy()

    return WebEvent(action, events_name, events_msg, events_fail_name, events_fail_msg)
