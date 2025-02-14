from setuptools import setup, find_packages

setup(
    name="maintenance",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django>=5.1.6",
        "psycopg>=3.2.4",
        "psycopg-c>=3.2.4",
        "django-pghistory>=3.5.2",
        "django-template-partials>=24.4",
    ],
)
