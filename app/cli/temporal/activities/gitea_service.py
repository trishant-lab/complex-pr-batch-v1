from datetime import timedelta

import httpx
import uuid
import re
import hashlib
from temporalio import activity
from temporalio.common import RetryPolicy
from dataclasses import dataclass

from app.cli.temporal.core.base import LaunchpadCLIBaseModel, Activity
from app.cli.temporal.core.log import log_info, log_error
from app.core.settings import AppSettings, ZSegmentSettings, get_settings


@dataclass
class GiteaUser:
    username: str
    email: str


class GiteaProperties(LaunchpadCLIBaseModel):
    tenant: str
    email: str
    base_url: str
    admin_username: str
    admin_password: str
    template_repo: str
    template_owner: str


class GiteaService:
    INVALID_CHARACTERS = re.compile(r"[^a-zA-Z0-9]")

    def __init__(self, properties: GiteaProperties) -> None:
        """
        Initialize the Gitea service
        """
        self.base_url = properties.base_url
        self.auth = httpx.BasicAuth(properties.admin_username, properties.admin_password)
        self.template_repo = properties.template_repo
        self.template_owner = properties.template_owner

    @staticmethod
    def extract_username(email: str) -> str:
        """
        Extract the username from the email
        """
        # Extract the local part of the email (before the "@")
        local_part = email.split("@")[0]

        # Replace invalid characters in the local part with "_"
        base_username = GiteaService.INVALID_CHARACTERS.sub("_", local_part)

        # Append the unique email hash
        return f"{base_username}_{GiteaService.get_email_hash(email)}"

    @staticmethod
    def get_email_hash(email: str) -> str:
        """
        Generate SHA-256 hash and convert to hex
        """
        hash_object = hashlib.sha256(email.encode("utf-8"))
        hash_hex = hash_object.hexdigest()

        # Return the first 8 characters for a short hash
        return hash_hex[:8]

    def create_gitea_user(self, username: str, email: str) -> GiteaUser:
        """
        Create a new Gitea user
        """
        try:
            url = f"{self.base_url}/admin/users"
            payload = {
                "username": username,
                "email": email,
                "password": str(uuid.uuid4()),
                "must_change_password": False,
                "restricted": False,
            }
            response = httpx.post(url, json=payload, auth=self.auth, timeout=30)
            response.raise_for_status()

            log_info(f"User created successfully: {response.json()}")
            return GiteaUser(username=username, email=email)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                log_info(f"User '{username}' already exists. Skipping creation.")
                return GiteaUser(username=username, email=email)
            else:
                log_error(f"Failed to create user '{username}': {e}")
                raise Exception("Error creating user") from e

    def create_repository(self, gitea_user: GiteaUser, repo_name: str) -> None:
        """
        Create a new repository
        """
        try:
            self._create_repo_from_template(gitea_user.username, repo_name)
            log_info("Repository created successfully.")
        except Exception as e:
            log_error(f"Could not create repository for user {gitea_user.username}")
            raise Exception("Error creating repository") from e

    def delete_user(self, username: str) -> None:
        """
        Delete a user
        """
        try:
            url = f"{self.base_url}/admin/users/{username}"
            response = httpx.delete(url, auth=self.auth, timeout=30)
            response.raise_for_status()
            log_info("User deleted successfully.")
        except httpx.HTTPStatusError as e:
            log_error(f"Could not delete user {username}: {e}")
            raise Exception("Error deleting user") from e

    def _create_repo_from_template(self, username: str, repo_name: str) -> None:
        """
        Create a new repository from the template repository
        """
        try:
            url = f"{self.base_url}/repos/gitea_admin/{self.template_repo}/generate"
            payload = {"name": repo_name, "owner": username, "git_content": True}
            response = httpx.post(url, json=payload, auth=self.auth, timeout=30)
            response.raise_for_status()
            log_info(f"Repository created successfully: {response.json()}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                pass
            else:
                log_error(f"Failed to create repository {repo_name}: {e}")
                raise Exception("Error creating repository") from e


class GiteaSetupActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="GiteaSetupActivity")
    async def defn(properties: GiteaProperties) -> None:
        """
        Gitea setup activity
        """
        gitea_service = GiteaService(properties)

        # Extract user info, and repo name from zsegment
        username = GiteaService.extract_username(properties.email)
        email = properties.email
        tenant = properties.tenant
        config: AppSettings = get_settings()
        zsegment_config: ZSegmentSettings = config.zsegment

        gitea_user = GiteaUser(username=username, email=email)

        log_info(f"Creating repository '{tenant}' for user '{username}' with branches: dev and prod")

        # Create repository
        try:
            gitea_service.create_gitea_user(username=username, email=email)
            gitea_service.create_repository(gitea_user=zsegment_config.gitea_admin_username, repo_name=tenant)

            log_info(f"Repository '{tenant}' setup successfully for user '{username}'")

        except Exception as e:
            log_error(f"Failed to setup Gitea repository for tenant '{tenant}': {e}")
            raise
