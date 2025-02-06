from __future__ import annotations

import functools
import sys
from typing import Any, Callable

import chz
from chz.mungers import Munger, default_munger
from chz.tiepin import TypeForm
from chz.util import _MISSING_TYPE, MISSING

_FieldValidator = Callable[[Any, str], None]


def field(
    *,
    # default related
    default: Any | _MISSING_TYPE = MISSING,
    default_factory: Callable[[], Any] | _MISSING_TYPE = MISSING,
    # munger related
    munger: Munger | Callable[[Any, Any], Any] | None = None,
    x_type: TypeForm | _MISSING_TYPE = MISSING,
    # blueprint related
    meta_factory: chz.factories.MetaFactory | None | _MISSING_TYPE = MISSING,
    blueprint_unspecified: Callable[..., Any] | _MISSING_TYPE = MISSING,
    blueprint_cast: Callable[[str], object] | None = None,
    # misc
    validator: _FieldValidator | (list[_FieldValidator] | None) = None,
    repr: bool | Callable[[Any], str] = True,
    doc: str = "",
    metadata: dict[str, Any] | None = None,
) -> Any:
    """Customise a field in a chz class.

    Args:
        default: The default value for the field (if any).

        default_factory:
            A function that returns the default value for the field.
            Useful for mutable types, for instance, `default_factory=list`.

            This does not interact at all with parametrisation. Perhaps a better name would be
            lazy_default (but unfortunately, this is not supported by PEP 681, so static type
            checkers would lose the ability to understand the class).

        munger: Lets you adjust the value of a field. Essentially works the same as
            an init_property.

        x_type: Useful in combination with mungers. This specifies the type before munging that
            will be used for parsing and type checking.

        meta_factory:
            Represents the set of possible callables that can give us a value of a given type.

        blueprint_unspecified:
            Used to construct the meta_factory, if meta_factory is unspecified. This is the
            default callable we can attempt to call to get a value of the expected type.
            See the documentation in chz.factories for more information.

            In particular, the following two are equivalent:
            ```
            x: Base = field(blueprint_unspecified=Sub)
            x: Base = field(meta_factory=chz.factories.subclass(Base, default_cls=Sub))
            ```

        blueprint_cast: A function that takes a str and returns an object. On failure to cast,
            it should raise `CastError`. Used to achieve custom parsing behaviour from the command
            line. Takes priority over the `__chz_cast__` dunder method (if present on the
            target type).

        validator: A function or list of functions that validate the field.
            Field validators take two arguments: the instance of the class
            and the name of the field.

        repr: Whether to include the field in the `__repr__` of the class. This can also be a
            callable to customise the repr of the field.

        doc: The docstring for the field.

        metadata: Arbitrary metadata to attach to the field.
    """
    return Field(
        name="",
        raw_type="",
        default=default,
        default_factory=default_factory,
        munger=munger,
        raw_x_type=x_type,
        meta_factory=meta_factory,
        blueprint_unspecified=blueprint_unspecified,
        blueprint_cast=blueprint_cast,
        validator=validator,
        repr=repr,
        doc=doc,
        metadata=metadata,
    )


class Field:
    def __init__(
        self,
        *,
        name: str,
        raw_type: TypeForm | str,
        default: Any = MISSING,
        default_factory: Callable[[], Any] | _MISSING_TYPE = MISSING,
        munger: Munger | Callable[[Any, Any], Any] | None = None,
        raw_x_type: TypeForm | _MISSING_TYPE = MISSING,
        meta_factory: chz.factories.MetaFactory | None | _MISSING_TYPE = MISSING,
        blueprint_unspecified: Callable[..., Any] | _MISSING_TYPE = MISSING,
        blueprint_cast: Callable[[str], object] | None = None,
        validator: _FieldValidator | (list[_FieldValidator] | None) = None,
        repr: bool | Callable[[Any], str] = True,
        doc: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        if default.__class__.__hash__ is None:
            raise ValueError(
                f"Mutable default {type(default)} for field "
                f"{name} is not allowed: use default_factory"
            )

        if (
            meta_factory is not MISSING
            and meta_factory is not None
            and not isinstance(meta_factory, chz.factories.MetaFactory)
        ):
            raise TypeError(f"meta_factory must be a MetaFactory, not {type(meta_factory)}")

        if blueprint_unspecified is not MISSING:
            if not callable(blueprint_unspecified):
                raise TypeError(
                    f"blueprint_unspecified must be callable, not {type(blueprint_unspecified)}"
                )
            if meta_factory is not MISSING:
                raise ValueError("Cannot specify both meta_factory and blueprint_unspecified")

        if default_factory is not MISSING:
            if not callable(default_factory):
                raise TypeError(f"default_factory must be callable, not {type(default_factory)}")
            if isinstance(default_factory, chz.factories.MetaFactory):
                raise TypeError(
                    "default_factory must be a callable that returns a value, "
                    "not a MetaFactory. Note that default_factory must be callable without any "
                    "arguments and does not interact with parametrisation."
                )

        if munger is not None and not callable(munger):
            raise TypeError(f"munger must be callable, not {type(munger)}")

        if validator is None:
            validator = []
        elif not isinstance(validator, list):
            validator = [validator]

        self._name = name
        self._raw_type = raw_type
        self._raw_x_type = raw_x_type
        self._default = default
        self._default_factory = default_factory
        self._meta_factory = meta_factory
        self._blueprint_unspecified = blueprint_unspecified
        self._munger = munger
        self._validator: list[_FieldValidator] = validator
        self._blueprint_cast = blueprint_cast
        self._repr = repr
        self._doc = doc
        self._metadata = metadata

        # We used to pass the actual globals around, but cloudpickle did not like that
        # when it tried to pickle chz classes by value in __main__
        # Note that this means that if we're using postponed annotations or quoted annotations
        # in __main__ that self.type will likely fail if this is ever pickled and unpickled
        self._user_module: str = ""

    @property
    def logical_name(self) -> str:
        for magic_prefix in ("隐", "_X_"):
            if self._name.startswith(magic_prefix):
                raise RuntimeError(f"Magic prefix {magic_prefix} no longer supported, use X_")
        if self._name.startswith("X_"):
            return self._name.removeprefix("X_")
        return self._name

    @property
    def x_name(self) -> str:
        return "X_" + self.logical_name

    @functools.cached_property
    def final_type(self) -> TypeForm:
        if not self._name:
            raise RuntimeError(
                "Something has gone horribly awry; are you using a chz.Field in a dataclass?"
            )
        # Delay the eval until after the class
        if isinstance(self._raw_type, str):
            # TODO: handle forward ref
            assert self._user_module
            if self._user_module not in sys.modules:
                raise RuntimeError(
                    f"Could not find module {self._user_module}; possibly a pickling issue?"
                )
            user_globals = sys.modules[self._user_module].__dict__
            return eval(self._raw_type, user_globals)
        return self._raw_type

    @functools.cached_property
    def x_type(self) -> TypeForm:
        if isinstance(self._raw_x_type, _MISSING_TYPE):
            return self.final_type
        return self._raw_x_type

    @property
    def meta_factory(self) -> chz.factories.MetaFactory | None:
        if self._meta_factory is None:
            return None

        if isinstance(self._meta_factory, _MISSING_TYPE):
            if isinstance(self._blueprint_unspecified, _MISSING_TYPE):
                unspec = None
            else:
                unspec = self._blueprint_unspecified

            import chz.factories

            ret = chz.factories.standard(
                self.x_type, unspecified=unspec, default_module=self._user_module
            )
            ret.field_annotation = self.x_type
            ret.field_module = self._user_module
            return ret

        self._meta_factory.field_annotation = self.x_type
        self._meta_factory.field_module = self._user_module
        return self._meta_factory

    def get_munger(self) -> Callable[[Any], None] | None:
        if self._munger is None:
            return None

        if isinstance(self._munger, Munger):
            m = self._munger
        else:
            assert callable(self._munger)
            m = default_munger(self._munger)

        # Must return a new callable every time
        return lambda chzself: m(chzself, field=self)

    @property
    def metadata(self) -> dict[str, Any] | None:
        return self._metadata

    def __repr__(self):
        return f"Field(name={self._name!r}, type={self.final_type!r}, ...)"

    def versioning_key(self) -> tuple[str, ...]:
        from chz.tiepin import approx_type_hash

        raw_type_key = approx_type_hash(self._raw_type)

        if self._default is MISSING:
            default_key = ""
        elif self._default.__repr__ is not object.__repr__:
            default_key = repr(self._default)
        else:
            default_key = self._default_factory.__class__.__name__

        if isinstance(self._default_factory, _MISSING_TYPE):
            default_factory_key = ""
        else:
            # TODO: support lambdas
            default_factory_key = (
                self._default_factory.__module__ + "." + self._default_factory.__name__
            )
        return (self._name, raw_type_key, default_key, default_factory_key)
