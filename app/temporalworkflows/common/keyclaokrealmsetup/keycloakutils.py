from keycloak import KeycloakAdmin
from app.core.settings import KeycloakSettings


class KeycloakAdminClient:
    def __init__(self: "KeycloakAdminClient", config: KeycloakSettings) -> None:
        self.kc_client: KeycloakAdmin = KeycloakAdmin(
            server_url=f"{config.auth_url}/auth/",
            client_id=config.admin_client_id,
            username=config.username,
            password=config.password,
        )
        self.kc_client.connection.realm_name = config.realm

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
        self.kc_client.create_realm(payload=realm_config)

    def delete_realm(self: "KeycloakAdminClient", realm_name: str) -> None:
        """

        :param realm_name:
        :type realm_name:
        :return:
        :rtype:
        """
        self.kc_client.delete_realm(realm_name)

    def create_user(self: "KeycloakAdminClient", user_config: dict, realm_name: str) -> None:
        """
        Create keycloak user
        """
        self.kc_client.connection.realm_name = realm_name
        self.kc_client.create_user(payload=user_config)

