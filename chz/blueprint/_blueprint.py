from __future__ import annotations

import ast
import collections.abc
import functools
import inspect
import io
import sys
import textwrap
import typing
from dataclasses import dataclass
from typing import Any, Callable, Final, Generic, Mapping, Protocol, TypeVar

import chz
from chz.blueprint._argmap import ArgumentMap, Layer, join_arg_path
from chz.blueprint._argv import argv_to_blueprint_args
from chz.blueprint._entrypoint import (
    EntrypointHelpException,
    ExtraneousBlueprintArg,
    InvalidBlueprintArg,
    MissingBlueprintArg,
)
from chz.blueprint._lazy import (
    Evaluatable,
    ParamRef,
    Thunk,
    Value,
    check_reference_targets,
    evaluate,
)
from chz.field import Field
from chz.tiepin import (
    CastError,
    _simplistic_try_cast,
    eval_in_context,
    is_kwargs_unpack,
    is_subtype_instance,
    is_typed_dict,
    type_repr,
)
from chz.util import _MISSING_TYPE, MISSING

_T = TypeVar("_T")
_T_cov = TypeVar("_T_cov", covariant=True)


class SpecialArg: ...


class Castable(SpecialArg):
    """A wrapper class for str if you want a Blueprint value to be magically type aware casted."""

    def __init__(self, value: str) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Castable({self.value!r})"

    def __hash__(self) -> int:
        return hash(self.value)


class Reference(SpecialArg):
    """A reference to another parameter in a Blueprint."""

    def __init__(self, ref: str) -> None:
        if "..." in ref:
            raise ValueError("Cannot use wildcard as a reference target")
        self.ref = ref

    def __repr__(self) -> str:
        return f"Reference({self.ref!r})"


@dataclass(frozen=True)
class _MakeResult:
    # `value_mapping` is a dictionary mapping from parameter paths to Evaluatable values.
    # This ultimately contains all the kinds of values we will use in instantiation.
    # See chz.blueprint._lazy.evaluate for an example of using Evaluatable.
    value_mapping: dict[str, Evaluatable]

    # `all_params` is a dictionary containing all parameters we discover, mapping from that param
    # path to the parameter. Note what parameters we discover will depend on polymorphic
    # construction via meta_factories. We use all_params to provide a useful --help (and various
    # other things, e.g. detect clobbering when checking for extraneous arguments)
    all_params: dict[str, _Param]

    # `used_args` is a set of (key, layer_index) tuples that we use to track which arguments from
    # arg_map we've used. We use this to check for extraneous arguments.
    used_args: set[tuple[str, int]]

    # `meta_factory_value` records what meta_factory we're using. This makes --help more
    # understandable in the presence of polymorphism, especially when factories come from
    # blueprint_unspecified. It's conceptually the same information as in Thunk.fn in value_mapping,
    # but preserves user input for variadics or generics (instead of being a constructor function)
    meta_factory_value: dict[str, Any]

    # `missing_params` is a list of parameters we know need are required but haven't been
    # specified. In theory, this is unnecessary because `__init__` will raise an error if
    # a required param is missing, but this improves diagnostics.
    missing_params: list[str]


class Blueprint(Generic[_T_cov]):
    def __init__(self, target: type[_T_cov] | Callable[..., _T_cov]) -> None:
        """Instantiate a Blueprint.

        Args:
            target: The target object or callable we will instantiate or call.
        """
        if not callable(target):
            raise ValueError(f"{target} is not callable")
        self.target: Any = target

        self._arg_map = ArgumentMap([])

    def clone(self) -> "Blueprint[_T_cov]":
        """Make a copy of this Blueprint."""
        return Blueprint(self.target).apply(self)

    def apply(
        self,
        values: Blueprint[_T_cov] | Mapping[str, Any],
        layer_name: str | None = None,
        *,
        subpath: str | None = None,
        strict: bool = False,
    ) -> Blueprint[_T_cov]:
        """Modify this Blueprint by partially applying some arguments.

        Args:
            values: The values to partially apply to this Blueprint
            layer_name: The name of the layer to add (allows identification of the source of values)
            subpath: A subpath to nest the argument names under
            strict: Whether to eagerly check for extraneous arguments. This may not work well in
                cases where a polymorphic field is applied later.
        """
        if isinstance(values, Mapping):
            self._arg_map.add_layer(Layer(values, layer_name).nest_subpath(subpath))

        elif isinstance(values, Blueprint):
            if subpath is None:
                if values.target is not self.target:
                    raise ValueError(
                        f"Cannot apply Blueprint for {type_repr(values.target)} to Blueprint for "
                        f"{type_repr(self.target)}"
                    )
            for layer in values._arg_map._layers:
                self._arg_map.add_layer(layer.nest_subpath(subpath))
        else:
            raise TypeError(f"Expected dict or Blueprint, got {type(values)}")

        if strict:
            r = self._make_lazy()
            self._arg_map.check_extraneous(r.used_args, r.all_params.keys(), target=self.target)

        return self

    def apply_from_argv(
        self, argv: list[str], allow_hyphens: bool = False, layer_name: str = "command line"
    ) -> Blueprint[_T_cov]:
        """Apply arguments from argv to this Blueprint."""
        values = argv_to_blueprint_args(
            [a for a in argv if a != "--help"], allow_hyphens=allow_hyphens
        )

        self.apply(values, layer_name=layer_name)

        if "--help" in argv:
            argv.remove("--help")
            raise EntrypointHelpException(self.get_help())
        return self

    def _make_lazy(self) -> _MakeResult:
        all_params: dict[str, _Param] = {}
        used_args: set[tuple[str, int]] = set()
        meta_factory_value: dict[str, Any] = {}
        missing_params: list[str] = []
        value_mapping = _construct_blueprint(
            self.target,
            "",
            self._arg_map,
            all_params=all_params,
            used_args=used_args,
            meta_factory_value=meta_factory_value,
            missing_params=missing_params,
        )
        if isinstance(value_mapping, ConstructionError):
            raise value_mapping
        return _MakeResult(
            value_mapping=value_mapping,
            all_params=all_params,
            used_args=used_args,
            meta_factory_value=meta_factory_value,
            missing_params=missing_params,
        )

    def make(self) -> _T_cov:
        """Instantiate or call the target object or callable."""
        r = self._make_lazy()
        self._arg_map.check_extraneous(r.used_args, r.all_params.keys(), target=self.target)
        check_reference_targets(r.value_mapping, r.all_params.keys())
        # Note we check for extraneous args first, so we get better errors for typos
        if r.missing_params:
            raise MissingBlueprintArg(
                f"Missing required arguments for parameter(s): {', '.join(r.missing_params)}"
            )
        # __chz_blueprint__
        return evaluate(r.value_mapping)

    def make_from_argv(self, argv: list[str] | None = None, allow_hyphens: bool = False) -> _T_cov:
        """Like make, but suitable for command line entrypoints.

        This will apply arguments from argv to this Blueprint before attempting to make the target.
        If "--help" is in argv, this will print help text and exit.
        """
        if argv is None:
            argv = sys.argv[1:]

        self.apply_from_argv(argv, allow_hyphens=allow_hyphens)

        return self.make()

    def get_help(self) -> str:
        """Get help text for this Blueprint.

        Note that applied arguments may affect output here, e.g. in case of polymorphically
        constructed fields.
        """
        r = self._make_lazy()

        f = io.StringIO()
        output = functools.partial(print, file=f)

        try:
            self._arg_map.check_extraneous(r.used_args, r.all_params.keys(), target=self.target)
        except ExtraneousBlueprintArg as e:
            output(f"WARNING: {e}\n")
        try:
            check_reference_targets(r.value_mapping, r.all_params.keys())
        except InvalidBlueprintArg as e:
            output(f"WARNING: {e}\n")

        if r.missing_params:
            output(
                f"WARNING: Missing required arguments for parameter(s): {', '.join(r.missing_params)}\n"
            )

        output(f"Entry point: {type_repr(self.target)}")
        output()
        if getattr(self.target, "__doc__", None):
            output(textwrap.indent(self.target.__doc__, "  "))
            output()

        param_output = []
        for param_path, param in r.all_params.items():
            # TODO: cast or meta_factory info, not just type
            found_arg = self._arg_map.get_kv(param_path)
            if found_arg is None:
                if param_path in r.meta_factory_value:
                    found_arg_str = type_repr(r.meta_factory_value[param_path]) + " (meta_factory)"
                elif param.default is not None:
                    found_arg_str = param.default.to_help_str() + " (default)"
                elif (
                    param.meta_factory is not None
                    and (factory := param.meta_factory.unspecified_factory()) is not None
                    and factory is not param.type
                ):
                    found_arg_str = type_repr(factory) + " (blueprint_unspecified)"
                else:
                    found_arg_str = "-"
            else:
                if isinstance(found_arg.value, Castable):
                    found_arg_str = repr(found_arg.value.value)[1:-1]
                elif isinstance(found_arg.value, Reference):
                    found_arg_str = f"@={found_arg.value.ref}"
                else:
                    found_arg_str = repr(found_arg.value)
                if found_arg.layer_name:
                    found_arg_str += f" (from {found_arg.layer_name})"

            param_output.append((param_path, type_repr(param.type), found_arg_str, param.doc))

        clip = 40
        lens = tuple(min(clip, max(map(len, column))) for column in zip(*param_output))

        def pad(s: str, l: int) -> str:
            if len(s) <= l:
                return s.ljust(l)
            return s.ljust(len(s) + (-len(s)) % 20)

        output("Arguments:")
        for p, typ, arg, doc in param_output:
            output(f"  {pad(p, lens[0])}  {pad(typ, lens[1])}  {pad(arg, lens[2])}  {doc}".rstrip())

        return f.getvalue()


def _lambda_repr(fn) -> str | None:
    try:
        src = inspect.getsource(fn).strip()
        tree = ast.parse(src)
        nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Lambda)]
        if len(nodes) != 1:
            return None
        return ast.unparse(nodes[0])
    except Exception:
        return None


@dataclass(frozen=True, kw_only=True)
class _Default:
    value: Any | _MISSING_TYPE
    factory: Callable[..., Any] | _MISSING_TYPE

    def to_help_str(self) -> str:
        if self.factory is not MISSING:
            if getattr(self.factory, "__name__", None) == "<lambda>":
                return f"({_lambda_repr(self.factory)})()" or "<default>"
            # type_repr works reasonably well for functions too
            return f"{type_repr(self.factory)}()"

        ret = repr(self.value)
        if len(ret) > 40:
            return "<default>"
        return ret

    def instantiate(self) -> Any:
        if not isinstance(self.factory, _MISSING_TYPE):
            return self.factory()
        return self.value

    @classmethod
    def from_field(cls, field: Field) -> _Default | None:
        if field._default is MISSING and field._default_factory is MISSING:
            return None
        return _Default(value=field._default, factory=field._default_factory)

    @classmethod
    def from_inspect_param(cls, sigparam: inspect.Parameter) -> _Default | None:
        if sigparam.default is sigparam.empty:
            return None
        return _Default(value=sigparam.default, factory=MISSING)


@dataclass(frozen=True, kw_only=True)
class _Param:
    name: str
    type: Any
    meta_factory: chz.factories.MetaFactory | None
    default: _Default | None
    doc: str
    blueprint_cast: Callable[[str], object] | None
    metadata: dict[str, Any]

    def cast(self, value: str) -> object:
        # If we have a field-level cast, always use that!
        if self.blueprint_cast is not None:
            return self.blueprint_cast(value)

        # If we have a meta_factory, route casting through it. This allows user expectations
        # of types that result from casting to better match their expectations from polymorphic
        # construction (e.g. using default_cls from chz.factories.subclass)
        if self.meta_factory is not None:
            return self.meta_factory.perform_cast(value)

        # TODO: maybe MetaFactory should have default impl and this should be:
        # return chz.factories.MetaFactory().perform_cast(value, self.type)
        return _simplistic_try_cast(value, self.type)


def _collect_params(obj) -> list[_Param] | ConstructionError:
    obj_origin = getattr(obj, "__origin__", obj)  # handle generic chz classes

    params: list[_Param] = []
    if hasattr(obj_origin, "__chz_fields__"):
        for field in obj_origin.__chz_fields__.values():
            params.append(
                _Param(
                    name=field.logical_name,
                    type=field.x_type,
                    meta_factory=field.meta_factory,
                    default=_Default.from_field(field),
                    doc=field._doc,
                    blueprint_cast=field._blueprint_cast,
                    metadata=field.metadata,
                )
            )
        return params

    if callable(obj):
        try:
            signature = inspect.signature(obj)
        except ValueError:
            return ConstructionError(f"Failed to get signature for {obj.__name__}")
        for i, (name, sigparam) in enumerate(signature.parameters.items()):
            if sigparam.kind == sigparam.POSITIONAL_ONLY:
                if sigparam.default is sigparam.empty:
                    return ConstructionError(
                        f"Cannot construct {obj.__name__} because it has positional-only "
                        f"parameter {name} without a default"
                    )
                continue
            if sigparam.kind == sigparam.VAR_POSITIONAL:
                return ConstructionError(
                    f"Cannot collect parameters from {obj.__name__} due to *args parameter {name}"
                )

            param_annot: Any
            if sigparam.annotation is sigparam.empty:
                if i == 0 and "." in obj.__qualname__:
                    # potentially first parameter of a method, default the annotation to the class
                    try:
                        cls = getattr(inspect.getmodule(obj), obj.__qualname__.rsplit(".", 1)[0])
                        param_annot = cls
                    except Exception:
                        param_annot = object
                else:
                    param_annot = object
            else:
                param_annot = sigparam.annotation
            if isinstance(param_annot, str):
                param_annot = eval_in_context(param_annot, obj)

            if sigparam.kind == sigparam.VAR_KEYWORD:
                if not is_kwargs_unpack(param_annot):
                    return ConstructionError(
                        f"Cannot collect parameters from {obj.__name__} due to "
                        f"**kwargs parameter {name}. Only Unpack[TypedDict] is supported."
                    )
                if len(param_annot.__args__) != 1 or not is_typed_dict(param_annot.__args__[0]):
                    return ConstructionError(
                        f"Cannot collect parameters from {obj.__name__}, expected Unpack[TypedDict], not {param_annot}"
                    )
                for key, annotation in typing.get_type_hints(param_annot.__args__[0]).items():
                    # TODO: handle total=False and PEP 655
                    params.append(
                        _Param(
                            name=key,
                            type=annotation,
                            meta_factory=chz.factories.standard(annotation),
                            default=None,
                            doc="",
                            blueprint_cast=None,
                            metadata={},
                        )
                    )
                continue

            # It could be interesting to let function defaults be chz.Field :-)
            # TODO: could be fun to parse function docstring
            params.append(
                _Param(
                    name=name,
                    type=param_annot,
                    meta_factory=chz.factories.standard(param_annot),
                    default=_Default.from_inspect_param(sigparam),
                    doc="",
                    blueprint_cast=None,
                    metadata={},
                )
            )
        # Note params may be empty here if obj doesn't take any parameters.
        # This is usually okay, but has some interaction with fully defaulted subcomponents.
        # See test_nested_all_defaults and variants
        return params

    return ConstructionError(
        f"Could not collect parameters to construct {obj} of type {type_repr(obj)}"
    )


def _collect_variadic_params(
    obj: object, obj_path: str, arg_map: ArgumentMap
) -> tuple[list[_Param], Callable[..., Any], list[Any]] | None:

    obj_origin: Any = getattr(obj, "__origin__", obj)
    if obj_origin not in (
        list,
        tuple,
        collections.abc.Sequence,
        dict,
        collections.abc.Mapping,
    ) and not is_typed_dict(obj_origin):
        return None

    elements = set()
    for subpath in arg_map.subpaths(obj_path, strict=True):
        assert subpath
        if subpath[0] != ".":
            element = subpath.split(".")[0]
            assert element
            elements.add(element)

    if obj_origin in (list, tuple, collections.abc.Sequence):
        max_element = max((int(e) for e in elements), default=-1)
        obj_type_construct = obj_origin

        type_for_index: Callable[[int], type]
        if obj_origin is list:
            element_type = getattr(obj, "__args__", [object])[0]
            type_for_index = lambda i: element_type
            variadic_types = [element_type]

        elif obj_origin is collections.abc.Sequence:
            element_type = getattr(obj, "__args__", [object])[0]
            type_for_index = lambda i: element_type
            variadic_types = [element_type]
            obj_type_construct = tuple

        elif obj_origin is tuple:
            args: tuple[Any, ...] = getattr(obj, "__args__", ())
            if len(args) == 2 and args[-1] is ...:
                # homogeneous tuple
                type_for_index = lambda i: args[0]
                variadic_types = [args[0]]
            else:
                # heterogeneous tuple
                if max_element >= len(args):
                    raise TypeError(
                        f"Tuple type {obj} must take {len(args)} items; "
                        f"arguments for index {max_element} were specified"
                        + (
                            f". Homogeneous tuples should be typed as tuple[{type_repr(args[0])}, ...] not tuple[{type_repr(args[0])}]"
                            if len(args) == 1
                            else ""
                        )
                    )
                type_for_index = lambda i: args[i]
                variadic_types = list(args)
        else:
            raise AssertionError

        params: list[_Param] = []
        for i in range(max_element + 1):
            element_type = type_for_index(i)
            params.append(
                _Param(
                    name=str(i),
                    type=element_type,
                    meta_factory=chz.factories.standard(element_type),
                    default=None,
                    doc="",
                    blueprint_cast=None,
                    metadata={},
                )
            )

        def sequence_constructor(**kwargs):
            return obj_type_construct(kwargs[str(i)] for i in range(max_element + 1))

        obj_constructor = sequence_constructor
        return params, obj_constructor, variadic_types

    elif obj_origin in (dict, collections.abc.Mapping):
        args = getattr(obj, "__args__", ())
        if len(args) == 0:
            element_type = object
        elif len(args) == 2:
            if args[0] is not str:
                if elements:
                    raise TypeError(
                        f"Variadic dict type must take str keys, not {type_repr(args[0])}"
                    )
                return None
            element_type = args[1]
        else:
            raise TypeError(f"Dict type {obj} must take 0 or 2 items")

        params = []
        for element in elements:
            params.append(
                _Param(
                    name=element,
                    type=element_type,
                    meta_factory=chz.factories.standard(element_type),
                    default=None,
                    doc="",
                    blueprint_cast=None,
                    metadata={},
                )
            )

        return params, dict, [element_type]

    elif is_typed_dict(obj_origin):
        params = []
        variadic_types = []
        for key, annotation in typing.get_type_hints(obj_origin).items():
            required = key in obj_origin.__required_keys__

            params.append(
                _Param(
                    name=key,
                    type=annotation,
                    meta_factory=chz.factories.standard(annotation),
                    # Mark the default as NotRequired to improve --help output
                    # We don't actually use the default values in Blueprint since we let
                    # instantiation handle insertion of default values
                    default=(
                        None if required else _Default(value=typing.NotRequired, factory=MISSING)
                    ),
                    doc="",
                    blueprint_cast=None,
                    metadata={},
                )
            )
            variadic_types.append(annotation)

        return params, obj_origin, variadic_types

    else:
        raise AssertionError


_K = TypeVar("_K")
_V = TypeVar("_V", contravariant=True)


class _WriteOnlyMapping(Generic[_K, _V], Protocol):
    def __setitem__(self, __key: _K, __value: _V, /) -> None: ...
    def update(self, __m: Mapping[_K, _V], /) -> None: ...


class ConstructionError(Exception):
    def __init__(self, issue: str) -> None:
        self.issue = issue


def _construct_blueprint(
    obj: Callable[..., _T],
    obj_path: str,
    arg_map: ArgumentMap,
    *,
    # Output parameters, do not use within this function
    # Typing these as write-only should help prevent accidental unsound use within this function
    # See _MakeResult for docs about these parameters
    all_params: _WriteOnlyMapping[str, _Param],
    used_args: set[tuple[str, int]],
    meta_factory_value: _WriteOnlyMapping[str, Any],
    missing_params: list[str],
) -> dict[str, Evaluatable] | ConstructionError:

    obj_constructor = obj
    result = _collect_variadic_params(obj, obj_path, arg_map)
    params: list[_Param] | ConstructionError
    if result is not None:
        params, obj_constructor, _ = result
    else:
        params = _collect_params(obj)
    del obj

    if isinstance(params, ConstructionError):
        return params

    # Ideas:

    # TODO: Allow automatically accessing any attribute on parent for factories?
    # This eases the responsibility of getting the right structure for the config and could mean
    # we don't need to support wildcards? Reduces problems of something not getting specified
    # correctly.
    # "If you need a value, move it one level up."

    # TODO: Allow factories to return blueprints? This would allow for better presets, e.g. you
    # could do model=d4-dev model.n_layers=5

    kwargs: dict[str, ParamRef] = {}
    value_mapping: dict[str, Evaluatable] = {}

    for param in params:
        arg = _construct_arg_for_param(
            param,
            obj_path,
            arg_map,
            all_params=all_params,
            used_args=used_args,
            meta_factory_value=meta_factory_value,
            missing_params=missing_params,
        )
        if arg is None:
            continue
        param_path, sub_value_mapping = arg
        value_mapping.update(sub_value_mapping)
        kwargs[param.name] = ParamRef(param_path)

    value_mapping[obj_path] = Thunk(obj_constructor, kwargs)
    return value_mapping


def _construct_arg_for_param(
    param: _Param,
    obj_path: str,
    arg_map: ArgumentMap,
    *,
    # Output parameters, do not use within this function
    # See _MakeResult for docs about these parameters
    all_params: _WriteOnlyMapping[str, _Param],
    used_args: set[tuple[str, int]],
    meta_factory_value: _WriteOnlyMapping[str, Any],
    missing_params: list[str],
) -> tuple[str, dict[str, Evaluatable]] | None:
    # Returns None if we don't need to pass any value. This doesn't mean there's an error,
    # we might simply want the default or default_factory value.

    param_path: Final = (obj_path + "." if obj_path else "") + param.name
    all_params[param_path] = param

    found_arg = arg_map.get_kv(param_path)

    # If nothing is specified, check if we have a factory we can feed subcomponents to
    # and if there are specified subcomponents we could feed to it
    if found_arg is None:
        if (
            param.meta_factory is not None
            and (factory := param.meta_factory.unspecified_factory()) is not None
        ):
            assert callable(factory)
            sub_all_params: dict[str, _Param] = {}
            sub_missing_params: list[str] = []
            sub_used_args: set[tuple[str, int]] = set()
            sub_meta_factory_value: dict[str, Any] = {}

            value_mapping = _construct_blueprint(
                factory,
                param_path,
                arg_map,
                all_params=sub_all_params,
                used_args=sub_used_args,
                meta_factory_value=sub_meta_factory_value,
                missing_params=sub_missing_params,
            )
            all_params.update(sub_all_params)
            used_args.update(sub_used_args)  # TODO: should this be gated by use?
            meta_factory_value.update(sub_meta_factory_value)

            if not isinstance(value_mapping, ConstructionError):
                thunk = value_mapping[param_path]
                assert isinstance(thunk, Thunk)
                # Only do this if we have subcomponents specified (including wildcards)
                if thunk.kwargs:
                    meta_factory_value[param_path] = factory
                    missing_params.extend(sub_missing_params)
                    return (param_path, value_mapping)

                # Alternatively, if a) we do not have a default, b) we're making a chz object
                # c) we know instantiation would always work, that's fine too.
                # A little special-case-y, but somewhat sane. It turns something that would
                # error due to lack of default into something reasonable.
                # See test_nested_all_defaults and variants
                if (
                    param.default is None
                    and hasattr(factory, "__chz_fields__")
                    and all(p.default is not None for p in sub_all_params.values())
                ):
                    assert not sub_missing_params
                    meta_factory_value[param_path] = factory
                    return (param_path, value_mapping)

                # If we have a default, make sure we don't extend missing_params
                if param.default is None:
                    if sub_missing_params:
                        missing_params.extend(sub_missing_params)
                    else:
                        # Happens if we collect no params, like non-chz field or variadics
                        missing_params.append(param_path)
                else:
                    # If we have a default, do some validation about wildcards + variadics
                    _check_for_wildcard_matching_variadic_top_level(
                        factory, param, param_path, arg_map
                    )

                return None

            assert not sub_missing_params

        # If we have no subcomponents specified or we have no factory, we don't add any kwargs
        # When the object is created, this will be equivalent to:
        # `attr = default` or `attr = default_factory()`

        # If there is no default, we will raise MissingBlueprintArg, instead of relying on the
        # normal Python error during instantiation. We also rely on raising ExtraneousBlueprintArg
        # if there are arguments that go unused.
        # (In the case of Blueprint implementation bugs, if we're missing a param, __init__ will
        # have our back, but the extraneous logic has no backup)
        if param.default is None:
            missing_params.append(param_path)

        return None

    used_args.add((found_arg.key, found_arg.layer_index))
    spec: object = found_arg.value

    # Something is specified, so we must either add something to kwargs or error out

    # If something is specified, and is of the expected type, we just assign it:
    # `attr = spec`
    if not isinstance(spec, SpecialArg) and is_subtype_instance(spec, param.type):
        # (ignore SpecialArg's here, in case param.type is object)
        # TODO: deep copy?
        return (param_path, {param_path: Value(spec)})

    # Otherwise, we see if we can cast it to the expected type:
    # `attr = trycast(spec.value, param.type)`
    if isinstance(spec, Castable):
        # If we have a meta_factory and we have args that are prefixed with the param path, we
        # will always want to construct that (if we successfully casted here when subcomponents
        # are specified, we'd just fail later because those subcomponents would be extraneous)
        if not (param.meta_factory is not None and arg_map.subpaths(param_path, strict=True)):
            try:
                casted_spec = param.cast(spec.value)
                return (param_path, {param_path: Value(casted_spec)})
            except CastError:
                pass

    # ..or if it's a Reference to some other parameter
    if isinstance(spec, Reference):
        if spec.ref == param_path and param.default is not None:
            # See test_blueprint_reference_wildcard_default
            # TODO: this is the only place we instantiate a default
            default = param.default.instantiate()
            return (param_path, {param_path: Value(default)})

        return (param_path, {param_path: ParamRef(spec.ref)})

    # Otherwise, see if it's something that can construct the expected type. For instance,
    # maybe it's a subclass of param.type, or more generally any `Callable[..., param.type]`,
    # in which case we do:
    # `attr = spec(...)`
    if is_subtype_instance(spec, Callable[..., param.type]):
        assert callable(spec)
        factory = spec
        value_mapping = _construct_blueprint(
            factory,
            param_path,
            arg_map,
            all_params=all_params,
            used_args=used_args,
            meta_factory_value=meta_factory_value,
            missing_params=missing_params,
        )
        if isinstance(value_mapping, ConstructionError):
            raise value_mapping
        return (param_path, value_mapping)

    # Otherwise, see if it's something that can be casted into something that can construct
    # the expected type. For instance, maybe it's a string that's the name of a subclass of
    # param.type or "module:func" where module.func is a `func: Callable[..., param.type]`.
    # `attr = trycast(spec, constructor_type)(...)`

    if isinstance(spec, Castable):
        if param.meta_factory is not None:
            try:
                factory = param.meta_factory.from_string(spec.value)
            except chz.factories.MetaFromString as e:
                cast_error = None
                try:
                    param.cast(spec.value)
                except CastError as e2:
                    cast_error = str(e2)
                if cast_error is None:
                    subpaths = arg_map.subpaths(param_path, strict=True)
                    assert subpaths
                    cast_error = f"Not a value, since subparameters were provided (e.g. {join_arg_path(param_path, subpaths[0])!r})"
                raise InvalidBlueprintArg(
                    f"Could not interpret argument {spec.value!r} provided for param {param_path!r}...\n\n"
                    f"- Failed to interpret it as a value:\n{cast_error}\n\n"
                    f"- Failed to interpret it as a factory for polymorphic construction:\n{e}"
                ) from None
            assert callable(factory)
            value_mapping = _construct_blueprint(
                factory,
                param_path,
                arg_map,
                all_params=all_params,
                used_args=used_args,
                meta_factory_value=meta_factory_value,
                missing_params=missing_params,
            )
            if isinstance(value_mapping, ConstructionError):
                raise value_mapping
            meta_factory_value[param_path] = factory
            return (param_path, value_mapping)

        # This cast is just to raise the error we caught previously
        try:
            param.cast(spec.value)
        except CastError as e:
            raise InvalidBlueprintArg(
                f"Could not cast {spec.value!r} to {type_repr(param.type)}:\n{e}"
            ) from e
        # This next line should be unreachable...
        raise TypeError(
            f"Expected {param.name!r} to be castable to "
            f"{type_repr(param.type)}, got {spec.value!r}"
        )

    raise TypeError(
        f"Expected {param.name!r} to be {type_repr(param.type)}, got {type_repr(type(spec))}"
    )


def _check_for_wildcard_matching_variadic_top_level(
    obj: object, param: _Param, obj_path: str, arg_map: ArgumentMap
):
    assert param.default is not None
    if (
        type(param.default.value) is tuple and param.default.value == ()
    ) or param.default.factory in (tuple, list, dict):
        return

    result = _collect_variadic_params(obj, obj_path, arg_map)
    if result is None:
        return
    variadic_params, _, variadic_types = result
    if variadic_params:
        return
    if isinstance(param.default.value, (tuple, list)):
        variadic_types = list(
            set(variadic_types) | {type(element) for element in param.default.value}
        )
    if isinstance(param.default.value, dict):
        variadic_types = list(
            set(variadic_types) | {type(element) for element in param.default.value.values()}
        )

    if not variadic_types:
        return

    # The case we're checking here is if we:
    # 1) have a param with a default
    # 1.5) the default is not an empty tuple or list or dict
    # 2) have a variadic factory for that param
    # 3) we do not find any variadic params
    # Then we check if any wildcards would have matched a param if we had one, since it can be
    # unintuitive that the default will not be affected by the wildcard (default / default_factory
    # are opaque and have no interaction with wildcards beyond their presence or absence).
    # See test_variadic_default_wildcard_error
    for element_type in variadic_types:
        subparams = _collect_params(element_type)
        if isinstance(subparams, ConstructionError):
            continue
        for subparam in subparams:
            param_path = obj_path + ".__chz_empty_variadic." + subparam.name
            found_arg = arg_map.get_kv(param_path)
            param_path = obj_path + ".(variadic)." + subparam.name
            if found_arg is not None:
                raise ConstructionError(
                    f"\n\nYou've hit an interesting case.\n\n"
                    f'The parameter "{obj_path}" is variadic ({type_repr(obj)}), but no '
                    "parametrisation was found (either variadic subparameters or a polymorphic "
                    "parametrisation).\n"
                    f'This is fine in theory, because "{obj_path}" has a '
                    f"default value.\n\n"
                    f'However, you also specified the wildcard "{found_arg.key}" and you may '
                    f'have expected it to modify the value of "{param_path}".\n'
                    "This is not possible -- default values / default_factory results are "
                    "opaque to chz. "
                    "The only way in which default / default_factory interact with Blueprint "
                    "is presence / absence. So out of caution, here's an error!\n\n"
                    "If this error is a false positive, consider scoping the wildcard more "
                    "narrowly or using exact keys. As always, appending --help to a chz command "
                    "will show you what gets mapped to which param."
                )
