from django.core.exceptions import ValidationError


def validate_file_xls(file):
    XLS_MAGIC_NUMBER = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

    file.seek(0)
    file_header = file.read(8)
    file.seek(0)

    if not file_header.startswith(XLS_MAGIC_NUMBER):
        raise ValidationError("Solo archivos Excel '.xls' son permitidos")


def validate_file_xlsx(file):
    XLSX_MAGIC_NUMBER = b"\x50\x4b\x03\x04"

    file.seek(0)
    file_header = file.read(8)
    file.seek(0)

    if not file_header.startswith(XLSX_MAGIC_NUMBER):
        raise ValidationError("Solo archivos Excel '.xlsx' son permitidos")


def cellphone_number(number):
    if not number.isdigit():
        raise ValidationError("Solo se permiten caracteres numéricos")
    if not number.startswith("9"):
        raise ValidationError("Números celulares comienzan con '9'")
    if len(number) != 9:
        raise ValidationError("Debe tener 9 dígitos de longitud")


def only_digits(value):
    if not value.isdigit():
        raise ValidationError("Solo se permiten caracteres numéricos")
