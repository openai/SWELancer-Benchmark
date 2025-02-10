import asyncio
import logging
import random

from alcatraz.clusters.swarm import SwarmCluster


async def main() -> None:
    # note: you could do a docker image w/o jupyter installed and Swarm Cluster will install jupyter in the container for you!
    logging.basicConfig(level=logging.DEBUG)
    async with SwarmCluster(image="quay.io/jupyter/base-notebook:python-3.11") as swarm_cluster:
        shell_commands = [
            "whoami",
            "ls -lh /home/",
            "cat /home/jovyan/example.txt",
            "pwd",
            "touch ~/test.txt",
            "df -h ~",
            "sleep 10",
        ]
        for _i in range(30):
            cmd = random.choice(shell_commands)
            print(cmd)
            print((await swarm_cluster.send_shell_command(cmd, timeout=60))["result"])


if __name__ == "__main__":
    asyncio.run(main())
