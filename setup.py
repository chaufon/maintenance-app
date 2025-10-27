from setuptools import find_packages, setup

setup(
    name="maintenance-app",
    version="1.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django>=5.2.7",
        "psycopg>=3.2.12",
        "psycopg-c>=3.2.12",
        "django-pghistory>=3.8.3",
        "django-template-partials>=25.2",
        "sentry-sdk[django]>=2.42.1",
        "tablib[xlsx]>=3.9.0",
        "python-magic>=0.4.27",
    ],
)
