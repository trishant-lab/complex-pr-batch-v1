import os
import re
from http.client import HTTPException

import aiohttp
from temporalio import activity
from temporalio.common import RetryPolicy

import orjson
from loguru import logger
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info
from app.core.settings import JeevesSettings
from app.onepasswordutil import OnePasswordUtil
from datetime import timedelta

CONTENT_TYPE = "application/json"


class ChatwootSetup:
    def __init__(self: "ChatwootSetup", tenant: str, product: str, config: JeevesSettings) -> None:
        self.tenant: str = tenant
        self.config = config
        self.product: str = product
        self.chatwoot_base_url = config.chatwoot_base_url
        self.chatwoot_platform_api_token = config.chatwoot_platform_api_token
        self.chatwoot_default_user_password = config.chatwoot_default_user_password

        self.onepassword_util = OnePasswordUtil(
            tenant=f"{product}_{self.tenant}",
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
            "name": self.tenant,
        }
        async with aiohttp.ClientSession() as session:
            response = await session.post(url=url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=20))
            response_json: dict = await response.json()
            if response.status >= 400:
                logger.error(f"Failed to create account in chatwoot : {response_json}")
                raise RuntimeError(f"Failed to create account in chatwoot : {response_json}")

            logger.info(f"chatwoot account created successfully : {self.tenant}")
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

        data: dict = {
            "name": f"{self.product} Assistant {self.tenant}",
            "email": f"{self.product.lower()}assistant.{self.tenant}@314ecorp.com",
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
            logger.info(f"chatwoot user created successfully apiuser {self.tenant}")
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
            logger.info(f"user added to chatwoot account successfully. user id:{user_id}")
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

        with open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                f"../{self.product}/templates/chatwoot/chatwoot_custom_attrs.json",
            ),
            "rb",
        ) as file:
            data = orjson.loads(file.read())
        for attr in data:
            attr["attribute_key"] = re.sub("[^a-zA-Z0-9]", "", attr.get("attribute_display_name")).lower()
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

    async def setup(self: "ChatwootSetup") -> None:
        """
        Setup the Chatwoot environment
        """
        # Create Chatwoot Account If not exists
        account_id = self.onepassword_util.get_key("chatwoot_account_id")
        if not account_id:
            account_id = await self.create_chatwoot_account()
            self.onepassword_util.insert_if_not_exists(key="chatwoot_account_id", value=str(account_id))
            log_info(f"chatwoot account created successfully : {self.tenant}")

        # Create Chatwoot User If not exists
        api_key = self.onepassword_util.get_key("chatwoot_api_key")
        if not api_key:
            user = await self.create_chatwoot_user()
            log_info(f"chatwoot user created successfully : {self.tenant}")
            await self.add_user_to_account(user_id=user["id"], account_id=account_id)
            log_info(f"chatwoot user added to account successfully : {self.tenant}")

            self.onepassword_util.insert_if_not_exists(key="chatwoot_api_key", value=user["access_token"])
            api_key = user["access_token"]

        # Create Chatwoot Agent Bot If not exists
        agents = await self.list_all_agent_bots_in_account(user_api_key=api_key, account_id=account_id)

        if not agents:
            agent_bot = await self.create_account_agent_bot(user_api_key=api_key, account_id=account_id)
            self.onepassword_util.insert_if_not_exists(key="chatwoot_bot_token", value=agent_bot["access_token"])
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

    tenant: str
    product: str
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
            tenant=activity_model.tenant, product=activity_model.product, config=activity_model.config
        )
        await chatwoot_setup.setup()
