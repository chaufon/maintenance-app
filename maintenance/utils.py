from maintenance.constants import FALSE_STR, TODOS, TODOS_STR, TRUE_STR


def complete_todos_choices(choices: tuple, at_the_end: bool = True) -> tuple:
    todos_tuple = ((TODOS, TODOS_STR),)
    return choices + todos_tuple if at_the_end else todos_tuple + choices


def true_false_str(value: bool) -> str:
    return TRUE_STR if value else FALSE_STR
