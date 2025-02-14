from import_export import resources

from maintenance.models import Departamento, Distrito, Provincia


class MaintenanceResource(resources.ModelResource):
    def get_export_fields(self, selected_fields=None):
        fields = super().get_export_fields(selected_fields)
        for field in fields:
            model_field = self._meta.model._meta.get_field(field.attribute)
            field.column_name = (
                model_field.verbose_name
                if model_field and model_field.verbose_name
                else field.column_name
            ).upper()
        return fields


class DepartamentoResource(MaintenanceResource):
    class Meta:
        model = Departamento
        fields = ("name", "codigo")
        import_id_fields = ("codigo",)
        skip_unchanged = True


class ProvinciaResource(MaintenanceResource):
    class Meta:
        model = Provincia
        fields = ("name", "codigo", "departamento")
        import_id_fields = ("codigo",)
        skip_unchanged = True

    def dehydrate_departamento(self, obj):
        return obj.departamento.name


class DistritoResource(MaintenanceResource):
    class Meta:
        model = Distrito
        fields = ("name", "codigo", "provincia")
        import_id_fields = ("codigo",)
        skip_unchanged = True

    def dehydrate_provincia(self, obj):
        return obj.provincia.name
