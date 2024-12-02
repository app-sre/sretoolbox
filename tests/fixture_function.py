import sys


def identity(x):
    return x


def raiser(*_args, **_kwargs):
    raise Exception("Oh noes!")  # noqa: TRY002


def sys_exit_func(*args, **_kwargs):
    sys.exit(args)


def return_int_raise_value_error_otherwise(x):
    if isinstance(x, int):
        return x
    raise ValueError(x)
