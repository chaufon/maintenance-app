from setuptools import find_packages, setup

setup(
    name="maintenance-app",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django>=5.2.1",
        "psycopg>=3.2.9",
        "psycopg-c>=3.2.9",
        "django-pghistory>=3.6.0",
        "django-template-partials>=24.4",
        "sentry-sdk[django]>=2.29.1",
        "tablib[xlsx]>=3.8.0",
        "python-magic>=0.4.27",
    ],
)
