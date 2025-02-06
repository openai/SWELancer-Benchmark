from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from chz.field import Field


class Munger:
    """Marker class for mungers"""

    def __call__(self, chzself: Any, field: Field) -> Any:
        raise NotImplementedError


class if_none(Munger):
    """If None, munge the field to the result of an arbitrary function of the chz object."""

    def __init__(self, replacement: Callable[[Any], Any]):
        self.replacement = replacement

    def __call__(self, chzself: Any, field: Field) -> Any:
        value = getattr(chzself, field.x_name)
        if value is not None:
            return value
        return self.replacement(chzself)


class attr_if_none(Munger):
    """If None, munge the field to another attribute of the chz object."""

    def __init__(self, replacement_attr: str):
        self.replacement_attr = replacement_attr

    def __call__(self, chzself: Any, field: Field) -> Any:
        value = getattr(chzself, field.x_name)
        if value is not None:
            return value
        return getattr(chzself, self.replacement_attr)


class default_munger(Munger):
    def __init__(self, fn: Callable[[Any, Any], Any]):
        self.fn = fn

    def __call__(self, chzself: Any, field: Field) -> Any:
        value = getattr(chzself, field.x_name)
        return self.fn(chzself, value)
