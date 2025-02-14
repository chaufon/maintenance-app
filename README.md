# MAINTENANCE
This repository serves as a template for future Django projects, providing a well-structured foundation to build upon. It includes essential features like user authentication, role management, and dynamic views using HTMX.


## env
```shell
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_SECRET_KEY=7hx7umjl)=l^uxsei32b*pepbvhi(=4_)qolp36pop6xcc$787
DJANGO_STATIC_ROOT=/home/centos/Documents/PARTNER/unicornio/static
DJANGO_ALLOWED_HOSTS=192.168.18.235
LOGGING_LEVEL=WARNING
REDIS_URL=redis://127.0.0.1:6379/4
DB_HOST=192.168.18.201
DB_PASSWORD=testing2021
DB_NAME=unicornio
DB_USER=postgres
DB_PORT=5432
SENTRY_DSN=https://xXXXXXXXX
SENTRY_ENVIRONMENT=develop
SENTRY_RELEASE=0.5.0
```

## PYTHON
`python3.13`

## PACKAGES
### base.txt
```shell
Django==5.1.6
redis==5.2.1
psycopg-c==3.2.4
psycopg==3.2.4
django-pghistory==3.5.2
django-template-partials==24.4
django-import-export[xlsx]==4.2.0  # TODO still need it?
django-import-export[xls]==4.2.0  # TODO still need it?
sentry-sdk[django]==2.20.0

```

### dev.txt
```shell
-r base.txt

black==25.1.0
flake8==7.1.1
django-extensions==3.2.3
ipython==8.32.0
pre_commit==4.1.0
isort==6.0.0
django-silk==5.3.2
```


### prod.txt
```shell
-r base.txt

gunicorn==23.0.0
```

## VENDORS

### CSS
### JS
### ICONS

## USE
1. navbar template and context_processors.py
