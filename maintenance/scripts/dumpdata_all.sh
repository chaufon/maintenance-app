#!/bin/bash
python manage.py dumpdata --indent 2 users.Rol > apps/users/fixtures/roles.json
python manage.py dumpdata --indent 2 users.User > apps/users/fixtures/users.json
python manage.py dumpdata --indent 2 common.Departamento > apps/common/fixtures/departamentos.json
python manage.py dumpdata --indent 2 common.Provincia > apps/common/fixtures/provincias.json
python manage.py dumpdata --indent 2 common.Distrito > apps/common/fixtures/distritos.json
