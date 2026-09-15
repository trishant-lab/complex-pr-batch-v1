import os
import re
from datetime import timedelta
from http.client import HTTPException

import aiohttp
from loguru import logger
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.keycloak_utils import KeycloakAdminClient, get_keycloak_manager
from app.cli.temporal.activities.keycloak_setup import template_render
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info
from app.core.ijson import ijson_loads
from app.core.settings import JeevesSettings, get_settings
from app.one_password_util import OnePasswordUtil
from app.utils.file_operations import get_opendal_file_client

CONTENT_TYPE = "application/json"

LIVE_AGENT_INBOX_NAME = "Live Agent"
BUSINESS_HOURS_OPEN_HOUR = 9
BUSINESS_HOURS_CLOSE_HOUR = 17
BUSINESS_HOURS_OPEN_DAYS = (1, 2, 3, 4, 5)  # Rails wday: 0=Sunday .. 6=Saturday


def _pem_wrap_certificate(certificate_base64: str) -> str:
    """
    Keycloak's realm keys endpoint returns a bare base64 blob; Chatwoot needs PEM armor.
    """
    lines = [certificate_base64[i : i + 64] for i in range(0, len(certificate_base64), 64)]
    return "-----BEGIN CERTIFICATE-----\n" + "\n".join(lines) + "\n-----END CERTIFICATE-----\n"


def _working_hours_day(day_of_week: int) -> dict:
    is_open = day_of_week in BUSINESS_HOURS_OPEN_DAYS
    return {
        "day_of_week": day_of_week,
        "closed_all_day": not is_open,
        "open_all_day": False,
        "open_hour": BUSINESS_HOURS_OPEN_HOUR if is_open else None,
        "open_minutes": 0 if is_open else None,
        "close_hour": BUSINESS_HOURS_CLOSE_HOUR if is_open else None,
        "close_minutes": 0 if is_open else None,
    }


class ChatwootSetup:
    def __init__(
        self: "ChatwootSetup",
        tenant_space_name: str,
        tenant: str,
        product: str,
        config: JeevesSettings,
        realm_name: str | None = None,
    ) -> None:
        self.tenant_space_name: str = tenant_space_name
        self.tenant: str = tenant
        self.config = config
        self.product: str = product
        self.realm_name: str | None = realm_name
        self.chatwoot_base_url = config.chatwoot_base_url
        self.chatwoot_platform_api_token = config.chatwoot_platform_api_token
        self.chatwoot_default_user_password = config.chatwoot_default_user_password
        self.external_base_url = f"https://jeeves-agent.{config.chatwoot_domain}"
        self.keycloak_auth_url = f"https://{tenant}.{config.domain_name}"

        self.onepassword_util = OnePasswordUtil(
            tenant=f"{self.tenant_space_name}",
            server_item="application-config",
            vault=self.product,
        )

    async def create_chatwoot_account(self: "ChatwootSetup") -> int:
        """
        Create a chatwoot account
        """
        headers = {
            "api_access_token": self.chatwoot_platform_api_token,
            "Content-Type": CONTENT_TYPE,
        }

        url = f"{self.chatwoot_base_url}/platform/api/v1/accounts"

        data = {
            "name": self.tenant_space_name,
        }
        async with aiohttp.ClientSession() as session:
            response = await session.post(url=url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=20))
            response_json: dict = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to create account in chatwoot : {response_json}")
                raise RuntimeError(f"Failed to create account in chatwoot : {response_json}")

            logger.info(f"chatwoot account created successfully : {self.tenant_space_name}")
            return response_json.get("id")

    async def create_chatwoot_user(self: "ChatwootSetup") -> dict:
        """
        Create a chatwoot user
        """
        headers = {
            "api_access_token": self.chatwoot_platform_api_token,
            "Content-Type": CONTENT_TYPE,
        }
        url = f"{self.chatwoot_base_url}/platform/api/v1/users"
        _, tenant, space = self.tenant_space_name.split("-")

        data: dict = {
            "name": f"{self.product} Assistant {tenant}{space}",
            "email": f"{self.product.lower()}assistant.{tenant}{space}@314ecorp.com",
            "password": self.chatwoot_default_user_password,
            "custom_attributes": {},
        }
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                url=url,
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            )
            if response.status >= 400:
                logger.error(f"Failed to create user in chatwoot : {response.status}")
                raise RuntimeError(f"Failed to create user in chatwoot : {response.status}")
            logger.info(f"chatwoot user created successfully apiuser {self.tenant_space_name}")
            return await response.json()

    async def add_user_to_account(self: "ChatwootSetup", user_id: int, account_id: int) -> int:
        """
        Add a user to a chatwoot account
            :return:
        """
        headers: dict = {
            "api_access_token": f"{self.chatwoot_platform_api_token}",
            "Content-Type": CONTENT_TYPE,
        }
        url: str = f"{self.chatwoot_base_url}/platform/api/v1/accounts/{account_id}/account_users"

        data: dict = {
            "user_id": user_id,
            "role": "administrator",
        }
        async with aiohttp.ClientSession() as session:
            response = await session.post(url=url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=20))
            response_json = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to add user to chatwoot account : {response_json}")
                raise HTTPException(f"Failed to add user to chatwoot account : {response_json}")
            logger.info(
                f"user added to chatwoot account successfully. user id:{user_id} for space:{self.tenant_space_name}"
            )
            return response.status

    async def create_account_agent_bot(self: "ChatwootSetup", user_api_key: str, account_id: int) -> dict:
        """
        Create a chatwoot account agent bot
        """
        server_url = f"http://jeeves.{self.tenant}.svc.cluster.local:8000"  # NOSONAR

        headers = {
            "api_access_token": user_api_key,
            "Content-Type": CONTENT_TYPE,
        }

        url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/agent_bots"

        data: dict = {
            "name": f"{self.product} AI Bot",
            "description": f"{self.product} AI Bot",
            "outgoing_url": f"{server_url}/public/api/v1/agent/{self.product.lower()}Chatbot",
        }
        async with aiohttp.ClientSession() as session:
            response = await session.post(url=url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=20))
            response_json: dict = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to create agent bot for chatwoot account : {response_json}")
                raise HTTPException(f"Failed to create agent bot for chatwoot account : {response_json}")
            logger.info(f"agent bot created successfully: {self.product} AI Bot")
            return response_json

    async def list_all_inboxes(self: "ChatwootSetup", user_api_key: str, account_id: int) -> dict:
        """
        List all the inboxes in a chatwoot account
        """
        headers = {
            "api_access_token": user_api_key,
            "Content-Type": CONTENT_TYPE,
        }

        url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes"

        async with aiohttp.ClientSession() as session:
            response = await session.get(url=url, headers=headers, timeout=aiohttp.ClientTimeout(total=20))
            response_json: dict = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to list all inboxes for chatwoot account : {response_json}")
                raise HTTPException(f"Failed to list all inboxes for chatwoot account : {response_json}")

            return response_json

    async def create_chatwoot_inbox(self: "ChatwootSetup", user_api_key: str, account_id: int) -> int | None:
        """
        Create a chatwoot inbox
        :return:
        """
        headers: dict = {
            "api_access_token": f"{user_api_key}",
            "Content-Type": CONTENT_TYPE,
        }
        url: str = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes"
        inbox_data: dict = {
            "name": self.product,
            "channel": {
                "type": "web_widget",
                "website_url": "localhost:2000",
            },
        }
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                url=url, headers=headers, json=inbox_data, timeout=aiohttp.ClientTimeout(total=20)
            )
            response_json: dict = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to create inbox bot for chatwoot account : {response_json}")
                raise HTTPException(f"Failed to create inbox bot for chatwoot account : {response_json}")
            logger.info(f"chatwoot inbox created successfully: {self.product}")
            return response_json.get("id")

    async def update_chatwoot_inbox(self: "ChatwootSetup", account_id: int, user_api_key: str, inbox_id: int) -> int:
        """
        Update a chatwoot inbox
        :return:
        """
        api_token_headers: dict = {
            "api_access_token": f"{user_api_key}",
            "Content-Type": CONTENT_TYPE,
        }
        update_data: dict = {
            "name": self.product,
            "enable_auto_assignment": False,
            "enable_email_collect": False,
            "csat_survey_enabled": True,
            "allow_messages_after_resolved": False,
            "greeting_enabled": False,
        }
        url: str = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes/{inbox_id}"

        async with aiohttp.ClientSession() as session:
            response = await session.patch(
                url=url, headers=api_token_headers, json=update_data, timeout=aiohttp.ClientTimeout(total=20)
            )
            response_json = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to update inbox for chatwoot account : {response_json}")
                raise HTTPException(f"Failed to update inbox for chatwoot account : {response_json}")
            logger.info(f"chatwoot inbox updated successfully: inbox id:{inbox_id}")
            return response.status

    async def add_agent_bot_to_inbox(
        self: "ChatwootSetup", agent_bot_id: int, user_api_key: str, account_id: int, inbox_id: int
    ) -> int:
        """
        Add an agent bot to a chatwoot inbox
        :return:
        """
        api_token_headers: dict = {
            "api_access_token": f"{user_api_key}",
            "Content-Type": CONTENT_TYPE,
        }
        agent_bot_data: dict = {
            "agent_bot": agent_bot_id,
        }
        url: str = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes/{inbox_id}/set_agent_bot"
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                url=url, headers=api_token_headers, json=agent_bot_data, timeout=aiohttp.ClientTimeout(total=20)
            )
            response_json: dict = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to add agent bot to inbox for chatwoot account : {response_json}")
                raise HTTPException(f"Failed to add agent bot to inbox for chatwoot account : {response_json}")
            logger.info(f"agent bot added to inbox successfully: agent bot id :{agent_bot_id}")
            return response.status

    async def get_inbox_agent_bot(self: "ChatwootSetup", user_api_key: str, account_id: int, inbox_id: int) -> dict:
        """
        Get the agent bot for a chatwoot inbox
        """
        headers = {
            "api_access_token": user_api_key,
            "Content-Type": CONTENT_TYPE,
        }

        url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes/{inbox_id}/agent_bot"

        async with aiohttp.ClientSession() as session:
            response = await session.get(url=url, headers=headers, timeout=aiohttp.ClientTimeout(total=20))
            response_json: dict = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to get agent bot for chatwoot account : {response.status}")
                raise HTTPException(f"Failed to get agent bot for chatwoot account : {response.status}")

            return response_json

    async def list_all_agent_bots_in_account(self: "ChatwootSetup", user_api_key: str, account_id: int) -> dict:
        """
        List all the agents in a chatwoot account
        """
        headers = {
            "api_access_token": user_api_key,
            "Content-Type": CONTENT_TYPE,
        }

        url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/agent_bots"

        async with aiohttp.ClientSession() as session:
            response = await session.get(url=url, headers=headers, timeout=aiohttp.ClientTimeout(total=20))
            response_json: dict = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to list all agents for chatwoot account : {response.status}")
                raise HTTPException(f"Failed to list all agents for chatwoot account : {response.status}")

            return response_json

    async def create_chatwoot_custom_attributes(self: "ChatwootSetup", user_api_key: str, account_id: int) -> None:
        """
        Create chatwoot custom attributes
        """
        url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/custom_attribute_definitions"
        headers = {
            "api_access_token": user_api_key,
            "Content-Type": "application/json",
        }
        if not os.path.exists(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                f"../{self.product}/templates/chatwoot/chatwoot_custom_attrs.json",
            )
        ):
            logger.warning("chatwoot_custom_attrs.json not found")
            return
        async with aiohttp.ClientSession() as session:
            response = await session.get(url=url, headers=headers, timeout=aiohttp.ClientTimeout(total=30))
            existing_attrs = await response.json() if response.status == 200 else []
            existing_keys = {attr.get("attribute_key") for attr in existing_attrs}

        opendal_file_operations = get_opendal_file_client()
        data = ijson_loads(
            await opendal_file_operations.read_file_str(
                os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    f"../{self.product}/templates/chatwoot/chatwoot_custom_attrs.json",
                )
            )
        )

        for attr in data:
            attr["attribute_key"] = (
                attr.get("attribute_key") or re.sub("[^a-zA-Z0-9]", "", attr.get("attribute_display_name")).lower()
            )
            if attr["attribute_key"] in existing_keys:
                logger.info(f"Custom attribute {attr['attribute_key']} already exists, skipping...")
                continue
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    url=url, headers=headers, json=attr, timeout=aiohttp.ClientTimeout(total=30)
                )
                if response.status != 200:
                    logger.error(f"Failed to create custom attribute with status code: {response.status}")
                    raise HTTPException(f"Failed to create custom attribute with status code: {response.status}")
        logger.info(f"chatwoot custom attributes created successfully : {self.tenant}")

    async def enable_saml_feature(self: "ChatwootSetup", account_id: int) -> None:
        """
        Toggle the per-account `saml` feature flag via Chatwoot's Platform API.
        """
        headers = {
            "api_access_token": self.chatwoot_platform_api_token,
            "Content-Type": CONTENT_TYPE,
        }
        url = f"{self.chatwoot_base_url}/platform/api/v1/accounts/{account_id}"
        async with aiohttp.ClientSession() as session:
            response = await session.patch(
                url=url, headers=headers, json={"features": {"saml": True}}, timeout=aiohttp.ClientTimeout(total=20)
            )
            if response.status >= 400:
                response_json = await response.json()
                logger.error(f"Failed to enable saml feature for account {account_id} : {response_json}")
                raise RuntimeError(f"Failed to enable saml feature for account {account_id} : {response_json}")
        log_info(f"chatwoot saml feature enabled successfully : {self.tenant}")

    def ensure_keycloak_saml_client(self: "ChatwootSetup", account_id: int, template_path: str) -> tuple:
        """
        Create the Keycloak SAML client for this tenant's Chatwoot account, idempotently.

        Returns (sp_entity_id, acs_url).
        """
        sp_entity_id = f"{self.external_base_url}/saml/sp/{account_id}"
        acs_url = f"{self.external_base_url}/omniauth/saml/callback?account_id={account_id}"

        client_config = template_render(
            template_path=template_path,
            template_name="keycloak_chatwoot_saml_client.json",
            template_payload={
                "sp_entity_id": sp_entity_id,
                "acs_url": acs_url,
                "base_url": self.external_base_url,
                "account_id": account_id,
            },
        )

        keycloak_client: KeycloakAdminClient = get_keycloak_manager()
        keycloak_client.create_client(ijson_loads(client_config), self.realm_name)
        log_info(f"keycloak saml client ready for chatwoot : {sp_entity_id}")
        return sp_entity_id, acs_url

    def fetch_signing_certificate(self: "ChatwootSetup") -> str:
        """
        Fetch the realm's active RS256 signing certificate, PEM-armored for Chatwoot.
        """
        keycloak_client: KeycloakAdminClient = get_keycloak_manager()
        keys = keycloak_client.get_realm_keys(realm_name=self.realm_name)
        signing_key = next(
            (
                key
                for key in keys
                if key.get("use") == "SIG" and key.get("algorithm") == "RS256" and key.get("certificate")
            ),
            None,
        )
        if not signing_key:
            raise RuntimeError(f"No active RS256 signing key found for realm {self.realm_name}")
        return _pem_wrap_certificate(signing_key["certificate"])

    async def configure_saml_sso(
        self: "ChatwootSetup", account_id: int, api_key: str, certificate_pem: str, sp_entity_id: str
    ) -> None:
        """
        Push SSO URL / IdP Entity ID / certificate / SP entity ID into Chatwoot's
        account-scoped SAML settings.
        """
        sso_url = f"{self.keycloak_auth_url}/auth/realms/{self.realm_name}/protocol/saml"
        idp_entity_id = f"{self.keycloak_auth_url}/auth/realms/{self.realm_name}"

        headers = {"api_access_token": api_key, "Content-Type": CONTENT_TYPE}
        url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/saml_settings"
        payload = {
            "saml_settings": {
                "sso_url": sso_url,
                "idp_entity_id": idp_entity_id,
                "certificate": certificate_pem,
                "sp_entity_id": sp_entity_id,
            }
        }
        async with aiohttp.ClientSession() as session:
            response = await session.patch(
                url=url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=20)
            )
            if response.status >= 400:
                response_json = await response.json()
                logger.error(f"Failed to configure chatwoot saml settings for account {account_id} : {response_json}")
                raise HTTPException(
                    f"Failed to configure chatwoot saml settings for account {account_id} : {response_json}"
                )
        log_info(f"chatwoot saml sso configured successfully : {self.tenant}")

    async def create_live_agent_inbox(self: "ChatwootSetup", account_id: int, api_key: str) -> None:
        """
        Create the API-channel "Live Agent" inbox with business hours + CSAT enabled, idempotently.
        """
        headers = {"api_access_token": api_key, "Content-Type": CONTENT_TYPE}
        inboxes_url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes"

        async with aiohttp.ClientSession() as session:
            response = await session.get(url=inboxes_url, headers=headers, timeout=aiohttp.ClientTimeout(total=20))
            existing_inboxes = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to list chatwoot inboxes for account {account_id} : {existing_inboxes}")
                raise HTTPException(f"Failed to list chatwoot inboxes for account {account_id} : {existing_inboxes}")
            existing_match = next(
                (inbox for inbox in existing_inboxes.get("payload", []) if inbox.get("name") == LIVE_AGENT_INBOX_NAME),
                None,
            )
            if existing_match:
                log_info(f"chatwoot inbox {LIVE_AGENT_INBOX_NAME!r} already exists, skipping creation")
                inbox_id = existing_match["id"]
            else:
                create_response = await session.post(
                    url=inboxes_url,
                    headers=headers,
                    json={"name": LIVE_AGENT_INBOX_NAME, "channel": {"type": "api"}},
                    timeout=aiohttp.ClientTimeout(total=20),
                )
                inbox = await create_response.json()
                if create_response.status >= 400:
                    logger.error(f"Failed to create chatwoot inbox for account {account_id} : {inbox}")
                    raise HTTPException(f"Failed to create chatwoot inbox for account {account_id} : {inbox}")
                inbox_id = inbox["id"]

            business_hours_payload = {
                "working_hours_enabled": True,
                "csat_survey_enabled": True,
                "timezone": "UTC",
                "working_hours": [_working_hours_day(day_of_week) for day_of_week in range(7)],
            }
            update_response = await session.patch(
                url=f"{inboxes_url}/{inbox_id}",
                headers=headers,
                json=business_hours_payload,
                timeout=aiohttp.ClientTimeout(total=20),
            )
            if update_response.status >= 400:
                response_json = await update_response.json()
                logger.error(f"Failed to configure business hours for inbox {inbox_id} : {response_json}")
                raise HTTPException(f"Failed to configure business hours for inbox {inbox_id} : {response_json}")
        log_info(f"chatwoot live agent inbox ready : {self.tenant}")

    async def setup_saml_and_live_agent_inbox(self: "ChatwootSetup", template_path: str) -> None:
        """
        Enable SAML SSO for this tenant's Chatwoot account and create the Live Agent inbox.

        Requires chatwoot_account_id/chatwoot_api_key already in 1Password —
        i.e. ChatwootSetupActivity must run before ChatwootSamlSetupActivity.
        """
        account_id = await self.onepassword_util.get_key("chatwoot_account_id")
        api_key = await self.onepassword_util.get_key("chatwoot_api_key")
        if not account_id or not api_key:
            raise RuntimeError(
                f"chatwoot_account_id/chatwoot_api_key not found in 1Password for {self.tenant_space_name} "
                "- ChatwootSetupActivity must run before ChatwootSamlSetupActivity"
            )
        account_id = int(account_id)

        await self.enable_saml_feature(account_id=account_id)

        sp_entity_id, _ = self.ensure_keycloak_saml_client(account_id=account_id, template_path=template_path)
        certificate_pem = self.fetch_signing_certificate()
        await self.configure_saml_sso(
            account_id=account_id, api_key=api_key, certificate_pem=certificate_pem, sp_entity_id=sp_entity_id
        )

        await self.create_live_agent_inbox(account_id=account_id, api_key=api_key)

    async def setup(self: "ChatwootSetup") -> None:
        """
        Setup the Chatwoot environment
        """
        # Create Chatwoot Account If not exists
        account_id = await self.onepassword_util.get_key("chatwoot_account_id")
        if not account_id:
            account_id = await self.create_chatwoot_account()
            await self.onepassword_util.insert_if_not_exists(key="chatwoot_account_id", value=str(account_id))
            log_info(f"chatwoot account created successfully : {self.tenant}")

        # Create Chatwoot User If not exists
        api_key = await self.onepassword_util.get_key("chatwoot_api_key")
        if not api_key:
            user = await self.create_chatwoot_user()
            log_info(f"chatwoot user created successfully : {self.tenant}")
            await self.add_user_to_account(user_id=user["id"], account_id=account_id)
            log_info(f"chatwoot user added to account successfully : {self.tenant}")

            await self.onepassword_util.insert_if_not_exists(key="chatwoot_api_key", value=user["access_token"])
            api_key = user["access_token"]

        # Create Chatwoot Agent Bot If not exists
        agents = await self.list_all_agent_bots_in_account(user_api_key=api_key, account_id=account_id)

        if not agents:
            agent_bot = await self.create_account_agent_bot(user_api_key=api_key, account_id=account_id)
            await self.onepassword_util.insert_if_not_exists(key="chatwoot_bot_token", value=agent_bot["access_token"])
            agent_bot_id = agent_bot["id"]
        else:
            agent_bot = agents[0]
            agent_bot_id = agent_bot["id"]

        log_info(f"chatwoot agent bot created successfully : {self.tenant}")

        inboxes = await self.list_all_inboxes(user_api_key=api_key, account_id=account_id)
        if not inboxes["payload"]:
            inbox_id = await self.create_chatwoot_inbox(user_api_key=api_key, account_id=account_id)
        else:
            inbox_id = inboxes["payload"][0]["id"]
        log_info(f"chatwoot inbox created successfully : {self.tenant}")

        if not await self.get_inbox_agent_bot(user_api_key=api_key, account_id=account_id, inbox_id=inbox_id):
            # add agent bot to inbox
            await self.add_agent_bot_to_inbox(
                agent_bot_id=agent_bot_id, user_api_key=api_key, account_id=account_id, inbox_id=inbox_id
            )
            log_info(f"agent bot added to inbox successfully : {self.tenant}")

        # update inbox
        await self.update_chatwoot_inbox(account_id=account_id, user_api_key=api_key, inbox_id=inbox_id)
        log_info(f"chatwoot inbox updated successfully : {self.tenant}")

        # create chatwoot custom attributes
        await self.create_chatwoot_custom_attributes(user_api_key=api_key, account_id=account_id)


class ChatwootSetupActivityModel(LaunchpadCLIBaseModel):
    """
    ChatwootSetupActivityModel
    """

    tenant_space_name: str
    product: str
    tenant: str
    config: JeevesSettings


class ChatwootSetupActivity(Activity):
    """
    ChatwootSetupActivity
    """

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    @activity.defn(name="ChatwootSetupActivity")
    async def defn(activity_model: ChatwootSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        chatwoot_setup = ChatwootSetup(
            tenant_space_name=activity_model.tenant_space_name,
            product=activity_model.product,
            config=activity_model.config,
            tenant=activity_model.tenant,
        )
        await chatwoot_setup.setup()


class ChatwootSamlSetupActivityModel(LaunchpadCLIBaseModel):
    """
    ChatwootSamlSetupActivityModel
    """

    tenant_space_name: str
    tenant: str
    product: str
    realm_name: str
    template_path: str
    config: JeevesSettings


class ChatwootSamlSetupActivity(Activity):
    """
    ChatwootSamlSetupActivity
    """

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    @activity.defn(name="ChatwootSamlSetupActivity")
    async def defn(activity_model: ChatwootSamlSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        chatwoot_setup = ChatwootSetup(
            tenant_space_name=activity_model.tenant_space_name,
            tenant=activity_model.tenant,
            product=activity_model.product,
            config=activity_model.config,
            realm_name=activity_model.realm_name,
        )
        await chatwoot_setup.setup_saml_and_live_agent_inbox(template_path=activity_model.template_path)


class DeleteChatwootAccountActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteChatwootAccountActivityModel
    """

    tenant: str
    product: str
    vault: str


class DeleteChatwootAccountActivity(Activity):
    """
    DeleteChatwootAccountActivity
    """

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
        return RetryPolicy(initial_interval=timedelta(seconds=1), backoff_coefficient=2, maximum_attempts=3)

    @staticmethod
    @activity.defn(name="DeleteChatwootAccountActivity")
    async def defn(activity_model: DeleteChatwootAccountActivityModel) -> None:
        """
        Callable for the activity
        """
        config = get_settings()
        onepassword_util = OnePasswordUtil(
            tenant=f"{activity_model.product.lower()}_{activity_model.tenant}",
            server_item="application-config",
            vault=activity_model.vault,
        )
        account_id = await onepassword_util.get_key("chatwoot_account_id")
        if not account_id:
            logger.error(f"chatwoot account not found : {activity_model.tenant}")
            raise RuntimeError(f"chatwoot account not found : {activity_model.tenant}")
        headers = {
            "api_access_token": config.jeeves.chatwoot_platform_api_token,
            "Content-Type": CONTENT_TYPE,
        }

        url = f"{config.jeeves.chatwoot_base_url}/platform/api/v1/accounts/{account_id}"
        async with aiohttp.ClientSession() as session:
            response = await session.delete(url=url, headers=headers, timeout=aiohttp.ClientTimeout(total=20))
            response_json: dict = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to delete account in chatwoot : {response_json}")
                raise RuntimeError(f"Failed to delete account in chatwoot : {response_json}")

            logger.info(f"chatwoot account deleted successfully : {activity_model.tenant}")
