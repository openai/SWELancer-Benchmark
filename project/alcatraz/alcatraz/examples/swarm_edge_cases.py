import asyncio
import logging
import time

import httpx

from alcatraz.clusters.swarm import SwarmCluster


async def main() -> None:
    try:
        async with SwarmCluster(image="quay.io/jupyter/base-notebook:python-3.11") as swarm_cluster:
            time.sleep(  # noqa: ASYNC251
                60 * 12
            )  # should block heartbeats which cause send_shell_command to raise  # noqa: ASYNC251
            try:
                await swarm_cluster.send_shell_command("ls")
            except AssertionError:
                pass
            else:
                assert False
    except httpx.HTTPStatusError as e:
        assert "404 Not Found" in str(e)
    else:
        assert False

    async with SwarmCluster(image="quay.io/jupyter/base-notebook:python-3.11") as swarm_cluster:
        pass
    try:
        await swarm_cluster.send_shell_command(
            "sleep"
        )  # should raise when making a method call on a released SwarmCluster instance
    except ValueError:
        pass
    else:
        assert False

    logging.basicConfig(level=logging.INFO)
    async with SwarmCluster(image="quay.io/jupyter/base-notebook:python-3.11") as swarm_cluster:
        await swarm_cluster.create_kernel_on_machine()
        for msg in await swarm_cluster.send_kernel_command("'a' * (2 ** 20)"):
            logging.info("%s", msg)

        # Very long executions, which might trip Azure LB 4 minute timeout if keepalive doesn't work
        print((await swarm_cluster.send_shell_command("sleep 420", timeout=450))["result"])
        print((await swarm_cluster.send_shell_command("echo hello", timeout=5))["result"])

    async with SwarmCluster(image="quay.io/jupyter/base-notebook:python-3.11") as swarm_cluster:
        await swarm_cluster.create_kernel_on_machine()
        try:
            async with asyncio.timeout(10):
                print("\033[32mStarting sleep(20) command\033[0m")
                await swarm_cluster.send_kernel_command("import time; time.sleep(20)")
                print("\033[32mSleep(20) done\033[0m")
        except asyncio.TimeoutError:
            print("\033[31mTimeout error\033[0m")
        s = time.time()
        print("\033[32mStarting hello world command\033[0m")
        await swarm_cluster.send_kernel_command("print('hello world')")
        time_taken = time.time() - s
        print("\033[32mHello world done\033[0m")
        print(f"\033[32mTime taken: {time_taken}\033[0m")
        assert time_taken < 3, f"Took {time_taken} to run the hello world :("


if __name__ == "__main__":
    asyncio.run(main())
