import asyncio
import io
import logging
import tarfile

from alcatraz.clusters.swarm import SwarmCluster


async def main() -> None:
    # note: you could do a docker image w/o jupyter installed and Swarm Cluster will install jupyter in the container for you!
    logging.basicConfig(level=logging.INFO)
    async with SwarmCluster(image="quay.io/jupyter/base-notebook:python-3.11") as swarm_cluster:
        container_names = await swarm_cluster.fetch_container_names()
        print("container names", container_names)

        print("upload file")
        await swarm_cluster.upload(
            file=b"the mango is the fruit of the rich",
            destination="/home/jovyan/example.txt",
        )
        print("download file")
        assert (
            await swarm_cluster.download(
                source="/home/jovyan/example.txt",
            )
            == b"the mango is the fruit of the rich"
        )
        print("download tar")
        b = await swarm_cluster.download_tar(
            source="/home/jovyan",
        )

        tar = tarfile.open(fileobj=io.BytesIO(b), mode="r")
        file_names = tar.getnames()
        print(file_names)
        assert "jovyan/example.txt" in file_names, "File not found in tar"

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
            print((await swarm_cluster.send_shell_command(cmd, timeout=60))["result"])

        kernel_commands = [
            "print('hello world')",
            "a = 10",
            "print(a)",
            "b = 232-",
            "print(b)",
            "print(a)",
        ]
        await swarm_cluster.create_kernel_on_machine()
        for cmd in kernel_commands:
            for msg in await swarm_cluster.send_kernel_command(cmd):
                logging.info("%s", msg)
            logging.info("Kernel is alive: %s", await swarm_cluster.kernel_is_alive())


if __name__ == "__main__":
    asyncio.run(main())
