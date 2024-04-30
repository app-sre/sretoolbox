import sys


def identity(x):
    return x


def raiser(*args, **kwargs):
    raise Exception("Oh noes!")


def sys_exit_func(*args, **kwargs):
    sys.exit(args)


def return_int_raise_value_error_otherwise(x):
    if isinstance(x, int):
        return x
    else:
        raise ValueError(x)
