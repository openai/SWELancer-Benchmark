"""

It's a fair question why this module exists, instead of using something third party.

There are two things I would have liked to farm out: 1) is_subtype_instance, 2) _simplistic_try_cast.

For is_subtype_instance, I would have liked to use `typeguard`. Unfortunately, the `typeguard`
version we were on did not support a lot of basic things. We couldn't upgrade either, because the
new version had breaking changes and more importantly created ref cycles in places that caused us
to hold on to GPU tensors for longer than we should have, causing GPU OOMs. Update: I eventually
got this fixed upstream.

For _simplistic_try_cast, despite its name, seems to work better than most things out there for our
use case. This is also nice to be able to customise for chz's purposes.

I also have another motivation, which is by writing my own Python runtime type checker, I'll
become a better maintainer of typing.py / typing_extensions.py upstream.

"""

import ast
import collections.abc
import functools
import hashlib
import inspect
import operator
import sys
import types
import typing

import typing_extensions


def type_repr(typ) -> str:
    # Similar to typing._type_repr
    if isinstance(typ, (types.GenericAlias, typing._GenericAlias)):
        if typ.__origin__.__module__ in ("typing", "typing_extensions", "collections.abc"):

            if typ.__origin__ is collections.abc.Callable:
                return repr(typ).removeprefix("collections.abc.").removeprefix("typing.")

            # Based on typing._GenericAlias.__repr__
            name = typ.__origin__.__name__
            if typ.__args__:
                args = ", ".join([type_repr(a) for a in typ.__args__])
            else:
                args = "()"
            return f"{name}[{args}]"

        return repr(typ)

    if isinstance(typ, (type, types.FunctionType)):
        module = getattr(typ, "__module__", None)
        name = getattr(typ, "__qualname__", None)
        if name is None:
            name = getattr(typ, "__name__", None)
        if name is not None:
            if module == "typing":
                return f"{module}.{name}"
            if module is not None and module != "builtins" and module != "__main__":
                return f"{module}:{name}"
            return name

    if typ is ...:
        return "..."
    return repr(typ)


def _approx_type_to_bytes(t) -> bytes:
    # This tries to keep the resulting value similar with and without __future__ annotations
    # As a result, the conversion is approximate. For instance, `builtins.float` and
    # `class float: ...` will look the same.
    # If you need something more discerning, maybe just use pickle? Although note that pickle
    # doesn't work on at least forward refs and non-module level typevars
    origin = getattr(t, "__origin__", None)
    args = getattr(t, "__args__", ())

    if origin is None:
        if isinstance(t, type):
            # don't use t.__module__, so that we're more likely to preserve hashes
            # with and without future annotations
            origin_bytes = t.__name__.encode("utf-8")
        elif isinstance(t, typing._SpecialForm):
            origin_bytes = t._name.encode("utf-8")
        elif isinstance(t, typing.TypeVar):
            origin_bytes = t.__name__.encode("utf-8")
        elif isinstance(t, typing.ForwardRef):
            origin_bytes = t.__forward_arg__.encode("utf-8")
        elif isinstance(t, str):
            origin_bytes = t.encode("utf-8")
        elif isinstance(t, (bytes, int, type(...), type(None))):
            # enums?
            origin_bytes = repr(t).encode("utf-8")
        else:
            raise TypeError(f"Cannot convert {t} of {type(t)} to bytes")
    else:
        origin_bytes = _approx_type_to_bytes(origin)

    arg_bytes = (b"[" + b",".join(_approx_type_to_bytes(a) for a in args) + b"]") if args else b""
    return origin_bytes + arg_bytes


def approx_type_hash(t) -> str:
    return hashlib.sha1(_approx_type_to_bytes(t)).hexdigest()


def eval_in_context(annot: str, obj: object) -> typing.Any:
    # Based on inspect.get_annotations
    if isinstance(obj, type):
        obj_globals = None
        module_name = getattr(obj, "__module__", None)
        if module_name:
            module = sys.modules.get(module_name, None)
            if module:
                obj_globals = getattr(module, "__dict__", None)
        obj_locals = dict(vars(obj))
        unwrap = obj
    elif isinstance(obj, types.ModuleType):
        obj_globals = getattr(obj, "__dict__", None)
        obj_locals = None
        unwrap = None
    elif callable(obj):
        obj_globals = getattr(obj, "__globals__", None)
        obj_locals = None
        unwrap = obj
    elif obj is None:
        obj_globals = None
        obj_locals = None
        unwrap = None
    else:
        raise TypeError(f"{obj!r} is not a module, class, or callable.")

    if unwrap is not None:
        while True:
            if hasattr(unwrap, "__wrapped__"):
                unwrap = unwrap.__wrapped__
                continue
            if isinstance(unwrap, functools.partial):
                unwrap = unwrap.func
                continue
            break
        if hasattr(unwrap, "__globals__"):
            obj_globals = unwrap.__globals__

    assert isinstance(annot, str)
    return eval(annot, obj_globals, obj_locals)


if sys.version_info >= (3, 11):
    typing_Never = (
        typing.NoReturn,
        typing_extensions.NoReturn,
        typing_extensions.Never,
        typing.Never,
    )
else:
    typing_Never = (typing.NoReturn, typing_extensions.NoReturn, typing_extensions.Never)


TypeForm = object
InstantiableType: typing.TypeAlias = type | types.GenericAlias  # | typing._GenericAlias


def is_instantiable_type(t: TypeForm) -> typing.TypeGuard[InstantiableType]:
    origin = getattr(t, "__origin__", t)
    return isinstance(origin, type) and origin is not type


def is_union_type(t: TypeForm) -> bool:
    origin = getattr(t, "__origin__", t)
    return origin is typing.Union or isinstance(t, types.UnionType)


def is_typed_dict(t: TypeForm) -> bool:
    return isinstance(t, (typing._TypedDictMeta, typing_extensions._TypedDictMeta))


class CastError(Exception):
    pass


def _sort_for_union_preference(typs: tuple[TypeForm, ...]):
    def sort_key(typ):
        typ = getattr(typ, "__origin__", typ)
        if typ is str:
            # sort str to last, because anything can be cast to str
            return 1
        if typ is typing.Literal or typ is typing_extensions.Literal:
            # sort literals to first, because they exact match
            return -2
        if typ is type(None) or typ is None:
            # None exact matches as well (like all singletons)
            return -1
        return 0

    # note this is a stable sort, so we preserve user ordering
    return sorted(typs, key=sort_key)


def is_args_unpack(t: TypeForm) -> bool:
    return getattr(t, "__unpacked__", False) or getattr(t, "__origin__", t) in (
        typing.Unpack,
        typing_extensions.Unpack,
    )


def is_kwargs_unpack(t: TypeForm) -> bool:
    return getattr(t, "__origin__", t) in (typing.Unpack, typing_extensions.Unpack)


def _unpackable_arg_length(t: TypeForm) -> tuple[int, bool]:
    item_args = None
    if getattr(t, "__unpacked__", False):
        assert t.__origin__ is tuple  # TODO
        item_args = t.__args__
    elif getattr(t, "__origin__", t) in (typing.Unpack, typing_extensions.Unpack):
        assert len(t.__args__) == 1
        assert t.__args__[0].__origin__ is tuple
        item_args = t.__args__[0].__args__
    else:
        return (1, False)

    if not item_args or item_args[-1] is ...:
        assert len(item_args) == 2
        return (0, True)

    min_length = 0
    unbounded = False
    for item_arg in item_args:
        arg_length, arg_unbounded = _unpackable_arg_length(item_arg)
        min_length += arg_length
        unbounded |= arg_unbounded
    return (min_length, unbounded)


def _cast_unpacked_tuples(
    inst_items: list[str], args: tuple[TypeForm, ...]
) -> tuple[typing.Any, ...]:

    # Cursed PEP 646 stuff
    arg_lengths = [_unpackable_arg_length(arg) for arg in args]
    min_length = sum(arg_length for arg_length, _ in arg_lengths)

    if len(inst_items) < min_length:
        raise CastError(
            f"Could not cast {repr(','.join(inst_items))} to {type_repr(tuple[*args])} "
            "because of length mismatch"
        )

    ret = []
    i = 0
    for arg, (arg_length, arg_unbounded) in zip(args, arg_lengths):
        if is_args_unpack(arg):
            if arg_unbounded:
                arg_length += len(inst_items) - min_length
                min_length = len(inst_items)
            if getattr(arg, "__origin__", arg) in (typing.Unpack, typing_extensions.Unpack):
                assert len(arg.__args__) == 1
                assert arg.__args__[0].__origin__ is tuple
                arg = arg.__args__[0]

            arg = arg.__args__
            if len(arg) == 0:
                ret.extend(inst_items[i : i + arg_length])
            elif len(arg) == 2 and arg[-1] is ...:
                ret.extend(
                    _cast_unpacked_tuples(inst_items[i : i + arg_length], (arg[0],) * arg_length)
                )
            else:
                ret.extend(_cast_unpacked_tuples(inst_items[i : i + arg_length], arg))
        else:
            assert arg_length == 1
            assert not arg_unbounded
            ret.append(_simplistic_try_cast(inst_items[i], arg))

        i += arg_length
    return tuple(ret)


def _simplistic_try_cast(inst_str: str, typ: TypeForm):
    origin = getattr(typ, "__origin__", typ)
    if is_union_type(origin):
        # sort str to last spot
        args = _sort_for_union_preference(getattr(typ, "__args__", ()))
        for arg in args:
            try:
                return _simplistic_try_cast(inst_str, arg)
            except CastError:
                pass
        raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}")

    if origin is typing.Any or origin is typing_extensions.Any or origin is object:
        try:
            return ast.literal_eval(inst_str)
        except (ValueError, SyntaxError):
            pass
        # Also accept some lowercase spellings
        if inst_str in {"true", "false"}:
            return inst_str == "true"
        if inst_str in {"none", "null", "NULL"}:
            return None
        return inst_str

    if origin is typing.Literal or origin is typing_extensions.Literal:
        values_by_type = {}
        for arg in getattr(typ, "__args__", ()):
            values_by_type.setdefault(type(arg), []).append(arg)
        for literal_typ, literal_values in values_by_type.items():
            try:
                value = _simplistic_try_cast(inst_str, literal_typ)
                if value in literal_values:
                    return value
            except CastError:
                pass
        raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}")

    if origin is None or origin is type(None):
        if inst_str == "None":
            return None
        raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}")

    if origin is bool:
        if inst_str in {"t", "true", "True", "1"}:
            return True
        if inst_str in {"f", "false", "False", "0"}:
            return False
        raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}")

    if origin is str:
        return inst_str

    if origin is float:
        try:
            return float(inst_str)
        except ValueError as e:
            raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}") from e
    if origin is int:
        try:
            return int(inst_str)
        except ValueError as e:
            raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}") from e

    if origin is list or origin is collections.abc.Sequence or origin is collections.abc.Iterable:
        if not inst_str:
            return []
        args = getattr(typ, "__args__", ())
        item_type = args[0] if args else typing.Any

        if inst_str[0] in ("[", "("):
            try:
                value = ast.literal_eval(inst_str)
            except (ValueError, SyntaxError):
                raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}") from None
            if is_subtype_instance(value, typ):
                return value
            raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}")

        inst_items = inst_str.split(",") if inst_str else []
        ret = [_simplistic_try_cast(item, item_type) for item in inst_items]
        if origin is list:
            return ret
        return tuple(ret)

    if origin is tuple:
        args = getattr(typ, "__args__", ())
        inst_items = inst_str.split(",") if inst_str else []
        if len(args) == 0:
            return tuple(inst_items)
        if len(args) == 2 and args[-1] is ...:
            item_type = args[0]
            return tuple(_simplistic_try_cast(item, item_type) for item in inst_items)

        num_unpack = sum(is_args_unpack(arg) for arg in args)
        if num_unpack == 0:
            # Great, normal heterogenous tuple
            if len(args) != len(inst_items):
                raise CastError(
                    f"Could not cast {repr(inst_str)} to {type_repr(typ)} because of length mismatch"
                    + (
                        f". Homogeneous tuples should be typed as tuple[{type_repr(args[0])}, ...] not tuple[{type_repr(args[0])}]"
                        if len(args) == 1
                        else ""
                    )
                )
            return tuple(
                _simplistic_try_cast(item, item_typ) for item, item_typ in zip(inst_items, args)
            )
        else:
            # Cursed PEP 646 stuff
            return _cast_unpacked_tuples(inst_items, args)

    if "torch" in sys.modules:
        import torch

        if origin is torch.dtype:
            value = getattr(torch, inst_str, None)
            if value and isinstance(value, torch.dtype):
                return value
            raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}")

    if "enum" in sys.modules:
        import enum

        if issubclass(origin, enum.Enum):
            try:
                # Look up by name
                return origin[inst_str]
            except KeyError:
                pass

            # Fallback to looking up by value
            for member in origin:
                try:
                    value = _simplistic_try_cast(inst_str, type(member.value))
                except CastError:
                    continue
                if value == member.value:
                    return member
            raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}")

    if "fractions" in sys.modules:
        import fractions

        if origin is fractions.Fraction:
            try:
                return fractions.Fraction(inst_str)
            except ValueError as e:
                raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}") from e

    if "pathlib" in sys.modules:
        import pathlib

        if origin is pathlib.Path:
            return pathlib.Path(inst_str)

    if not isinstance(origin, type):
        raise CastError(f"Unrecognised type object {type_repr(typ)}")

    if hasattr(origin, "__chz_cast__"):
        return origin.__chz_cast__(inst_str)

    raise CastError(f"Could not cast {repr(inst_str)} to {type_repr(typ)}")


def is_subtype(left: TypeForm, right: TypeForm) -> bool:
    left_origin = getattr(left, "__origin__", left)
    left_args = getattr(left, "__args__", ())
    right_origin = getattr(right, "__origin__", right)
    right_args = getattr(right, "__args__", ())

    if left_origin is typing.Any or left_origin is typing_extensions.Any:
        return True
    if right_origin is typing.Any or right_origin is typing_extensions.Any:
        return True
    # TODO: handle other special forms

    try:
        if not issubclass(left_origin, right_origin):
            return False
    except TypeError:
        return False

    # see comments in is_subtype_instance
    # TODO: add invariance
    # TODO: think about some of this logic more carefully
    if hasattr(left_origin, "__class_getitem__") and hasattr(right_origin, "__class_getitem__"):
        if (
            issubclass(right_origin, collections.abc.Mapping)
            and typing.Generic not in left_origin.__mro__
            and typing.Generic not in right_origin.__mro__
        ):
            if left_args:
                left_key, left_value = left_args
            else:
                left_key, left_value = typing.Any, typing.Any
            if right_args:
                right_key, right_value = right_args
            else:
                right_key, right_value = typing.Any, typing.Any
            return is_subtype(left_key, right_key) and is_subtype(left_value, right_value)

        if left_origin is tuple and right_origin is tuple:
            if not left_args:
                left_args = (typing.Any, ...)
            if not right_args:
                right_args = (typing.Any, ...)
            if len(right_args) == 2 and right_args[1] is ...:
                return all(is_subtype(left_arg, right_args[0]) for left_arg in left_args)
            if len(left_args) == 2 and left_args[1] is ...:
                return False
            return len(left_args) == len(right_args) and all(
                is_subtype(left_arg, right_arg)
                for left_arg, right_arg in zip(left_args, right_args)
            )

        if (
            issubclass(right_origin, collections.abc.Iterable)
            and typing.Generic not in left_origin.__mro__
            and typing.Generic not in right_origin.__mro__
        ):
            if left_args:
                (left_item,) = left_args
            else:
                left_item = typing.Any
            if right_args:
                (right_item,) = right_args
            else:
                right_item = typing.Any
            return is_subtype(left_item, right_item)

    return True


def is_subtype_instance(inst: typing.Any, typ: TypeForm) -> bool:
    if typ is typing.Any or typ is typing_extensions.Any:
        return True

    if isinstance(typ, typing.TypeVar):
        if typ.__constraints__:
            # types must match exactly
            return any(
                type(inst) is getattr(c, "__origin__", c) and is_subtype_instance(inst, c)
                for c in typ.__constraints__
            )
        if typ.__bound__:
            return is_subtype_instance(inst, typ.__bound__)
        return True

    if isinstance(typ, typing.NewType):
        return isinstance(inst, typ.__supertype__)

    origin: typing.Any
    args: typing.Any
    if sys.version_info >= (3, 10) and isinstance(typ, types.UnionType):
        origin = typing.Union
    else:
        origin = getattr(typ, "__origin__", typ)

    args = getattr(typ, "__args__", ())
    del typ

    if origin is typing.Union:
        return any(is_subtype_instance(inst, t) for t in args)
    if origin is typing.Literal:
        return inst in args

    if origin is typing.LiteralString:
        return isinstance(inst, str)

    if is_typed_dict(origin):
        if not isinstance(inst, dict):
            return False

        for k, v in typing.get_type_hints(origin).items():
            if k in inst:
                if not is_subtype_instance(inst[k], v):
                    return False
            elif k in origin.__required_keys__:
                return False
        return True

    # Pydantic implements generics in a special way. Just delegate validation to Pydantic.
    # Note that all pydantic models have __pydantic_generic_metadata__, even non-generic ones.
    if hasattr(origin, "__pydantic_generic_metadata__"):
        from pydantic import ValidationError

        try:
            origin.model_validate(inst)
            return True
        except ValidationError:
            return False

    # We're done handling special forms, now just need to handle things like generics
    if not isinstance(origin, type):
        # TODO: handle other special forms before exit on this branch
        return False
    if not isinstance(inst, origin):
        # PEP 484 duck type compatibility
        if origin is complex and isinstance(inst, (int, float)):
            return True
        if origin is float and isinstance(inst, int):
            return True
        if origin is bytes and isinstance(inst, (bytearray, memoryview)):
            # TODO: maybe remove bytearray and memoryview ducktyping based on PEP 688
            return True

        if inst in typing_Never:
            return True
        if issubclass(type(inst), typing_extensions.Any) or (
            sys.version_info >= (3, 11) and issubclass(type(inst), typing.Any)
        ):
            return True
        return False

    assert isinstance(inst, origin)
    if not args:
        return True

    # TODO: there's some confusion when checking issubclass against a generic collections.abc
    # base class, since you don't actually know whether the generic args of typ / origin correspond
    # to the generic args of the base class. So if we detect a user defined generic (i.e. based
    # on presence of Generic in the mro), we just fall back and don't assume we know the semantics
    # of what the generic args are.
    if issubclass(origin, collections.abc.Mapping) and typing.Generic not in origin.__mro__:
        key_type, value_type = args
        return all(
            is_subtype_instance(key, key_type) and is_subtype_instance(value, value_type)
            for key, value in inst.items()
        )
    if origin is tuple:
        if len(args) == 2 and args[1] is ...:
            return all(is_subtype_instance(i, args[0]) for i in inst)
        if len(inst) != len(args):
            return False
        return all(is_subtype_instance(i, t) for i, t in zip(inst, args))

    if issubclass(origin, collections.abc.Iterable) and typing.Generic not in origin.__mro__:
        (item_type,) = args
        return all(is_subtype_instance(item, item_type) for item in inst)

    if origin is type:
        (type_type,) = args
        return issubclass(inst, type_type)
    if origin is collections.abc.Callable:
        try:
            signature = inspect.signature(inst)
        except ValueError:
            return True
        *params, ret = args
        if params != [...]:
            try:
                bound = signature.bind(*params)
            except TypeError:
                return False
            for param, callable_param_type in bound.arguments.items():
                param = signature.parameters[param]
                param_annot = param.annotation
                # ooh, contravariance
                if param_annot is not param.empty:
                    if isinstance(param_annot, str):
                        param_annot = eval_in_context(param_annot, inst)
                    if param.kind is param.VAR_POSITIONAL:
                        if any(not is_subtype(cpt, param_annot) for cpt in callable_param_type):
                            return False
                    elif not is_subtype(callable_param_type, param_annot):
                        return False
        if signature.return_annotation is not signature.empty:
            ret_annot = signature.return_annotation
            if isinstance(ret_annot, str):
                ret_annot = eval_in_context(ret_annot, inst)
            # inspect.signature(Cls) will have Cls.__init__, which is annotated as -> None
            if not (isinstance(inst, type) and ret_annot is None and is_subtype(inst, ret)):
                if ret_annot is None:
                    ret_annot = type(None)
                elif ret_annot in typing_Never:
                    ret_annot = ret
                if ret_annot != ret and not is_subtype(ret_annot, ret):
                    return False
        return True

    # We don't really know how to handle user defined generics
    if hasattr(inst, "__orig_class__"):
        # If we have an __orig_class__ and the origins match, check the args (assuming that they
        # are invariant, although maybe covariant is a better guess?)
        if inst.__orig_class__.__origin__ is origin:
            return inst.__orig_class__.__args__ == args
    # Otherwise, fail open
    return True

    # TODO: overloads
    # TODO: more protocols, callback protocol
    # TODO: non runtime checkable protocols
    # TODO: paramspec / concatenate
    # TODO: typeguard
    # TODO: annotated
    # TODO: forwardref, future annotations
    # TODO: self
    # TODO: pep 692 unpack
    # TODO: typevartuple??


def simplified_union(types):
    if len(types) == 0:
        return typing.Never
    if len(types) == 1:
        return types[0]

    union_types = []
    for typ in types:
        if getattr(typ, "__args__", None) is None and any(
            issubclass(typ, member) for member in union_types
        ):
            continue
        union_types.append(typ)

    types = union_types
    union_types = []
    for typ in reversed(types):
        if getattr(typ, "__args__", None) is None and any(
            issubclass(typ, member) for member in union_types
        ):
            continue
        union_types.append(typ)

    return functools.reduce(operator.or_, union_types)


def _simplistic_type_of_value(value: object) -> TypeForm:
    # TODO: maybe remove this? Its current use is in diagnostics (for providing the actual type),
    # but is_subtype_instance is in a position to provide better diagnostics
    if hasattr(type(value), "__class_getitem__"):
        if isinstance(value, collections.abc.Mapping) and typing.Generic not in type(value).__mro__:
            return type(value)[
                simplified_union([_simplistic_type_of_value(k) for k in value.keys()]),
                simplified_union([_simplistic_type_of_value(v) for v in value.values()]),
            ]
        if isinstance(value, tuple):
            if len(value) <= 10:
                return type(value)[tuple(_simplistic_type_of_value(v) for v in value)]
            return type(value)[simplified_union([_simplistic_type_of_value(v) for v in value]), ...]
        if (
            isinstance(value, collections.abc.Iterable)
            and typing.Generic not in type(value).__mro__
        ):
            return type(value)[simplified_union([_simplistic_type_of_value(v) for v in value])]

    if isinstance(value, type):
        return type[value]

    return type(value)
