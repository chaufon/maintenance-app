from maintenance.constants import MENU_MANTENIMIENTOS, MENU_REPORTES, MENU_VENTAS


def menu(request):
    return {
        "menu": {
            "ventas": MENU_VENTAS,
            "reportes": MENU_REPORTES,
            "mantenimientos": MENU_MANTENIMIENTOS,
        }
    }
