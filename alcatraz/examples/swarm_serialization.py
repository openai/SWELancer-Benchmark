import asyncio
import logging
from pprint import pprint

from alcatraz.clusters.swarm import SwarmConfig


async def main() -> None:
    # Test session resumption!
    logging.basicConfig(level=logging.INFO)
    async with SwarmConfig(
        image="quay.io/jupyter/base-notebook:python-3.11", kill_machine_on_exit=False
    ).build() as swarm_cluster:
        print("upload file")
        await swarm_cluster.upload(
            file=b"the mango is the fruit of the rich",
            destination="/home/jovyan/example.txt",
        )

    print("Serialization")

    # kill the machine next time around
    serialized = swarm_cluster.serialize().model_copy(update={"kill_machine_on_exit": True})
    pprint(serialized)

    async with serialized.build() as swarm_cluster:
        print("download file")
        assert (
            await swarm_cluster.download(
                source="/home/jovyan/example.txt",
            )
            == b"the mango is the fruit of the rich"
        )


if __name__ == "__main__":
    asyncio.run(main())
