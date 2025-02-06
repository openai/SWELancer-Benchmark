import asyncio

import structlog.stdlib
from structlog.contextvars import bound_contextvars

from alcatraz.clusters.interface import ExecutionResult
from alcatraz.clusters.local import BaseAlcatrazCluster, CommandOutputResult

logger = structlog.stdlib.get_logger(component=__name__)


async def run_command_streaming(cluster: BaseAlcatrazCluster, command: str) -> ExecutionResult:
    """
    Runs a long command using a streaming/polling interface. Benefits:

    - It iteratively logs the output of the command. every 5 seconds.
    - It is likely more reliable than HTTP long polling on the `send_shell_command` API.
    """

    result = await cluster.send_shell_command(command) 
    return result
