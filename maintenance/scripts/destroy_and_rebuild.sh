#!/bin/bash
python manage.py reset_db --no-input
rm -rf apps/*/migrations/000*
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata departamentos.json
python manage.py loaddata provincias.json
python manage.py loaddata distritos.json
python manage.py loaddata roles.json
python manage.py loaddata users.json
