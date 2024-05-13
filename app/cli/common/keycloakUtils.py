from functools import lru_cache

from keycloak import KeycloakAdmin
from loguru import logger

from app.core.settings import KeycloakSettings, get_settings


class KeycloakAdminClient:
    def __init__(self: "KeycloakAdminClient", config: KeycloakSettings) -> None:
        self.kc_client: KeycloakAdmin = KeycloakAdmin(
            server_url=f"{config.auth_url}/auth/",
            client_id=config.admin_client_id,
            username=config.username,
            password=config.password,
        )
        self.realm = config.realm
        self.kc_client.connection.realm_name = self.realm

    @staticmethod
    def _refresh_token(client: KeycloakAdmin, realm: str) -> None:
        client.connection.realm_name = "master"
        client.connection.refresh_token()
        client.connection.realm_name = realm

    def refresh_token(self: "KeycloakAdminClient") -> None:
        """
        Refresh keycloak client token
        """
        self._refresh_token(self.kc_client, self.realm)

    def get_all_realms(self: "KeycloakAdminClient") -> list:
        """
        Returns keycloak realms
        """
        return self.kc_client.get_realms()

    def get_realm(self: "KeycloakAdminClient", realm_name: str) -> dict:
        """
        Returns keycloak realm
        """
        return self.kc_client.get_realm(realm_name)

    def create_realm(self: "KeycloakAdminClient", realm_config: dict) -> None:
        """
        Create keycloak realm
        """
        self.kc_client.connection.refresh_token()
        self.kc_client.create_realm(payload=realm_config, skip_exists=True)

    def delete_realm(self: "KeycloakAdminClient", realm_name: str) -> None:
        """

        :param realm_name:
        :type realm_name:
        :return:
        :rtype:
        """
        # check if realm exists
        realms = [row["realm"] for row in self.get_all_realms()]
        if realm_name in realms:
            self.kc_client.delete_realm(realm_name)
        return

    def create_user(self: "KeycloakAdminClient", user_config: dict, realm_name: str) -> None:
        """
        Create keycloak user
        """
        self.kc_client.connection.realm_name = realm_name
        self.kc_client.create_user(payload=user_config, exist_ok=True)


@lru_cache
def get_keycloak_manager() -> "KeycloakAdminClient":
    """
    Returns Keycloak client instance
    """
    config = get_settings().keycloak
    return KeycloakAdminClient(config=config)
