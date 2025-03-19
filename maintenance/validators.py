from django.core.exceptions import ValidationError

from maintenance.constants import CONTENT_TYPE_MP3, CONTENT_TYPE_XLSX, CONTENT_TYPE_ZIP


def get_file_content_type(file):
    import magic

    file_buffer = file.read(2048)
    file.seek(0)
    return magic.from_buffer(file_buffer, mime=True)


def is_zip(file):
    content_type = get_file_content_type(file)
    return content_type == CONTENT_TYPE_ZIP


def is_mp3(file):
    content_type = get_file_content_type(file)
    return content_type == CONTENT_TYPE_MP3


def is_xlsx(file):
    content_type = get_file_content_type(file)
    return content_type == CONTENT_TYPE_XLSX


def is_xls(file):
    content_type = get_file_content_type(file)
    return content_type == "application/vnd.ms-excel"


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
