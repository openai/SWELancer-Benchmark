from __future__ import annotations

import collections
import collections.abc
import re
from typing import Any, Callable, Literal

import chz
from chz.field import Field
from chz.tiepin import _simplistic_type_of_value, is_subtype_instance, type_repr


class validate:
    def __init__(self, fn: Callable[[Any], None]):
        self.fn = fn

    def __set_name__(self, owner: Any, name: str) -> None:
        _ensure_chz_validators(owner)
        owner.__chz_validators__.append(self.fn)
        setattr(owner, name, self.fn)


def _ensure_chz_validators(cls: Any) -> None:
    if "__chz_validators__" not in cls.__dict__:
        # make a copy of the parent's validators, if any
        validators: list[Callable[[object], None]] = []
        for base in cls.__bases__:
            validators.extend(getattr(base, "__chz_validators__", []))
        cls.__chz_validators__ = validators


def for_all_fields(fn: Callable[[Any, str], None]) -> Callable[[Any], None]:
    def inner(self: Any) -> None:
        for field in self.__chz_fields__.values():
            fn(self, field.x_name)

    return inner


def instancecheck(self: Any, attr: str) -> None:
    """A good old fashioned isinstance check based on the annotated type of the field."""
    typ = self.__chz_fields__[attr.removeprefix("X_")].final_type
    value = getattr(self, attr)
    if not isinstance(value, typ):
        raise TypeError(f"Expected {attr} to be {type_repr(typ)}, got {type_repr(type(value))}")


def typecheck(self: Any, attr: str) -> None:
    """A fancy type check based on the annotated type of the field."""

    # TODO: this needs to work like the mungers to correctly type check the x and final values
    typ = self.__chz_fields__[attr.removeprefix("X_")].final_type
    value = getattr(self, attr)

    if not is_subtype_instance(value, typ):
        # TODO: is_subtype_instance is in a much better place to return diagnostics
        if getattr(typ, "__origin__", None) is Literal:
            raise TypeError(f"Expected {attr} to be {type_repr(typ)}, got {value!r}")
        raise TypeError(
            f"Expected {attr} to be {type_repr(typ)}, got {type_repr(_simplistic_type_of_value(value))}"
        )


def instance_of(typ: type) -> Callable[[Any, str], None]:
    """Check the attribute is an instance of the given type."""

    def inner(self: Any, attr: str) -> None:
        value = getattr(self, attr)
        if not isinstance(value, typ):
            raise TypeError(f"Expected {attr} to be {type_repr(typ)}, got {type_repr(type(value))}")

    return inner


def gt(base) -> Callable[[Any, str], None]:
    def inner(self: Any, attr: str) -> None:
        value = getattr(self, attr)
        if not value > base:
            raise ValueError(f"Expected {attr} to be greater than {base}, got {value}")

    return inner


def lt(base) -> Callable[[Any, str], None]:
    def inner(self: Any, attr: str) -> None:
        value = getattr(self, attr)
        if not value < base:
            raise ValueError(f"Expected {attr} to be less than {base}, got {value}")

    return inner


def valid_regex(self: Any, attr: str) -> None:
    """Check the attribute is a valid regex."""
    import re

    value = getattr(self, attr)
    try:
        re.compile(value)
    except re.error as e:
        raise ValueError(f"Invalid regex in {attr}: {e}") from None


def const_default(self: Any, attr: str) -> None:
    """Check the attribute matches the field's default value."""
    from chz.util import _MISSING_TYPE

    field: Field = self.__chz_fields__[attr.removeprefix("X_")]
    default = field._default
    if isinstance(default, _MISSING_TYPE):
        raise ValueError(
            "const_default requires a default value (default_factory is not supported)"
        )

    value = getattr(self, attr)
    if value != default:
        raise ValueError(f"Expected {attr} to match the default {default!r}, got {value!r}")


_decorator_typecheck = for_all_fields(typecheck)


def check_field_consistency_in_tree(obj: Any, fields: set[str], regex_root: str = "") -> None:
    """
    This isn't itself a validator. See test_validate_field_consistency for example usage.
    This is effectively a way to paper over a potential missing feature in chz.
    """
    values: dict[tuple[str, str], dict[object, list[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(list)
    )

    def inner(obj: Any, obj_path: str):
        assert chz.is_chz(obj)

        for f in obj.__chz_fields__.values():
            value = getattr(obj, f.logical_name)
            field_path = f"{obj_path}.{f.logical_name}" if obj_path else f.logical_name
            regex_match = re.search(regex_root, obj_path)
            if f.logical_name in fields and regex_match:
                values[(regex_match.group(), f.logical_name)][value].append(field_path)

            if chz.is_chz(value):
                inner(value, field_path)
            if isinstance(value, collections.abc.Mapping):
                for k, v in value.items():
                    if chz.is_chz(v):
                        inner(v, f"{field_path}.{k}")
            elif isinstance(value, collections.abc.Sequence):
                for i, v in enumerate(value):
                    if chz.is_chz(v):
                        inner(v, f"{field_path}.{i}")

    inner(obj, "")

    def paths_repr(paths: list[str]) -> str:
        if len(paths) <= 3:
            return ", ".join(paths)
        return ", ".join(paths[:3]) + f", ... ({len(paths) - 3} more)"

    for (_, field), value_to_paths in values.items():
        if len(value_to_paths) > 1:
            raise ValueError(
                f"Field {field!r} has inconsistent values in object tree:\n"
                + "\n".join(
                    f"{value!r} at {paths_repr(paths)}" for value, paths in value_to_paths.items()
                )
            )


def _find_original_definitions(instance: Any) -> dict[str, tuple[Field, type]]:
    """Find the original field definitions in the parent classes of the instance."""

    assert chz.is_chz(instance)
    fields = {}
    for cls in reversed(type(instance).__mro__):
        if not chz.is_chz(cls):
            continue
        for field in chz.chz_fields(cls).values():
            if field.logical_name not in fields:
                fields[field.logical_name] = (field, cls)
    return fields


def is_override(
    instance: Any, attr: str, *, original_defs: dict[str, tuple[Field, type]] | None = None
) -> None:
    """
    Validator that checks if a field is an override of a field of the same type in a parent class.

    This validator will error out if either:
    - the field doesn't exist in any parent
    - the type of field on the child is not a subtype of the type of the field on the parent

    This is especially useful in case someone renames a field name in the parent class.
    You'll get an error message rather than your override being silently ignored.
    """
    if original_defs is None:
        original_defs = _find_original_definitions(instance)

    logical_name = attr.removeprefix("X_")
    assert logical_name in original_defs

    original_field, original_class = original_defs[logical_name]

    if original_class is type(instance):
        raise ValueError(
            f"Field {logical_name} does not exist in any parent classes of {type_repr(type(instance))}"
        )

    instance_value = getattr(instance, attr)
    if not chz.tiepin.is_subtype_instance(instance_value, original_field.final_type):
        raise ValueError(
            f"{type_repr(type(instance))}.{attr}' must be an instance of "
            f"{type_repr(original_field.final_type)} to match the type on the original definition "
            f"in {type_repr(original_class)}"
        )


class IsOverrideMixin:
    """A mixin that checks if fields are overrides of fields in parent classes.

    The following:

    ```
    @chz.chz
    class Foo:
        x: int = chz.field(default=1, validator=is_override)
        y: int = chz.field(default=1, validator=is_override)
    ```

    is equivalent to:

    ```
    @chz.chz
    class Foo(IsOverrideMixinMixin):
        x: int = chz.field(default=1)
        y: int = chz.field(default=1)
    ```
    """

    @validate
    def _check_overrides(self) -> None:
        fields = getattr(self, "__chz_fields__", None)
        if fields is None:
            return

        original_defs = _find_original_definitions(self)
        for field in fields.values():
            is_override(self, field.x_name, original_defs=original_defs)
