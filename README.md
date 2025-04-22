# Django Maintenance App

This Django app provides a streamlined solution for implementing maintenance functionalities within
your Django projects. It offers a collection of reusable templates, static assets, base models, and
a powerful `MaintenanceView` that leverages HTMX for a smooth and interactive user experience.

## Features

* **Reusable Templates:**  A set of pre-built templates for common maintenance tasks, such as
  database backups, cache clearing, and more. These templates are designed to be easily customized
  to fit your project's specific needs.
* **Static Assets:** Includes CSS and JavaScript files (including HTMX) to enhance the look and feel
  of your maintenance pages and provide interactive functionality.
* **Base Models:** Provides abstract base models and Mixin classes that can be extended to represent
  maintenance-related data.
* **`MaintenanceView`:** A generic view that simplifies the creation of maintenance interfaces. It
  provides a framework for defining and executing maintenance actions, with HTMX integration for
  dynamic updates and a responsive user interface.
* **HTMX Integration:**  The `MaintenanceView` is designed to work seamlessly with HTMX, allowing
  you to create dynamic and interactive maintenance interfaces without writing extensive JavaScript.

## Installation

1. **Install the package:**

   ```bash
   pip install git+https://github.com/chaufon/maintenance-app.git@v1.0.0
   ```

2. **Add `maintenance` to your `INSTALLED_APPS` in `settings.py`:**

   ```python
   INSTALLED_APPS = [
       ...
       'maintenance',
       ...
   ]
   ```

3. **Include the app's URLs in your project's `urls.py` (optional, if you want to use the "ubigeo 
views directly):**

   ```python
   from django.urls import include, path

   urlpatterns = [
       ...
       path('maintenance/', include('maintenance.urls')),
       ...
   ]
   ```

## env

```shell
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_SECRET_KEY=7hx7umjl)=l^uxsei32b*pepbvhi(=4_)qolp36pop6xcc$787
DJANGO_STATIC_ROOT=/tmp/static
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


## EXAMPLES

### Redirect logic after login

```python
class MyLoginView(MaintenanceLoginView):

    def get_success_url(self):
        user = self.request.user
        if user.es_root or (not user.can_list_venta and not user.es_op_invitado):
            return reverse("users:user:home")
        else:
            app = "renovacion" if user.es_renovacion else "portabilidad"
            model = "reporte" if user.es_op_invitado else "venta"
            return reverse(f"{app}:{model}:home")
```

## TODO

* Modal size customization per variable
* Javascript/CSS sources integration
* SCSS customization
* Show error message on login form
* Show error when importing
* Change password for everybody
* Pagination always at the end of the page
* Remove modify_date from History detail
* Autofocus on single field forms
* return HttpResponseForbidden(), is that fine or can be improve.
* Create/modify user is needed? or with user provided by pghistory is enough? 
* Modal does not show errors when form is invalid

## NEW FEATURES

* Command management to add new actions (ADVANCED)
* Captcha
* Sticky table headers
* Re-enable objects after being deleted 
* History is showing date_modified as a field edited (it shouldn't 'cause is a system managed field)
