from __future__ import annotations

import functools
import types
from typing import Any, Mapping, TypeVar

import chz.blueprint
from chz.blueprint._argmap import Layer
from chz.blueprint._wildcard import wildcard_key_to_regex
from chz.tiepin import type_repr

_T = TypeVar("_T")


def argv_to_blueprint_args(
    argv: list[str], *, allow_hyphens: bool = False
) -> Mapping[str, chz.blueprint.Castable | chz.blueprint.Reference]:
    # TODO: allow stuff like model[family=linear n_layers=1]
    ret: dict[str, chz.blueprint.Castable | chz.blueprint.Reference] = {}
    for arg in argv:
        try:
            key, value = arg.split("=", 1)
        except ValueError:
            raise ValueError(
                f"Invalid argument {arg!r}. Specify arguments in the form key=value"
            ) from None
        if allow_hyphens:
            key = key.lstrip("-")

        # parse key@=reference syntax (note =@ would be ambiguous)
        if key.endswith("@"):
            ret[key.removesuffix("@")] = chz.blueprint.Reference(value)
        else:
            ret[key] = chz.blueprint.Castable(value)
    return ret


def beta_blueprint_to_argv(blueprint: chz.Blueprint[_T]) -> list[str]:
    """Returns a list of arguments that would recreate the given blueprint."""

    def to_string(key: str, value: Any) -> str:
        if isinstance(value, chz.blueprint.Castable):
            return f"{key}={value.value}"
        elif isinstance(value, chz.blueprint.Reference):
            return f"{key}@={value.ref}"
        elif isinstance(value, (types.FunctionType, type)):
            return f"{key}={type_repr(value)}"
        if isinstance(value, (str, int, float, bool)):
            return f"{key}={repr(value)}"
        # Probably safe to use repr here, but I'm curious to see how people end up using this
        raise NotImplementedError(
            f"TODO: beta_blueprint_to_argv does not currently convert {value!r} of "
            f"type {type(value)} to string"
        )

    return [to_string(key, value) for key, value in _collapse_layers(blueprint)]


@functools.lru_cache(maxsize=8192)
def _collapse_layer(
    ordered_args: tuple[tuple[str, Any], ...], layer: Layer
) -> tuple[tuple[str, Any], ...]:
    """Collapses `layer` into `ordered_args`, overriding any old keys as necessary."""

    def key_covers(key: str, other: str) -> bool:
        """Returns True iff `key` would match `other`."""
        if "..." not in key:
            return key == other

        # TODO(shantanu): usually this regex is only matched against concrete keys
        # However, here we're matching against other wildcards
        regex = wildcard_key_to_regex(key)
        return regex.fullmatch(other) is not None

    def prune_ordered_args(
        key: str, ordered_args: tuple[tuple[str, Any], ...]
    ) -> tuple[tuple[str, Any], ...]:
        """Prunes the args so far to remove any that would be covered by `key`.

        If `key` is from a later layer, then it overrides any earlier keys that it covers.
        """
        ret = []
        for arg in ordered_args:
            if not key_covers(key, arg[0]):
                ret.append(arg)

        return tuple(ret)

    layer_args: list[tuple[str, Any]] = []
    for key, _ in layer.iter_keys():
        maybe_kv = layer.get_kv(key)
        assert maybe_kv is not None, f"missing layer kv for {key=}"
        got_key, got_value = maybe_kv
        assert got_key == key, f"key mismatch ({key} != {got_key})"
        # Remove any previous args that would be overwritten by this one.
        ordered_args = prune_ordered_args(key, ordered_args)
        layer_args.append((key, got_value))
    # Commit the new layer.
    return ordered_args + tuple(layer_args)


def _collapse_layers(blueprint: chz.Blueprint[_T]) -> list[tuple[str, Any]]:
    """Collapses the layers of a blueprint into a list of key-value pairs.

    These could be applied as a single layer to a new blueprint to recreate the original.
    """
    ordered_args: tuple[tuple[str, Any], ...] = tuple()

    for layer in blueprint._arg_map._layers:
        ordered_args = _collapse_layer(ordered_args, layer)

    return list(ordered_args)
