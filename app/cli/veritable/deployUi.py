import os

from loguru import logger

from app.core.settings import AppSettings, get_settings
from app.cli.common.minioUtils import deploy_ui
from app.cli.veritable.common import VeritableSpec, ProductName


async def deploy_ui_func(veritable: VeritableSpec):
    """
    Deploy UI
    """
    # deploy UI in k8s
    config: AppSettings = get_settings()

    domain_name: str = config.veritable.domain_name
    repo_name = "veritable-ui"

    environment: str = os.getenv("DEPLOYMENT", "integration").lower()

    deploy_ui(
        environment=environment,
        tenant=veritable.tenant,
        image_tag=veritable.imageTag,
        domain_name=domain_name,
        repo_name=repo_name
    )

    logger.info(f"Deployed Veritable UI for {veritable.tenant}")