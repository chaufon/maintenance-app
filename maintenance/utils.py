from maintenance.constants import (
    ACCESS_PORTABILIDAD,
    ACCESS_PORTABILIDAD_STR,
    ACCESS_RENOVACION,
    ACCESS_RENOVACION_STR,
    ACCESS_ROOT,
    ACCESS_ROOT_STR,
    FALSE_STR,
    TODOS,
    TODOS_STR,
    TRUE_STR,
)


def complete_todos_choices(choices: tuple, at_the_end: bool = True) -> tuple:
    todos_tuple = ((TODOS, TODOS_STR),)
    return choices + todos_tuple if at_the_end else todos_tuple + choices


def get_accesses(access: int | None = None) -> tuple:
    if access == ACCESS_PORTABILIDAD:
        return ((ACCESS_PORTABILIDAD, ACCESS_PORTABILIDAD_STR),)
    elif access == ACCESS_RENOVACION:
        return ((ACCESS_RENOVACION, ACCESS_RENOVACION_STR),)
    else:
        return (
            (ACCESS_PORTABILIDAD, ACCESS_PORTABILIDAD_STR),
            (ACCESS_RENOVACION, ACCESS_RENOVACION_STR),
            (ACCESS_ROOT, ACCESS_ROOT_STR),
        )


def true_false_str(value: bool) -> str:
    return TRUE_STR if value else FALSE_STR
