from typing import TypedDict


class ExecutionResult(TypedDict):
    exit_code: int
    result: bytes


class AlcatrazException(Exception):
    """Base exception for all Alcatraz exceptions that are not a client error (i.e., improper auth, etc.)."""

    pass


class AlcatrazCodeExecutorTimeoutError(AlcatrazException):
    pass


class AlcatrazTimeoutInterruptError(AlcatrazException):
    """Interrupting the code execution was unsuccessful"""

    pass


class AlcatrazAsyncioCancelledError(AlcatrazException):
    """Asyncio execution cancelled by the user/client."""

    pass


class AlcatrazUnexpectedSystemError(AlcatrazException):
    """An unexpected error was encountered. This is a catch-all to handle unexpected termination of code execution."""

    pass


class AlcatrazOutOfDiskSpaceError(AlcatrazException):
    """The code execution has run out of disk space."""

    pass
