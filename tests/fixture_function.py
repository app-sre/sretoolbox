import sys
from typing import Any, Never


def identity(x: Any) -> Any:
    return x


def raiser(*_args: Any, **_kwargs: Any) -> Never:
    raise Exception("Oh noes!")  # noqa: TRY002


def sys_exit_func(arg: str | int | None = None) -> None:
    sys.exit(arg)


def return_int_raise_value_error_otherwise(x: Any) -> int:
    if isinstance(x, int):
        return x
    raise ValueError(x)
