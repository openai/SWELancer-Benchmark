from typing import TYPE_CHECKING, Callable, TypeVar, overload

from . import blueprint, factories, mungers, tiepin, validators
from .blueprint import (
    Blueprint,
    Castable,
    entrypoint,
    get_nested_target,
    methods_entrypoint,
    nested_entrypoint,
)
from .data_model import (
    asdict,
    beta_to_blueprint_values,
    chz_fields,
    chz_make_class,
    init_property,
    is_chz,
    replace,
)
from .field import field
from .validators import validate

__all__ = [
    "Blueprint",
    "asdict",
    "chz",
    "is_chz",
    "chz_fields",
    "entrypoint",
    "field",
    "get_nested_target",
    "init_property",
    "methods_entrypoint",
    "nested_entrypoint",
    "replace",
    "beta_to_blueprint_values",
    "validate",
    "validators",
    "mungers",
    "Castable",
    # are the following public?
    "blueprint",
    "factories",
    "tiepin",
]


def _chz(cls=None, *, version: str | None = None, typecheck: bool | None = None):
    if cls is None:
        return lambda cls: chz_make_class(cls, version=version, typecheck=typecheck)
    return chz_make_class(cls, version=version, typecheck=typecheck)


if TYPE_CHECKING:
    _TypeT = TypeVar("_TypeT", bound=type)

    from typing_extensions import dataclass_transform

    @dataclass_transform(kw_only_default=True, frozen_default=True, field_specifiers=(field,))
    @overload
    def chz(version: str = ..., typecheck: bool = ...) -> Callable[[type], type]: ...

    @overload
    def chz(cls: _TypeT, /) -> _TypeT: ...

    def chz(*a, **k):
        raise NotImplementedError

else:
    chz = _chz
