#!/bin/bash
python manage.py reset_db
python manage.py migrate
python manage.py loaddata roles.json
python manage.py loaddata departamentos.json
python manage.py loaddata provincias.json
python manage.py loaddata distritos.json
python manage.py loaddata test_users.json
