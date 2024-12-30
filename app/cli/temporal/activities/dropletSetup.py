from datetime import timedelta

import digitalocean
from digitalocean import Droplet
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info
from app.core.settings import APP_CONFIG


def get_digitalocean_client() -> digitalocean.Manager:
    """
    Get a digitalocean client
    """
    return digitalocean.Manager(token=APP_CONFIG.digitalocean.api_token)


def get_ssh_keys() -> list[str]:
    """
    Get the ssh keys
    """
    manager = get_digitalocean_client()
    ssh_keys = manager.get_all_sshkeys()
    return [ssh_key for ssh_key in ssh_keys if ssh_key.name == APP_CONFIG.digitalocean.ssh_key_name]


def get_droplet(name: str) -> list[Droplet]:
    """
    Get a droplet
    """
    manager = get_digitalocean_client()
    return [droplet for droplet in manager.get_all_droplets() if droplet.name == name]


def create_droplet(product: str, name: str, ssh_keys: list[str], script: str) -> Droplet:
    """
    Create a droplet
    """
    droplet: Droplet = Droplet(
        token=APP_CONFIG.digitalocean_api_token,
        name=name,
        region=APP_CONFIG.digitalocean.region,
        size=APP_CONFIG.digitalocean.size,
        image=APP_CONFIG.digitalocean.image,
        tags=[product, name],
        monitoring=True,
        ssh_keys=ssh_keys,
        backups=False,
        features=["install_agent"],
        enable_private_networking=True,
        enable_ipv6=True,
        user_data=script,
    )

    droplet.create()

    return droplet


def delete_droplet(name: str) -> None:
    """
    Delete a droplet
    """
    manager = get_digitalocean_client()
    for droplet in manager.get_all_droplets():
        if droplet.name == name:
            droplet.destroy()
            break


class CreateDropletActivityModel(LaunchpadCLIBaseModel):
    """
    CreateDropletActivityModel
    """

    product: str
    name: str
    script: str


class CreateDropletActivity(Activity):
    """
    CreateDropletActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(minutes=10)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @activity.defn(name="create_droplet")
    async def create_droplet(self, activity_input: CreateDropletActivityModel) -> str:
        """
        Create droplet
        """
        # check if the droplet already exists
        droplets = get_droplet(activity_input.name)
        if droplets:
            log_info(f"Droplet {activity_input.name} already exists")
            return droplets[0].ip_address

        # create the droplet
        ssh_keys = get_ssh_keys()

        droplet: Droplet = create_droplet(
            product=activity_input.product,
            name=activity_input.name,
            ssh_keys=ssh_keys,
            script=activity_input.script,
        )

        # wait for the droplet to be ready
        actions = droplet.get_actions()
        for action in actions:
            action.wait()

        return droplet.ip_address
