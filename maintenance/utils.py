from datetime import date, datetime, time

from maintenance.constants import (
    DATE_FORMAT,
    DATETIME_FORMAT,
    EMPTY_VALUE,
    FALSE_STR,
    TIME_FORMAT,
    TODOS,
    TODOS_STR,
    TRUE_STR,
)


def complete_todos_choices(choices: tuple, at_the_end: bool = True) -> tuple:
    todos_tuple = ((TODOS, TODOS_STR),)
    return choices + todos_tuple if at_the_end else todos_tuple + choices


def true_false_str(value: bool) -> str:
    return TRUE_STR if value else FALSE_STR


def validar_si_bool(value: str) -> str:
    if value == "True":
        value = True
    elif value == "False":
        value = False
    return true_false_str(value) if isinstance(value, bool) else value


def format_to_str(value) -> str:
    if isinstance(value, bool):
        return true_false_str(value)
    elif isinstance(value, datetime):
        return value.strftime(DATETIME_FORMAT)
    elif isinstance(value, date):
        return value.strftime(DATE_FORMAT)
    elif isinstance(value, time):
        return value.strftime(TIME_FORMAT)
    elif value is None or value == "":
        return EMPTY_VALUE
    return str(value)
