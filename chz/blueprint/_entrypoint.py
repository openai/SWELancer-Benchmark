from __future__ import annotations

import functools
import inspect
import io
import os
import sys
from typing import Any, Callable, TypeVar

import chz
from chz.tiepin import eval_in_context, type_repr

_T = TypeVar("_T")
_F = TypeVar("_F", bound=Callable[..., Any])


class EntrypointException(Exception): ...


class EntrypointHelpException(EntrypointException): ...


class ExtraneousBlueprintArg(EntrypointException): ...


class InvalidBlueprintArg(EntrypointException): ...


class MissingBlueprintArg(EntrypointException): ...


def exit_on_entrypoint_error(fn: _F) -> _F:
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except EntrypointException as e:
            if isinstance(e, EntrypointHelpException):
                print(e, end="" if e.args[0][-1] == "\n" else "\n")
            else:
                print("Error:", file=sys.stderr)
                print(e, end="" if e.args[0][-1] == "\n" else "\n", file=sys.stderr)
            if "PYTEST_VERSION" in os.environ:
                raise
            sys.exit(1)

    return inner  # type: ignore[return-value]


@exit_on_entrypoint_error
def entrypoint(
    target: Callable[..., _T], *, argv: list[str] | None = None, allow_hyphens: bool = False
) -> _T:
    """Easy way to create a script entrypoint using chz.

    For example, if you wish to run a function:
    ```
    def do_something(alpha: int, beta: str, gamma: bytes) -> None:
        ...

    if __name__ == "__main__":
        chz.entrypoint(do_something)
    ```

    It also works for instantiating objects:
    ```
    @chz.chz
    class Run:
        name: str
        def launch(self) -> None: ...

    if __name__ == "__main__":
        run = chz.entrypoint(Run)
        run.launch()
    ```
    """
    # This function should be easily forkable, so do not make it more complicated
    return chz.Blueprint(target).make_from_argv(argv, allow_hyphens=allow_hyphens)


@exit_on_entrypoint_error
def nested_entrypoint(
    main: Callable[[Any], _T], *, argv: list[str] | None = None, allow_hyphens: bool = False
) -> _T:
    """Easy way to create a script entrypoint using chz for functions that take a chz object.

    For example:
    ```
    @chz.chz
    class Run:
        name: str

    def main(run: Run) -> None:
        ...

    if __name__ == "__main__":
        chz.nested_entrypoint(main)
    ```
    """
    # This function should be easily forkable, so do not make it more complicated
    target = get_nested_target(main)
    value = chz.Blueprint(target).make_from_argv(argv, allow_hyphens=allow_hyphens)
    return main(value)


@exit_on_entrypoint_error
def methods_entrypoint(
    target: type[_T],
    *,
    argv: list[str] | None = None,
    transform: Callable[[chz.Blueprint[Any], Any, str], chz.Blueprint[Any]] | None = None,
) -> _T:
    """Easy way to create a script entrypoint using chz for methods on a class.

    For example, given main.py:
    ```
    @chz.chz
    class Run:
        name: str

        def launch(self, cluster: str):
            "Launch a job on a cluster"
            return ("launch", self, cluster)

    if __name__ == "__main__":
        print(chz.methods_entrypoint(Run))
    ```

    Try out the following command line invocations:
    ```
    python main.py launch self.name=job cluster=owl
    python main.py launch --help
    python main.py --help
    ```

    Note that you can rename the `self` argument in your method to something else.
    """
    if argv is None:
        argv = sys.argv[1:]
    if not argv or not argv[0].isidentifier():
        f = io.StringIO()
        output = functools.partial(print, file=f)
        if argv and not argv[0].isidentifier() and not argv[0].startswith("--"):
            output(f"WARNING: {argv[0]} is not a valid method")
        output(f"Entry point: methods of {type_repr(target)}")
        output()
        output("Available methods:")
        for name in dir(target):
            meth = getattr(target, name)
            if not name.startswith("_") and callable(meth):
                meth_doc = getattr(meth, "__doc__", "") or ""
                meth_doc = meth_doc.strip().split("\n", 1)[0]
                output(f"  {name}  {meth_doc}".rstrip())
        raise EntrypointHelpException(f.getvalue())

    blueprint = chz.Blueprint(getattr(target, argv[0]))
    if transform is not None:
        blueprint = transform(blueprint, target, argv[0])
    return blueprint.make_from_argv(argv[1:])


def _resolve_annotation(annotation: Any, func: Any) -> Any:
    """Resolves a type annotation against the globals of the target function."""
    if annotation is inspect.Parameter.empty:
        return None
    if isinstance(annotation, str):
        return eval_in_context(annotation, func)
    return annotation


def get_nested_target(main: Callable[[_T], object]) -> type[_T]:
    """Returns the type of the first argument of a function.

    For example:
    ```
    def main(run: Run) -> None: ...

    assert chz.get_nested_target(main) is Run
    ```
    """
    params = list(inspect.signature(main).parameters.values())
    if not params or params[0].annotation == inspect.Parameter.empty:
        raise ValueError("Nested entrypoints must take a type annotated argument")
    if any(p.default is p.empty for p in params[1:]):
        raise ValueError("Nested entrypoints must take at most one argument without a default")
    return _resolve_annotation(params[0].annotation, main)
