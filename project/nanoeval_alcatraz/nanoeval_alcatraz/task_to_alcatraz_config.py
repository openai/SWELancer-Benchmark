from __future__ import annotations

import logging

from alcatraz.clusters.local import ClusterConfig
from alcatraz.clusters.swarm import SwarmConfig
from nanoeval.solvers.computer_tasks.code_execution_interface import ComputerConfiguration

logger = logging.getLogger(__name__)


def task_to_alcatraz_config(task: ComputerConfiguration, config: ClusterConfig) -> ClusterConfig:
    # TODO, we should really just have a ClusterConfig as part of the task itself

    if task.azure_vm_sku:
        if isinstance(config, SwarmConfig):
            logger.info("Using custom azure_vm_sku: %s", task.azure_vm_sku)
            config = config.model_copy(update={"azure_vm_sku": task.azure_vm_sku})
        else:
            logger.warning(
                "Task specified azure_vm_sku=%s, but config is not a SwarmConfig, cannot use custom SKU",
                task.azure_vm_sku,
            )
    if task.docker_image:
        logger.info("Using custom docker image: %s", task.docker_image)
        config = config.model_copy(update={"image": task.docker_image})
    if task.docker_compose_yaml:
        logger.info(f"Using custom docker-compose.yaml: {task.docker_compose_yaml}")
        config = config.model_copy(update={"docker_compose_yaml": task.docker_compose_yaml})
    if task.side_images:
        logger.info(f"Using custom side images: {task.side_images}")
        config = config.model_copy(update={"side_images": task.side_images})

    if task.azure_files_config:
        logger.info("Using custom azure_files_config: %s", task.azure_files_config)
        config = config.model_copy(update={"azure_files_config": task.azure_files_config})

    if task.azure_container_config:
        logger.info("Using custom azure_container_config: %s", task.azure_container_config)
        config = config.model_copy(update={"azure_container_config": task.azure_container_config})

    if task.alcatraz_limits:
        logger.info("Using custom limits: %s", task.alcatraz_limits)
        config = config.model_copy(update={"limits": task.alcatraz_limits})

    if task.volumes_config:
        logger.info("Using custom volumes_config: %s", task.volumes_config)
        config = config.model_copy(update={"volumes_config": task.volumes_config})

    if task.shm_size:
        logger.info("Using custom shm size: %s", task.shm_size)
        config = config.model_copy(update={"shm_size": task.shm_size})

    if task.mem_limit:
        logger.info("Using custom mem limit: %s", task.mem_limit)
        config = config.model_copy(update={"mem_limit": task.mem_limit})

    if task.jupyter_setup:
        logger.info("Using custom jupyter setup: %s", task.jupyter_setup)
        config = config.model_copy(update={"jupyter_setup": task.jupyter_setup})

    if task.environment:
        logger.info("Using custom environment: %s", task.jupyter_setup)
        config = config.model_copy(update={"environment": task.environment})

    return config
