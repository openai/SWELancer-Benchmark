import asyncio
import logging

from alcatraz.clusters.swarm import SwarmCluster
from alcatraz.utils.network import assert_internet_disabled


async def main() -> None:
    # note: you could do a docker image w/o jupyter installed and Swarm Cluster will install jupyter in the container for you!
    logging.basicConfig(level=logging.INFO)
    async with SwarmCluster(image="quay.io/jupyter/base-notebook:python-3.11") as swarm_cluster:
        await swarm_cluster.add_weak_network_block_via_ip_tables()
        await assert_internet_disabled(swarm_cluster)
        print("it worked!")

        await swarm_cluster.create_kernel_on_machine()
        print(await swarm_cluster.send_kernel_command("print('hello world')"))


if __name__ == "__main__":
    asyncio.run(main())
