from django.contrib import admin


class MaintenanceAdmin(admin.AdminSite):
    site_title = "Administración de Proyecto"
    site_header = "Proyecto"
    index_title = "Lista de Mantenimientos"
    site_url = "/"


maintenance_admin = MaintenanceAdmin(name="maintenance_admin")
