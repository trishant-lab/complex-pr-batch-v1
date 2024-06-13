import requests
from loguru import logger

from app.cli.jeeves.jeeves import JeevesSpec
from app.core.settings import AppSettings, get_settings
from app.onepasswordutil import OnePasswordUtil


class ChatwootSetup:
    def __init__(self, jeeves: JeevesSpec) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.config: AppSettings = get_settings()
        self.chatwoot_base_url = self.config.jeeves.chatwoot_base_url
        self.chatwoot_platform_api_token = self.config.jeeves.chatwoot_platform_api_token
        self.chatwoot_default_user_password = self.config.jeeves.chatwoot_default_user_password

        self.onepassword_util = OnePasswordUtil(
            tenant=f"Jeeves_{self.jeeves.tenant}",
            server_item="application-config",
            vault="Jeeves",
        )

    def create_chatwoot_account(self) -> int:
        """
        Create a chatwoot account
        """
        headers = {
            "api_access_token": self.chatwoot_platform_api_token,
            "Content-Type": "application/json",
        }

        url = f"{self.chatwoot_base_url}/platform/api/v1/accounts"

        data = {
            "name": self.jeeves.tenant,
        }

        response = requests.post(url=url, headers=headers, json=data, timeout=20)

        if response.status_code >= 400:
            logger.error(f"Failed to create account in chatwoot : {response.json()}")
            raise Exception(f"Failed to create account in chatwoot : {response.json()}")

        logger.info(f"chatwoot account created successfully : {self.jeeves.tenant}")
        return response.json().get("id")

    def create_chatwoot_user(self) -> dict:
        """
        Create a chatwoot user
        """
        headers = {
            "api_access_token": self.chatwoot_platform_api_token,
            "Content-Type": "application/json",
        }

        url = f"{self.chatwoot_base_url}/platform/api/v1/users"

        data: dict = {
            "name": f"Jeeves Assistant {self.jeeves.tenant}",
            "email": f"jeevesassistant.{self.jeeves.tenant}@314ecorp.com",
            "password": self.chatwoot_default_user_password,
            "custom_attributes": {},
        }
        response = requests.post(url=url, headers=headers, json=data, timeout=20)
        if response.status_code >= 400:
            logger.error(f"Failed to create user in chatwoot : {response.status_code}")
            raise
        logger.info(f"chatwoot user created successfully apiuser {self.jeeves.tenant}")
        return response.json()

    def add_user_to_account(self, user_id: int, account_id: int) -> int:

        """
        Add a user to a chatwoot account
            :return:
        """
        headers: dict = {
            "api_access_token": f"{self.chatwoot_platform_api_token}",
            "Content-Type": "application/json",
        }
        url: str = f"{self.chatwoot_base_url}/platform/api/v1/accounts/{account_id}/account_users"

        data: dict = {
            "user_id": user_id,
            "role": "administrator",
        }
        response = requests.post(url=url, headers=headers, json=data, timeout=20)
        if response.status_code >= 400:
            logger.error(f"Failed to add user to chatwoot account : {response.json()}")
            raise
        logger.info(f"user added to chatwoot account successfully. user id:{user_id}")
        return response.status_code

    def create_account_agent_bot(self, user_api_key: str, account_id: int) -> dict:
        """
        Create a chatwoot account agent bot
        """

        server_url = f"https://{self.jeeves.tenant}.{self.config.jeeves.domain_name}"

        headers = {
            "api_access_token": user_api_key,
            "Content-Type": "application/json",
        }

        url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/agent_bots"

        data: dict = {
            "name": "Jeeves AI Bot",
            "description": "Jeeves AI Bot",
            "outgoing_url": f"{server_url}/public/api/v1/jeevesAgent/jeevesChatbot",
        }
        response = requests.post(url=url, headers=headers, json=data, timeout=20)
        if response.status_code >= 400:
            logger.error(f"Failed to create agent bot for chatwoot account : {response.json()}")
            raise
        logger.info("agent bot created successfully: Jeeves AI Bot")
        return response.json()

    def list_all_inboxes(self, user_api_key: str, account_id: int) -> dict:

        headers = {
            "api_access_token": user_api_key,
            "Content-Type": "application/json",
        }

        url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes"

        response = requests.get(url=url, headers=headers, timeout=20)

        if response.status_code >= 400:
            logger.error(f"Failed to list all inboxes for chatwoot account : {response.status_code}")
            raise Exception(f"Failed to list all inboxes for chatwoot account : {response.status_code}")

        return response.json()

    def create_chatwoot_inbox(self, user_api_key: str, account_id: int) -> int | None:
        """
        Create a chatwoot inbox
        :return:
        """
        headers: dict = {
            "api_access_token": f"{user_api_key}",
            "Content-Type": "application/json",
        }
        url: str = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes"
        inbox_data: dict = {
            "name": "Jeeves",
            "channel": {
                "type": "web_widget",
                "website_url": "localhost:2000",
            },
        }
        response = requests.post(url=url, headers=headers, json=inbox_data, timeout=20)
        if response.status_code >= 400:
            logger.error(f"Failed to create inbox bot for chatwoot account : {response.json()}")
            raise
        logger.info("chatwoot inbox created successfully: Jeeves")
        return response.json().get("id")

    def update_chatwoot_inbox(self, account_id: int, user_api_key: str, inbox_id: int) -> int:
        """
        Update a chatwoot inbox
        :return:
        """
        api_token_headers: dict = {
            "api_access_token": f"{user_api_key}",
            "Content-Type": "application/json",
        }
        update_data: dict = {
            "name": "Jeeves",
            "enable_auto_assignment": False,
            "enable_email_collect": False,
            "csat_survey_enabled": True,
            "allow_messages_after_resolved": False,
            "greeting_enabled": False,
        }
        url: str = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes/{inbox_id}"

        response = requests.patch(url=url, headers=api_token_headers, json=update_data, timeout=20)
        if response.status_code >= 400:
            logger.error(f"Failed to update inbox for chatwoot account : {response.json()}")
            raise
        logger.info(f"chatwoot inbox updated successfully: inbox id:{inbox_id}")
        return response.status_code

    def add_agent_bot_to_inbox(self, agent_bot_id: int, user_api_key: str, account_id: int, inbox_id: int,) -> int:
        """
        Add an agent bot to a chatwoot inbox
        :return:
        """
        api_token_headers: dict = {
            "api_access_token": f"{user_api_key}",
            "Content-Type": "application/json",
        }
        agent_bot_data: dict = {
            "agent_bot": agent_bot_id,
        }
        url: str = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes/{inbox_id}/set_agent_bot"
        response = requests.post(url=url, headers=api_token_headers, json=agent_bot_data, timeout=20)
        if response.status_code >= 400:
            logger.error(f"Failed to add agent bot to inbox for chatwoot account : {response.json()}")
            raise
        logger.info(f"agent bot added to inbox successfully: agent bot id :{agent_bot_id}")
        return response.status_code

    def get_inbox_agent_bot(self, user_api_key: str, account_id: int, inbox_id: int) -> dict:
        """
        Get the agent bot for a chatwoot inbox
        """
        headers = {
            "api_access_token": user_api_key,
            "Content-Type": "application/json",
        }

        url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/inboxes/{inbox_id}/agent_bot"

        response = requests.get(url=url, headers=headers, timeout=20)

        if response.status_code >= 400:
            logger.error(f"Failed to get agent bot for chatwoot account : {response.status_code}")
            raise Exception(f"Failed to get agent bot for chatwoot account : {response.status_code}")

        return response.json()

    def list_all_agent_bots_in_account(self, user_api_key: str, account_id: int) -> dict:
        """
        List all the agents in a chatwoot account
        """
        headers = {
            "api_access_token": user_api_key,
            "Content-Type": "application/json",
        }

        url = f"{self.chatwoot_base_url}/api/v1/accounts/{account_id}/agent_bots"

        response = requests.get(url=url, headers=headers, timeout=20)

        if response.status_code >= 400:
            logger.error(f"Failed to list all agents for chatwoot account : {response.status_code}")
            raise Exception(f"Failed to list all agents for chatwoot account : {response.status_code}")

        return response.json()

    def setup(self):
        """
        Setup the Chatwoot environment
        """
        # Create Chatwoot Account If not exists
        account_id = self.onepassword_util.get_key("chatwoot_account_id")
        if not account_id:
            account_id = self.create_chatwoot_account()
            self.onepassword_util.insert_if_not_exists(key="chatwoot_account_id", value=str(account_id))

        # Create Chatwoot User If not exists
        api_key = self.onepassword_util.get_key("chatwoot_api_key")
        if not api_key:
            user = self.create_chatwoot_user()
            self.add_user_to_account(user_id=user['id'], account_id=account_id)

            self.onepassword_util.insert_if_not_exists(key="chatwoot_api_key", value=user['access_token'])
            api_key = user['access_token']

        # Create Chatwoot Agent Bot If not exists
        agents = self.list_all_agent_bots_in_account(user_api_key=api_key, account_id=account_id)

        if not agents:
            agent_bot = self.create_account_agent_bot(user_api_key=api_key, account_id=account_id)
            self.onepassword_util.insert_if_not_exists(key="chatwoot_bot_token", value=agent_bot['access_token'])
            agent_bot_id = agent_bot['id']
        else:
            agent_bot = agents[0]
            agent_bot_id = agent_bot['id']

        inboxes = self.list_all_inboxes(user_api_key=api_key, account_id=account_id)
        if not inboxes['payload']:
            inbox_id = self.create_chatwoot_inbox(user_api_key=api_key, account_id=account_id)
        else:
            inbox_id = inboxes['payload'][0]['id']

        if not self.get_inbox_agent_bot(user_api_key=api_key, account_id=account_id, inbox_id=inbox_id):
            # add agent bot to inbox
            self.add_agent_bot_to_inbox(
                agent_bot_id=agent_bot_id,
                user_api_key=api_key,
                account_id=account_id,
                inbox_id=inbox_id
            )

        # update inbox
        self.update_chatwoot_inbox(account_id=account_id, user_api_key=api_key, inbox_id=inbox_id)
