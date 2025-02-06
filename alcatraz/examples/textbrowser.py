# mypy: ignore-errors
import asyncio
import json
import logging
import os
import random
import re
import subprocess
import tempfile
import time
from textwrap import dedent
from typing import Any

import backoff
import structlog
import yaml
from typing_extensions import TypedDict

import chat
import chz
from alcatraz.clusters.local import BaseAlcatrazCluster
from alcatraz.clusters.swarm import SwarmCluster
from bus_token_completer import BusTokenCompleter
from message_completer.token_message_completer import TokenMessageCompleter
from oaipkg import MONOREPO
from turn_completer.single_message_turn_completer import SingleMessageTurnCompleter


@chz.chz
class SelfHostedWebApp:
    app_name: str = "app"
    root_domain: str = "devbox.com"
    docker_compose_yaml: str
    nginx_server_blocks: str
    services: tuple[str, ...]
    frontend_username: str | None = None
    frontend_password: str | None = (
        None  # cursed since other places in codebase do strip on this :(
    )


class CaproverOneClickVariable(TypedDict):
    pass


class CaproverOneClickAppInstructions(TypedDict):
    start: str
    end: str


class CaproverOneClickApp(TypedDict):
    instructions: CaproverOneClickAppInstructions
    displayName: str
    variables: list[CaproverOneClickVariable]


class CaproverOneClickDockerComposeService(TypedDict):
    pass


class CaproverOneClickTemplate(TypedDict):
    services: dict[str, CaproverOneClickDockerComposeService]
    captainVersion: int
    caproverOneClickApp: CaproverOneClickApp


def get_stdout(jupyter_message_generator: list[dict[str, Any]]) -> str:
    for msg in jupyter_message_generator:
        if msg["msg_type"] == "error":
            raise ValueError("\n".join(msg["content"]["traceback"]))
    return "".join(
        msg["content"]["text"] for msg in jupyter_message_generator if msg["msg_type"] == "stream"
    )


# TODO make actual ssl keys
# TODO www
# Inspired by /captain/generated/nginx which is where caprover compiles the nginx
NGINX_SERVER_BLOCK_TEMPLATE = """
server {
    listen 80;
    listen              443 ssl http2;
    ssl_certificate     /etc/nginx/ssl/server_certificate.pem;
    ssl_certificate_key /etc/nginx/ssl/server_private_key.pem;
    server_name $$hostname;
    client_max_body_size 2G;

    location / {
        proxy_pass http://srv-captain--$$container:$$port;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""


def replace_random_hex(input_string):
    def gen_random_hex(length):
        return "".join(random.choices("0123456789abcdef", k=length))

    pattern = r"\$\$cap_gen_random_hex\((\d+)\)"

    def hex_replacer(match):
        length = int(match.group(1))
        return gen_random_hex(length)

    return re.sub(pattern, hex_replacer, input_string)


def map_to_acr(image, acr_registry):
    """
    Maps the original image name to the ACR image name.
    Supports both tag and digest references.

    Examples:
        ghcr.io/advplyr/audiobookshelf:2.2.14 -> selfhostedapps.azurecr.io/advplyr/audiobookshelf:2.2.14
        ghcr.io/advplyr/audiobookshelf@sha256:abcdef... -> selfhostedapps.azurecr.io/advplyr/audiobookshelf:sha256-abcdef...
        ubuntu:latest -> selfhostedapps.azurecr.io/library/ubuntu:latest
        ubuntu@sha256:abcdef... -> selfhostedapps.azurecr.io/library/ubuntu:sha256-abcdef...
    """
    digest_pattern = re.compile(r"^(?P<repo>[^@]+)@(?P<digest>sha256:[a-fA-F0-9]{64})$")
    tag_pattern = re.compile(r"^(?P<repo>[^:]+):(?P<tag>[^@]+)$")

    digest_match = digest_pattern.match(image)
    tag_match = tag_pattern.match(image)

    if digest_match:
        repo = digest_match.group("repo")
        digest = digest_match.group("digest")
        tag_or_digest = digest.replace(":", "-")
    elif tag_match:
        repo = tag_match.group("repo")
        tag_or_digest = tag_match.group("tag")
    else:
        repo = image
        tag_or_digest = "latest"

    # Handle images with and without namespace
    if "/" in repo:
        namespace, image_name = repo.split("/", 1)
    else:
        namespace, image_name = "library", repo  # Default namespace for official images

    return f"{acr_registry}/{namespace}/{image_name}:{tag_or_digest}"


ACR_REGISTRY = "selfhostedapps.azurecr.io"


def caprover_to_docker_compose(
    pth: str, values: dict, should_map_to_acr: bool = True
) -> tuple[str, str, list[str], str, str]:
    with open(pth) as f:
        s = f.read()
    s = replace_random_hex(s)
    s = s.replace("$$cap_appname", values["$$cap_appname"])
    s = s.replace("$$cap_root_domain", values["$$cap_root_domain"])
    template: CaproverOneClickTemplate = yaml.safe_load(s)
    # Extract caprover specific fields
    assert template.pop("captainVersion", None) == 4, f"Wrong version for {pth}"
    one_click_app: CaproverOneClickApp = template.pop("caproverOneClickApp")
    nginx_server_blocks_str = ""
    for name, service in template["services"].items():
        service.pop("volumes", {})
        service["platform"] = "linux/amd64"  # helps us run on mac
        caproverExtra = service.pop("caproverExtra", {})
        container_http_port = caproverExtra.pop(
            "containerHttpPort", 80 if name == values["$$cap_appname"] else None
        )
        not_expose_as_web_app = caproverExtra.pop("notExposeAsWebApp", None)
        if container_http_port:
            if type(not_expose_as_web_app) is bool:
                assert not not_expose_as_web_app
            server_block = NGINX_SERVER_BLOCK_TEMPLATE
            server_block = server_block.replace(
                "$$hostname",
                (
                    f"{name}.{values['$$cap_root_domain']}"
                    if name == values["$$cap_appname"]
                    else f"{name}-{values['$$cap_appname']}.{values['$$cap_root_domain']}"
                ),
            )  # note this could have variables in it
            server_block = server_block.replace("$$container", name)
            server_block = server_block.replace("$$port", str(container_http_port))
            nginx_server_blocks_str += server_block + "\n\n"
        # get dockerfileLines out of caproverExtra and somehow replace variables in it then also hash it so we can build docker image and name it after the hash and set service.image to the hashed image
        # caproverExtra.pop("dockerfileLines", "")
        assert not caproverExtra, f"Unhandled values in caproverExtra {caproverExtra}"

    # double check we extracted all caprover specific fields
    def dfs(o):
        if type(o) is not dict:
            return
        for k, v in o.items():
            assert not k.startswith("caprover"), f"Failed to parse field: {k}"
            dfs(v)

    dfs(template)

    # replace variables
    stringified_main = json.dumps(template)
    # print(one_click_app['variables'], values)
    for var in one_click_app["variables"]:
        if var["id"] not in values:
            if "defaultValue" in var:
                values[var["id"]] = str(var["defaultValue"])
            else:
                values[var["id"]] = ""
        # assert values[var["id"]], f"Empty variable {var['id']} for caprover template {pth}"
        stringified_main = stringified_main.replace(var["id"], values[var["id"]])
        nginx_server_blocks_str = nginx_server_blocks_str.replace(var["id"], values[var["id"]])

    _temp = json.loads(stringified_main)
    if (
        should_map_to_acr
    ):  # now that vars are replaced, we can loop through to replace the image names!
        for service in _temp["services"].values():
            service["image"] = map_to_acr(service["image"], ACR_REGISTRY)
    yaml_str = yaml.dump(_temp, sort_keys=False, default_flow_style=False)

    with tempfile.NamedTemporaryFile(mode="w") as f:
        f.write(yaml_str)
        f.flush()
        subprocess.run(["docker-compose", "-f", f.name, "config"], check=True)
    return (
        yaml_str,
        nginx_server_blocks_str.strip(),
        list(template["services"].keys()),
        values.get("$$app_username", ""),
        values.get("$$app_password", ""),
    )


async def _test(app_name, root_domain, yaml_str, nginx_server_blocks_str, services) -> None:
    start_time = time.monotonic()
    assert yaml_str and nginx_server_blocks_str and services
    logging.basicConfig(level=logging.INFO)
    async with SwarmCluster(
        image="alcatrazswarmcontainers.azurecr.io/playwright-java-tika:latest"
    ) as swarm_cluster:
        print("CONFIURING")
        ax_tree = await configure_alcatraz_with_docker_compose_app(
            swarm_cluster, app_name, root_domain, yaml_str, nginx_server_blocks_str, services
        )
        return swarm_cluster.swarm_metrics | {
            "ax_tree": ax_tree,
            "total_time": time.monotonic() - start_time,
        }


logger = structlog.get_logger(component="alcatraz.examples")


async def configure_alcatraz_with_docker_compose_app(
    cluster: BaseAlcatrazCluster, app_name, root_domain, yaml_str, nginx_server_blocks_str, services
):
    async with asyncio.timeout(60 * 30):
        logger.debug(
            f"configuring alcatraz with docker compose app with app_name{app_name} root_domain {root_domain} yaml_str {yaml_str}\n\nnginx{nginx_server_blocks_str}\n\nservices{services}"
        )
        staging_hostname = f"http://{app_name}.{root_domain}/"  # TODO, why do some sites like activepieces and adminer fail when this is https??? shouldn't nginx mean that doesn't matter if this is https??
        await cluster.start_docker_compose(
            docker_compose_yaml=yaml_str,
            root_domain=root_domain,
            app_container_name=app_name,
            nginx_config=nginx_server_blocks_str,
            service_names=services,
        )
        logger.debug("caprover app started")
        container_names = await cluster.fetch_container_names()
        logger.debug(f"container names {container_names}")
        await cluster.create_kernel_on_machine()
        logger.debug("jupyter kernel created")
        await cluster.add_weak_network_block_via_ip_tables()
        logger.debug("Network access disabled for browser container")
        _health_wait_time = 60 * 10
        logger.debug(
            get_stdout(
                await cluster.send_kernel_command(
                    dedent(
                        f"""
                    import requests
                    import time
                    def healthcheck():
                        start_time = time.time()
                        while time.time() - start_time < {_health_wait_time}:
                            try:
                                response = requests.get("{staging_hostname}", timeout=5, verify=False)
                                response.raise_for_status()
                                print(response.text)
                                return
                            except Exception:
                                time.sleep(1)
                        raise TimeoutError("Error: {staging_hostname} did not respond within {_health_wait_time} seconds.")
                    healthcheck()
                """
                    ),
                    timeout=_health_wait_time
                    + 120,  # timeout is handled in the python block above...
                )
            )
        )
        logger.debug("basic health check succeeded")
        with open(MONOREPO / "project/textbrowser/textbrowser/__init__.py") as f:
            text_browser_code_str = f.read()
        get_stdout(await cluster.send_kernel_command(text_browser_code_str))
        get_stdout(
            await cluster.send_kernel_command(
                "text_browser = await TextBrowser(wait_time=5.0, chromium_args=['--ignore-certificate-errors']).__aenter__()",
                timeout=60,
            )
        )
        logger.debug("text browser started")
        # assert container_names == # or do length assert
        get_stdout(
            # why does this fail on Swarm but not Local??? Oh lol local is going to app.devbox.com since no ip table override?? meh the requests above went to the right place
            await cluster.send_kernel_command(
                f"print(await text_browser.goto('{staging_hostname}'))", timeout=60 * 5
            )
            # AlcatrazUnexpectedSystemError # if this is small, did not hear back after timeout interrupt was sent shouldnt be an unexpected error!
        )
        page_url = get_stdout(
            await cluster.send_kernel_command("print(text_browser.get_current_url())")
        ).strip()
        logger.debug(f"page url {page_url}")
        assert f"{app_name}.{root_domain}" in page_url, (
            f"Expected page_url `{page_url}` to have `{app_name}.{root_domain}` as a substring"
        )
        ax_tree = get_stdout(
            await cluster.send_kernel_command(
                "print(await text_browser.get_current_accessibility_tree())"
            )
        ).strip()
        logger.debug(ax_tree)
        return ax_tree


async def configure_alcatraz_with_tiny_app(cluster: BaseAlcatrazCluster, html: str):
    async with asyncio.timeout(60 * 10):
        logger.debug("configuring alcatraz with tiny app")
        staging_hostname = "http://localhost/"
        await cluster.send_shell_command("cd ~/ sudo python3 -m http.server 80 --bind 0.0.0.0")
        r = await cluster.send_shell_command("mkdir -p /tinyapp")
        assert r["exit_code"] == 0
        await cluster.upload(html.encode(), "/tinyapp")
        _server_process_cmd_id = await cluster.send_shell_command_and_get_cmd_id(
            "cd ~/ sudo python3 -m http.server 80 --bind 0.0.0.0"
        )
        logger.debug("http server started")
        await cluster.create_kernel_on_machine()
        logger.debug("jupyter kernel created")
        await cluster.add_ip_table_network_block()  # why is this so slow? (3 minutes sometimes)
        logger.debug("Network access disabled for browser container")
        _health_wait_time = 60
        logger.debug(
            get_stdout(
                await cluster.send_kernel_command(
                    dedent(
                        f"""
                    import requests
                    import time
                    def healthcheck():
                        start_time = time.time()
                        while time.time() - start_time < {_health_wait_time}:
                            try:
                                response = requests.get("{staging_hostname}", timeout=5, verify=False)
                                response.raise_for_status()
                                print(response.text)
                                return
                            except Exception:
                                time.sleep(1)
                        raise TimeoutError("Error: {staging_hostname} did not respond within {_health_wait_time} seconds.")
                    healthcheck()
                """
                    ),
                    timeout=_health_wait_time
                    + 120,  # timeout is handled in the python block above...
                )
            )
        )
        logger.debug("basic health check succeeded")
        with open(MONOREPO / "project/textbrowser/textbrowser/__init__.py") as f:
            text_browser_code_str = f.read()
        get_stdout(await cluster.send_kernel_command(text_browser_code_str))
        get_stdout(
            await cluster.send_kernel_command(
                "text_browser = await TextBrowser(wait_time=5.0, chromium_args=['--ignore-certificate-errors']).__aenter__()",
                timeout=60,
            )
        )
        logger.debug("text browser started")
        # assert container_names == # or do length assert
        get_stdout(
            # why does this fail on Swarm but not Local??? Oh lol local is going to app.devbox.com since no ip table override?? meh the requests above went to the right place
            await cluster.send_kernel_command(
                f"print(await text_browser.goto('{staging_hostname}'))", timeout=60 * 5
            )
            # AlcatrazUnexpectedSystemError # if this is small, did not hear back after timeout interrupt was sent shouldnt be an unexpected error!
        )
        page_url = get_stdout(
            await cluster.send_kernel_command("print(text_browser.get_current_url())")
        ).strip()
        logger.debug(f"page url {page_url}")
        assert page_url == staging_hostname, f"{page_url} != {staging_hostname}"
        ax_tree = get_stdout(
            await cluster.send_kernel_command(
                "print(await text_browser.get_current_accessibility_tree())"
            )
        ).strip()
        logger.debug(ax_tree)
        return ax_tree


turn_completer = SingleMessageTurnCompleter(
    TokenMessageCompleter(
        # token_completer=BusTokenCompleter(topic_or_snapshot="az://oairic1/oaistrawberry2/twapi/mini/e/hwc-cbv31-aug28-run1-t1/56b4b1f5-3e78-4b23-a632-5e7f8b6f228a/checkpoint/policy/000000000200/"),
        token_completer=BusTokenCompleter(
            topic_or_snapshot="bus:snap:oaidsm2/oaistrawberry2/twapi/mini/e/hwc-cbv31-aug28-run1-t1/56b4b1f5-3e78-4b23-a632-5e7f8b6f228a/checkpoint/policy/000000000200:user:secevals"
        ),
        completion_params={"temperature": 1.0},
        renderer=chat.get_renderer("chatberry-v3-renderer-128k-cot"),
    )
)


@backoff.on_exception(backoff.expo, Exception, max_tries=10, max_value=30)
async def chatberry(prompt: str) -> str:
    conv = chat.Conversation(
        messages=[chat.Message(role=chat.Role.USER, content=chat.Text.from_string(prompt))]
    )
    conv = (await turn_completer.async_completion(conv)).output_conversation
    output_str = str(conv.messages[-1].content)
    output_str = output_str.strip("'")
    output_str = output_str.strip('"')
    print(conv.messages[-1].metadata["cot"])
    return output_str


ONE_CLICK_APPS_FOLDER = "/Users/evanmays/code/one-click-apps/public/v4/apps/"


async def main(k: int = 1, chatberry_check: bool = False, n: int = 99999999999):
    root_domain = "devbox.com"
    app_name = "app"
    parsed_apps = []
    for pth in sorted(os.listdir(ONE_CLICK_APPS_FOLDER))[:n]:
        print(pth)
        pth = ONE_CLICK_APPS_FOLDER + pth
        try:
            yaml_str, nginx_server_blocks_str, services, frontend_username, frontend_password = (
                caprover_to_docker_compose(
                    pth, {"$$cap_appname": app_name, "$$cap_root_domain": root_domain}
                )
            )
            print(frontend_username)
            print(frontend_password)
            parsed_apps.append((pth, yaml_str, nginx_server_blocks_str, services))
        except Exception:
            logger.exception(f"Exception parsing YAML for {pth}", exc_info=True)
            continue

    async def f(pth, *args, **kwargs):
        async def _inner():
            try:
                metrics = await _test(*args, **kwargs)
                if chatberry_check:
                    metrics["chatberry_nginx_error"] = (
                        "yes"
                        in (
                            await chatberry(
                                f"""{metrics["ax_tree"]}\n\n---\n\nIs the site on an nginx error page, yes or no?"""
                            )
                        ).lower()
                    )
                return metrics
            except Exception as e:
                logger.exception(f"Docker failed {pth} {e}")
                return None

        return await asyncio.gather(*[_inner() for _ in range(k)])

    good = await asyncio.gather(
        *[
            f(pth, app_name, root_domain, yaml_str, nginx_server_blocks_str, services)
            for pth, yaml_str, nginx_server_blocks_str, services in parsed_apps
        ]
    )
    print("total parsed apps:", len(parsed_apps))
    print("total apps loaded:", len(list(filter(None, good))))
    print(f"total apps loaded  w/ all {k=}:", len([a for a in good if a and all(a)]))

    with open("stats.json", "w") as f:
        stats = {
            pth: g
            for g, (pth, yaml_str, nginx_server_blocks_str, services) in zip(good, parsed_apps)
        }
        json.dump(stats, f, indent=2)
    with open("temp.txt", "w") as f:
        f.writelines(
            [
                pth + "\n"
                for is_good, (pth, yaml_str, nginx_server_blocks_str, services) in zip(
                    good, parsed_apps
                )
                if is_good and all(is_good)
            ]
        )


if __name__ == "__main__":
    asyncio.run(chz.entrypoint(main))
