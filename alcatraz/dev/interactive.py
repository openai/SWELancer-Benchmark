"""
Interactively log into a new alcatraz cluster and run shell commands.
You can use chz to configure the alcatraz cluster you want to use.

Example usage:
    python -m alcatraz.dev.interactive config=alcatraz.clusters.swarm:SwarmConfig config.image=alcatrazswarmcontainers.azurecr.io/cimg/base:current
    python -m alcatraz.dev.interactive config=alcatraz.clusters.swarm:SwarmConfig config.image=alcatrazswarmcontainers.azurecr.io/alcatraz_api_proxy:latest

TODO(kevinliu): use a real pty and terminal tool instead of this hacky solution.
"""

import asyncio
import logging

import chz

# no aioconsole stubs
from aioconsole import ainput, aprint  # type: ignore
from alcatraz.clusters.local import ClusterConfig
from alcatraz.clusters.swarm import SwarmConfig  # type: ignore

DEFAULT_CONFIG = SwarmConfig()


async def main(config: ClusterConfig = DEFAULT_CONFIG) -> None:
    await aprint("Starting cluster...")
    async with config.build() as cluster:
        await aprint("We're in 😎")
        while True:
            command = await ainput("alcatraz-shell$ ")
            if command == "exit":
                break

            result = await cluster.send_shell_command(command)
            await aprint("exit code:", result["exit_code"])
            await aprint(result["result"].decode("utf-8"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(chz.entrypoint(main))
