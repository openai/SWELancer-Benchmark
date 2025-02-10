import asyncio
import logging
import os

from alcatraz.clusters.local import LocalCluster

logger = logging.getLogger(__name__)
INTERACTIVE = bool(int(os.getenv("INTERACTIVE", 0)))


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with LocalCluster(image="quay.io/jupyter/base-notebook:python-3.11") as local_cluster:
        if INTERACTIVE:
            await local_cluster.create_kernel_on_machine()
            while True:
                cmd = input("[In]: ")
                for msg in await local_cluster.send_kernel_command(cmd):
                    logging.info("%s", msg)

                logging.info("Kernel is alive: %s", await local_cluster.kernel_is_alive())
        else:
            # note: you could do a docker image w/o jupyter installed and Swarm Cluster will install jupyter in the container for you!
            print("container names", await local_cluster.fetch_container_names())
            print("upload file")
            await local_cluster.upload(
                file=b"the mango is the fruit of the rich",
                destination="/home/jovyan/example.txt",
            )
            print("download file")
            assert (
                await local_cluster.download(
                    source="/home/jovyan/example.txt",
                )
                == b"the mango is the fruit of the rich"
            )
            shell_commands = [
                "whoami",
                "ls -lh /home/jovyan",
                "cat /home/jovyan/example.txt",
                "pwd",
                "touch ~/test.txt",
                "df -h ~",
                "curl https://www.google.com",
                "curl -Iv https://invalid.blob.core.windows.net",
                "curl -Iv https://oaistrawberryaceresearch.blob.core.windows.net",
                "java --version",
                "javac --version",
            ]
            for cmd in shell_commands:
                print(cmd)
                print(
                    (await local_cluster.send_shell_command(cmd, timeout=60))["result"].decode(
                        "utf-8"
                    )
                )

            kernel_commands = ["!ls", "!uname -a"]
            await local_cluster.create_kernel_on_machine()
            for cmd in kernel_commands:
                for msg in await local_cluster.send_kernel_command(cmd):
                    logging.info("%s", msg)

                logging.info("Kernel is alive: %s", await local_cluster.kernel_is_alive())


if __name__ == "__main__":
    asyncio.run(main())
