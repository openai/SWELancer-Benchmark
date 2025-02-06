"""

This is the core implementation of the chz class. It's based off of the implementation of
dataclasses, but is somewhat simpler. I also fixed a couple minor issues in dataclasses when
writing this :-)

Some non-exhaustive reasons why chz's feature set isn't built on top of dataclasses / attrs:
- dataclasses is a general purpose class replacement, chz isn't. This lets us establish intention,
  have better defaults, make different tradeoffs, better errors in various places
- Ability to have custom logic in chz.field
- Clearer handling of type annotation evaluation and scopes
- chz needs keyword-only arguments for various reasons (dataclasses acquired this only later)
- Cool data model tricks like munging and init_property
- Automatically calculated versions
- Many small things

"""

import builtins
import copy
import dataclasses
import functools
import hashlib
import inspect
import sys
import types
import typing
from collections.abc import Collection
from typing import TYPE_CHECKING, Any, Callable, TypeVar

import typing_extensions

from chz.field import Field
from chz.tiepin import type_repr
from chz.util import MISSING

FrozenInstanceError = dataclasses.FrozenInstanceError

_T = TypeVar("_T")


_INIT_ALTERNATIVES: str = (
    "For validation, see @chz.validate decorators. "
    "For per-field defaults, see `default` and `default_factory` options in chz.field. "
    "To perform post-initialization rewrites of field values, use `munger` option in chz.field "
    "or add an `init_property` to the class.\n"
    "See the docs for more details."
)


def _create_fn(
    name: str, args: list[str], body: list[str], *, locals: dict[str, Any], globals: dict[str, Any]
):
    args_str = ",".join(args)
    body_str = "\n".join(f"  {b}" for b in body)

    # Compute the text of the entire function.
    txt = f" def {name}({args_str}):\n{body_str}"

    # Free variables in exec are resolved in the global namespace.
    # The global namespace we have is user-provided, so we can't modify it for
    # our purposes. So we put the things we need into locals and introduce a
    # scope to allow the function we're creating to close over them.
    local_vars = ", ".join(locals.keys())
    txt = f"def __create_fn__({local_vars}):\n{txt}\n return {name}"

    ns: Any = {}
    exec(txt, globals, ns)
    return ns["__create_fn__"](**locals)


# ==============================
# Method synthesis
# ==============================


def _synthesise_field_init(f: Field, out_vars: dict[str, Any]) -> tuple[str, str]:
    # This function modifies out_vars
    var_type = f"__chz_{f.logical_name}"
    out_vars[var_type] = f._raw_type

    var_default = f"__chz_dflt_{f.logical_name}"
    if f._default_factory is not MISSING:
        out_vars[var_default] = f._default_factory
        value = f"{var_default}() if {f.logical_name} is __chz_MISSING else {f.logical_name}"
        dflt_expr = " = __chz_MISSING"
    elif f._default is not MISSING:
        out_vars[var_default] = f._default
        # Is it ever useful to explicitly pass MISSING?
        # value = f"{var_default} if {f.logical_name} is __chz_MISSING else {f.logical_name}"
        value = f.logical_name
        dflt_expr = f" = {var_default}"
    else:
        value = f.logical_name
        dflt_expr = ""

    arg = f"{f.logical_name}: {var_type}{dflt_expr}"
    body = f"__chz_builtins.object.__setattr__(self, {f.x_name!r}, {value})"

    return arg, body


def _synthesise_init(fields: Collection[Field], user_globals: dict[str, Any]) -> Callable[..., Any]:
    varlocals = {"__chz_MISSING": MISSING, "__chz_builtins": builtins}

    # __chz_args is not strictly necessary, but makes for better errors
    args = ["self", "*__chz_args"]
    body = [
        "if __chz_args:",
        "    raise __chz_builtins.TypeError(f'{self.__class__.__name__}.__init__ only takes keyword arguments')",
        "if '__chz_fields__' not in __chz_builtins.type(self).__dict__:",
        "    raise __chz_builtins.TypeError(f'{self.__class__.__name__} is not decorated with @chz.chz')",
    ]
    for field in fields:
        if field.logical_name.startswith("__chz") or field.logical_name == "self":
            raise ValueError(f"Field name {field.logical_name!r} is reserved")
        _arg, _body = _synthesise_field_init(field, varlocals)

        args.append(_arg)
        body.append(_body)

    # Note it's important we validate before we check all init_property
    body.append("self.__chz_validate__()")
    body.append("self.__chz_init_property__()")

    return _create_fn("__init__", args, body, locals=varlocals, globals=user_globals)


def __setattr__(self, name, value):
    raise FrozenInstanceError(f"Cannot modify field {name!r}")


def __delattr__(self, name):
    raise FrozenInstanceError(f"Cannot delete field {name!r}")


def _recursive_repr(user_function):
    import threading

    repr_running = set()

    @functools.wraps(user_function)
    def wrapper(self):
        key = id(self), threading.get_ident()
        if key in repr_running:
            return "..."
        repr_running.add(key)
        try:
            result = user_function(self)
        finally:
            repr_running.discard(key)
        return result

    return wrapper


def __repr__(self) -> str:
    def field_repr(field: Field) -> str:
        # use x_name so that repr can be copy-pasted to create the same object
        if callable(field._repr):
            return field._repr(getattr(self, field.x_name))
        assert isinstance(field._repr, bool)
        if field._repr:
            return repr(getattr(self, field.x_name))
        return "..."

    contents = ", ".join(
        f"{field.logical_name}={field_repr(field)}" for field in self.__chz_fields__.values()
    )
    return self.__class__.__qualname__ + f"({contents})"


def __eq__(self, other):
    if self.__class__ is not other.__class__:
        return NotImplemented
    return all(getattr(self, name) == getattr(other, name) for name in self.__chz_fields__)


def __hash__(self) -> int:
    try:
        return hash(
            tuple((name, getattr(self, f.x_name)) for name, f in self.__chz_fields__.items())
        )
    except TypeError as e:
        for name, f in self.__chz_fields__.items():
            value = getattr(self, f.x_name)
            try:
                hash(value)
            except TypeError:
                raise TypeError(
                    f"Cannot hash chz field: {type(self).__name__}.{name}={value}"
                ) from e
        raise e


def __chz_validate__(self) -> None:
    for field in self.__chz_fields__.values():
        if field._munger is None:
            for validator in field._validator:
                # So without mungers, we always run validators against the raw value
                # There is currently code that relies on not running validator against a potential
                # user-specified init_property
                # TODO: is it unfortunate that x_name appears in error messages?
                validator(self, field.x_name)
        else:
            # With mungers, we run validators against both the munged and unmunged value
            # I'm willing to reconsider this, but want to be conservative for now
            for validator in field._validator:
                validator(self, field.logical_name)
                validator(self, field.x_name)
    for validator in getattr(self, "__chz_validators__", []):
        validator(self)


def __chz_init_property__(self) -> None:
    # TODO: getmembers_static in 3.11?
    for name, _obj in inspect.getmembers_static(
        self.__class__, lambda o: isinstance(o, init_property)
    ):
        getattr(self, name)


def pretty_format(obj: Any, colored: bool = True) -> str:
    """Format a chz object for human readability."""
    bold = "\033[1m" if colored else ""
    blue = "\033[34m" if colored else ""
    grey = "\033[90m" if colored else ""
    reset = "\033[0m" if colored else ""
    space = " " * 4

    if isinstance(obj, (list, tuple)):
        if not obj or all(not is_chz(x) for x in obj):
            return repr(obj)

        a, b = ("[", "]") if isinstance(obj, list) else ("(", ")")
        items = [pretty_format(x, colored).replace("\n", "\n" + space) for x in obj]
        items_str = f",\n{space}".join(items)
        return f"{a}\n{space}{items_str},\n{b}"

    if isinstance(obj, dict):
        if not obj or all(not is_chz(x) for x in obj.values()):
            return repr(obj)

        items = []
        for k, v in obj.items():
            k_str = pretty_format(k, colored).replace("\n", "\n" + space)
            v_str = pretty_format(v, colored).replace("\n", "\n" + space)
            items.append(f"{k_str}: {v_str}")
        items_str = f",\n{space}".join(items)
        return f"{{\n{space}{items_str},\n}}"

    if not is_chz(obj):
        return repr(obj)

    cls_name = obj.__class__.__qualname__
    out = f"{bold}{cls_name}({reset}\n"

    def field_repr(field: Field) -> str:
        # use x_name so that repr can be copy-pasted to create the same object
        if field._repr is False:
            return "..."
        if callable(field._repr):
            r = field._repr
        else:
            assert field._repr is True
            r = lambda o: pretty_format(o, colored=colored)

        x_val = getattr(obj, field.x_name)
        val = getattr(obj, field.logical_name)
        if x_val is val:
            return r(val)
        return f"{grey}{r(x_val)}  # {reset}{r(val)}{grey} (after init){reset}"

    field_reprs: dict[bool, list[str]] = {True: [], False: []}
    for field in sorted(obj.__chz_fields__.values(), key=lambda f: f.logical_name):
        if field._default is not MISSING:
            matches_default = field._default is getattr(obj, field.x_name)
        elif field._default_factory is not MISSING:
            matches_default = field._default_factory() == getattr(obj, field.x_name)
        else:
            matches_default = False

        val_str = field_repr(field).replace("\n", "\n" + space)
        field_str = f"{space}{blue}{field.logical_name}={reset}{val_str},\n"
        field_reprs[matches_default].append(field_str)

    out += "".join(field_reprs[False])
    if field_reprs[True]:
        out += f"{space}{bold}# Fields where pre-init value matches default:{reset}\n"
        out += "".join(field_reprs[True])
    out += f"{bold}){reset}"
    return out


def _repr_pretty_(self, p, cycle: bool) -> None:
    # for nice ipython printing
    p.text(pretty_format(self))


def __chz_pretty__(self, colored: bool = True) -> str:
    """Print a chz object for human readability."""
    return pretty_format(self, colored=colored)


# ==============================
# Construction
# ==============================


def _is_classvar_annotation(annot: str | Any) -> bool:
    if isinstance(annot, str):
        # TODO: use better dataclass logic?
        return annot.startswith(("typing.ClassVar[", "ClassVar["))
    return annot is typing.ClassVar or (
        type(annot) is typing._GenericAlias  # type: ignore[attr-defined]
        and annot.__origin__ is typing.ClassVar
    )


def _is_property_like(obj: Any) -> bool:
    # TODO: the semantics implied here could be more crisply defined and maybe generalised to
    # more descriptors
    return isinstance(obj, (property, init_property, functools.cached_property))


def chz_make_class(cls, version: str | None, typecheck: bool | None) -> type:
    if cls.__class__ is not type:
        if cls.__class__ is typing._ProtocolMeta:
            if typing_extensions.is_protocol(cls):
                raise TypeError("chz class cannot itself be a Protocol)")
        else:
            import abc

            if cls.__class__ is not abc.ABCMeta:
                raise TypeError("Cannot use custom metaclass")

    user_module = cls.__module__
    cls_annotations = cls.__dict__.get("__annotations__", {})

    fields: dict[str, Field] = {}

    # Collect fields from parent classes
    for b in reversed(cls.__mro__):
        if hasattr(b, "__dataclass_fields__"):
            raise ValueError("Cannot mix chz with dataclasses")

        # Only process classes that have been processed by our decorator
        base_fields: dict[str, Field] | None = getattr(b, "__chz_fields__", None)
        if base_fields is None:
            continue
        for f in base_fields.values():
            if (
                f.logical_name in cls.__dict__
                and f.logical_name not in cls_annotations
                and not _is_property_like(getattr(cls, f.logical_name))
            ):
                # Do an LSP check against parent fields (for non-property-like members)
                raise ValueError(
                    f"Cannot override field {f.logical_name!r} with a non-field member; "
                    f"maybe you're missing a type annotation?"
                )
            else:
                fields[f.logical_name] = f

    # Collect fields from the current class
    for name, annotation in cls_annotations.items():
        if _is_classvar_annotation(annotation):
            continue

        # Find the field specification from the class __dict__
        value = cls.__dict__.get(name, MISSING)
        if value is MISSING:
            field = Field(name=name, raw_type=annotation)
        elif isinstance(value, Field):
            field = value
            field._name = name
            field._raw_type = annotation
            delattr(cls, name)
        else:
            if _is_property_like(value) or (
                isinstance(value, types.FunctionType)
                and value.__name__ != "<lambda>"
                and value.__qualname__.startswith(cls.__qualname__)
            ):
                # It's problematic to redefine the field in the same class, because it means we
                # lose any field specification or default value
                raise ValueError(f"Field {name!r} is clobbered by {type_repr(type(value))}")
            field = Field(name=name, raw_type=annotation, default=value)
            delattr(cls, name)
        field._user_module = user_module

        # Do a basic LSP check for new fields
        parent_value = getattr(cls, name, MISSING)  # note the delattr above
        if parent_value is not MISSING and not (
            field.logical_name in fields and isinstance(parent_value, init_property)
        ):
            raise ValueError(
                f"Cannot define field {name!r} because it conflicts with something defined on a "
                f"superclass: {parent_value!r}"
            )
        other_name = field.logical_name if name != field.logical_name else field.x_name
        parent_value = getattr(cls, other_name, MISSING)
        if (
            parent_value is not MISSING
            and not (field.logical_name in fields and isinstance(parent_value, init_property))
            and other_name not in cls.__dict__
        ):
            raise ValueError(
                f"Cannot define field {name!r} because it conflicts with something defined on a "
                f"superclass: {parent_value!r}"
            )

        if (
            name == field.logical_name
            and name not in cls.__dict__
            and name in fields
            and fields[name]._name != name
        ):
            raise ValueError(
                "I'm a little unsure of what the semantics should be here. "
                "See test_conflicting_superclass_x_field_in_base. "
                "Please let @shantanu know if you hit this. "
                f"You can also just rename the field in the subclass to X_{name}."
            )

        # Create a default init_property for the field that accesses the raw X_ field
        munger: Any = field.get_munger()
        if munger is not None:
            if field.logical_name in cls.__dict__:
                raise ValueError(
                    f"Cannot define {field.logical_name!r} in class when the associated field "
                    f"has a munger"
                )
            munger.__name__ = field.logical_name
            munger = init_property(munger)
            munger.__set_name__(cls, field.logical_name)
            setattr(cls, field.logical_name, munger)
        if (
            # but don't clobber existing definitions...
            field.logical_name not in cls.__dict__  # ...if something is already there in class
            and field.logical_name not in fields  # ...if a parent has defined the field
        ):
            fn: Any = lambda self, x_name=field.x_name: getattr(self, x_name)
            fn.__name__ = field.logical_name
            fn = init_property(fn)
            fn.__set_name__(cls, field.logical_name)
            setattr(cls, field.logical_name, fn)

        fields[field.logical_name] = field

    for name, value in cls.__dict__.items():
        if isinstance(value, Field) and name not in cls_annotations:
            raise TypeError(f"{name!r} has no type annotation")

    # Mark the class as having been processed by our decorator
    cls.__chz_fields__ = fields

    if "__init__" in cls.__dict__:
        raise ValueError("Cannot define __init__ on a chz class. " + _INIT_ALTERNATIVES)
    if "__post_init__" in cls.__dict__:
        raise ValueError("Cannot define __post_init__ on a chz class. " + _INIT_ALTERNATIVES)
    cls.__init__ = _synthesise_init(fields.values(), sys.modules[user_module].__dict__)
    cls.__init__.__qualname__ = f"{cls.__qualname__}.__init__"

    cls.__chz_validate__ = __chz_validate__
    cls.__chz_init_property__ = __chz_init_property__

    if "__setattr__" in cls.__dict__:
        raise ValueError("Cannot define __setattr__ on a chz class")
    cls.__setattr__ = __setattr__
    if "__delattr__" in cls.__dict__:
        raise ValueError("Cannot define __delattr__ on a chz class")
    cls.__delattr__ = __delattr__

    if "__repr__" not in cls.__dict__:
        cls.__repr__ = __repr__
    if "__eq__" not in cls.__dict__:
        cls.__eq__ = __eq__

    if "__hash__" not in cls.__dict__:
        cls.__hash__ = __hash__

    if "_repr_pretty_" not in cls.__dict__:
        # Special-cased by IPython
        cls._repr_pretty_ = _repr_pretty_
    if "__chz_pretty__" not in cls.__dict__:
        cls.__chz_pretty__ = __chz_pretty__

    if version is not None:
        import json

        # Hash all the fields and check the version matches
        expected_version = version.split("-")[0]
        key = [f.versioning_key() for f in sorted(fields.values(), key=lambda f: f.x_name)]
        key_bytes = json.dumps(key, separators=(",", ":")).encode()
        actual_version = hashlib.sha1(key_bytes).hexdigest()[:8]
        if actual_version != expected_version:
            raise ValueError(f"Version {version!r} does not match {actual_version!r}")

    if typecheck is not None:
        import chz.validators as chzval

        if typecheck:
            chzval._ensure_chz_validators(cls)
            if chzval._decorator_typecheck not in cls.__chz_validators__:
                cls.__chz_validators__.append(chzval._decorator_typecheck)
        else:
            if chzval._decorator_typecheck in getattr(cls, "__chz_validators__", []):
                raise ValueError("Cannot disable typecheck; all validators are inherited")

    return cls


# ==============================
# is_chz
# ==============================


def is_chz(c: object) -> bool:
    """Check if an object is a chz object."""
    return hasattr(c, "__chz_fields__")


# ==============================
# __chz_fields__
# ==============================


def chz_fields(c: object) -> dict[str, Field]:
    return c.__chz_fields__  # type: ignore[attr-defined]


# ==============================
# replace
# ==============================


def replace(obj: _T, /, **changes) -> _T:
    """Return a new object replacing specified fields with new values.

    Example:
    ```
    @chz.chz
    class Foo:
        a: int
        b: str

    foo = Foo(a=1, b="hello")
    assert chz.replace(foo, a=101) == Foo(a=101, b="hello")
    ```

    This just constructs a new object, so for example, the generated `__init__` gets run and
    validation will work exactly as if you manually constructed the new object.
    """
    if not hasattr(obj, "__chz_fields__"):
        raise ValueError(f"{obj} is not a chz object")

    for field in obj.__chz_fields__.values():
        if field.logical_name not in changes:
            changes[field.logical_name] = getattr(obj, field.x_name)
    return obj.__class__(**changes)


# ==============================
# asdict
# ==============================


def asdict(obj: object) -> dict[str, Any]:
    """Recursively convert a chz object to a dict.

    This works similarly to dataclasses.asdict. Note no computed properties will be included
    in the output.

    See also: beta_to_blueprint_values
    """

    def inner(x: Any):
        if hasattr(x, "__chz_fields__"):
            return {k: inner(getattr(x, k)) for k in x.__chz_fields__}
        if isinstance(x, dict):
            return {k: inner(v) for k, v in x.items()}
        if isinstance(x, list):
            return [inner(x) for x in x]
        if isinstance(x, tuple):
            return tuple(inner(x) for x in x)
        return copy.deepcopy(x)

    if not hasattr(obj, "__chz_fields__"):
        raise RuntimeError(f"{obj} is not a chz object")

    result = inner(obj)
    assert type(result) is dict
    return result


# ==============================
# beta_to_blueprint_values
# ==============================


def beta_to_blueprint_values(obj) -> Any:
    """Return a dict which can be used to recreate the same object via blueprint.

    Example:
    ```
    @chz.chz
    class Foo:
        a: int
        b: str

    foo = Foo(a=1, b="hello")
    bfoo = chz.Blueprint(Foo)
    assert bfoo.apply(chz.beta_to_blueprint_values(foo)).make() == foo
    ```

    See also: asdict
    """
    blueprint_values = {}
    for field_name, field_info in obj.__chz_fields__.items():
        field_value = getattr(obj, field_info.x_name)
        if hasattr(field_value, "__chz_fields__"):
            if (
                field_info.meta_factory is not None
                and type(field_value) is not field_info.meta_factory.unspecified_factory()
            ):
                # Try to detect when we have used polymorphic construction
                # We only handle type (not function) meta-factories
                # As subclass is the default meta-factory, we also only include
                # the type if the instance type is different from the default
                blueprint_values[field_name] = type(field_value)

            blueprint_values.update(
                {
                    f"{field_name}.{name}": value
                    for name, value in beta_to_blueprint_values(field_value).items()
                }
            )
        else:
            blueprint_values[field_name] = field_value
    return blueprint_values


# ==============================
# init_property
# ==============================

if TYPE_CHECKING:
    init_property = functools.cached_property
else:

    class init_property:
        # Simplified and pickleable version of Python 3.8's cached_property
        # It's important that this remains a non-data descriptor

        def __init__(self, func: Callable[..., Any]) -> None:
            self.func = func
            self.name = None

        def __set_name__(self, owner, name):
            self.name = name
            # Basically just validation
            func_name = self.func.__name__
            if (
                name != func_name
                and func_name != "<lambda>"
                # TODO: remove figure out why mini needs name mangling
                and not func_name.endswith("__register_chz_has_state")
            ):
                raise ValueError("Are you doing something weird with init_property?")

        def __get__(self, obj: Any, cls: Any) -> Any:
            if obj is None:
                return self
            ret = self.func(obj)
            if self.name is not None:
                obj.__dict__[self.name] = ret

            return ret
