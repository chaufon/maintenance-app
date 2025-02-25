# Django Maintenance App

This Django app provides a streamlined solution for implementing maintenance functionalities within your Django projects. It offers a collection of reusable templates, static assets, base models, and a powerful `MaintenanceView` that leverages HTMX for a smooth and interactive user experience.

## Features

*   **Reusable Templates:**  A set of pre-built templates for common maintenance tasks, such as database backups, cache clearing, and more.  These templates are designed to be easily customized to fit your project's specific needs.
*   **Static Assets:** Includes CSS and JavaScript files (including HTMX) to enhance the look and feel of your maintenance pages and provide interactive functionality.
*   **Base Models:** Provides abstract base models and Mixin classes that can be extended to represent maintenance-related data.
*   **`MaintenanceView`:** A generic view that simplifies the creation of maintenance interfaces. It provides a framework for defining and executing maintenance actions, with HTMX integration for dynamic updates and a responsive user interface.
*   **HTMX Integration:**  The `MaintenanceView` is designed to work seamlessly with HTMX, allowing you to create dynamic and interactive maintenance interfaces without writing extensive JavaScript.

## Installation

1.  **Install the package:**

    ```bash
    pip install django-maintenance-app  # Replace with your actual package name
    ```

2.  **Add `maintenance_app` to your `INSTALLED_APPS` in `settings.py`:**

    ```python
    INSTALLED_APPS = [
        ...
        'maintenance_app',
        ...
    ]
    ```

3.  **Include the app's URLs in your project's `urls.py` (optional, if you want to use the provided views directly):**

    ```python
    from django.urls import include, path

    urlpatterns = [
        ...
        path('maintenance/', include('maintenance_app.urls')),
        ...
    ]
    ```

4.  **Configure settings (optional):**

    *   You can customize the app's behavior by overriding settings in your project's `settings.py`.  See the "Configuration" section below for available settings.

## Usage

### Using the `MaintenanceView`

The core of this app is the `MaintenanceView`.  Here's a basic example of how to use it:

1.  **Create a subclass of `MaintenanceView` in your `views.py`:**

    ```python
    from maintenance_app.views import MaintenanceView
    from django.http import HttpResponse

    class MyMaintenanceView(MaintenanceView):
        template_name = 'my_maintenance_template.html'  # Your custom template

        def get_actions(self):
            return [
                {'name': 'Clear Cache', 'url': self.get_action_url('clear_cache')},
                {'name': 'Database Backup', 'url': self.get_action_url('database_backup')},
            ]

        def clear_cache(self, request):
            # Your cache clearing logic here
            # Example:
            # from django.core.cache import cache
            # cache.clear()
            return HttpResponse("Cache cleared successfully!")

        def database_backup(self, request):
            # Your database backup logic here
            # Example:
            # from django.core.management import call_command
            # call_command('dumpdata', output='backup.json')
            return HttpResponse("Database backup completed!")
    ```

2.  **Register the view in your `urls.py`:**

    ```python
    from django.urls import path
    from .views import MyMaintenanceView

    urlpatterns = [
        path('my-maintenance/', MyMaintenanceView.as_view(), name='my_maintenance'),
    ]
    ```

3.  **Create your custom template (`my_maintenance_template.html`):**

    This template should extend the base template provided by the app (e.g., `maintenance_app/base.html`) and display the available actions.  Use HTMX attributes to trigger the actions.  See the "Templates" section for more details.

### Templates

The app provides base templates that you can extend in your project.  These templates include basic styling and HTMX setup.  The main template is located at `maintenance_app/base.html`.

You can override these templates by creating templates with the same name in your project's template directories.

### Static Files

The app includes static files (CSS and JavaScript) that enhance the appearance and functionality of the maintenance pages.  Make sure your Django project is configured to serve static files correctly.

### Base Models

The app provides abstract base models that you can extend to represent maintenance-related data.  These models include fields for tracking task status, timestamps, and other relevant information.

## Configuration

You can customize the app's behavior by overriding the following settings in your project's `settings.py`:

*   `MAINTENANCE_APP_TEMPLATE_BASE`:  The base template to extend (default: `maintenance_app/base.html`).
*   `MAINTENANCE_APP_STATIC_URL`: The URL where the static files are served (default: `STATIC_URL`).

## Contributing

Contributions are welcome!  Please submit pull requests with bug fixes, new features, or improvements to the documentation.

## License

[Your License (e.g., MIT License)]


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
tablib[xlsx]==3.8.0
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


## TODOs

* Modal size customization
* Javascript/CSS sources integration
* CSS customization


## NEW FEATURES

* Command management to add new actions (ADVANCED)
