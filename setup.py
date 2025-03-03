from setuptools import find_packages, setup

setup(
    name="maintenance-app",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django>=5.1.6",
        "psycopg>=3.2.5",
        "psycopg-c>=3.2.5",
        "django-pghistory>=3.5.2",
        "django-template-partials>=24.4",
        "sentry-sdk[django]>=2.22.0",
        "tablib[xlsx]>=3.8.0"
    ],
)
