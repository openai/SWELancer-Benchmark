import asyncio
import logging

from alcatraz.clusters.swarm import SwarmCluster


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with SwarmCluster(
        image="quay.io/jupyter/base-notebook:python-3.11", azure_vm_sku="Standard_NC4as_T4_v3"
    ) as swarm_cluster:
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
        print("nvidia-smi")
        r = await swarm_cluster.send_shell_command("nvidia-smi", timeout=60)
        print(r["result"].decode("utf-8"))
        print("Exit Code:", r["exit_code"])
        assert r["exit_code"] == 0, (
            f"OUTPUT_START\n{r['result'].decode('utf-8')}\nOUTPUT_END\nExit code expected 0 but was instead {r['exit_code']}"
        )

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
