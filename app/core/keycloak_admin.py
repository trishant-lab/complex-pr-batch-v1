from functools import lru_cache

from keycloak import KeycloakAdmin

from .settings import KeycloakSettings, get_settings


@lru_cache
def get_keycloak_manager() -> "Keycloak":
    """
    Returns Keycloak client instance
    """
    config = get_settings().keycloak
    return Keycloak(config=config)


class Keycloak:
    def __init__(self: "Keycloak", config: KeycloakSettings) -> None:
        self.kc_client: KeycloakAdmin = KeycloakAdmin(
            server_url=f"{config.auth_url}/auth/",
            client_id=config.admin_client_id,
            username=config.username,
            password=config.password,
        )
        self.kc_client.realm_name = config.realm
        self.client_id = config.client_id
        self.realm = config.realm

    @staticmethod
    def _refresh_token(client: KeycloakAdmin, realm: str) -> None:
        client.connection.realm_name = "master"
        client.connection.refresh_token()
        client.connection.realm_name = realm

    def refresh_token(self: "Keycloak") -> None:
        """
        Refresh keycloak client token
        """
        self._refresh_token(self.kc_client, self.realm)

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_realm_roles(client: KeycloakAdmin, realm: str) -> list:
        """
        Helper function to cache results,
        Caching on instance methods leads to memory leaks - B019
        """
        Keycloak._refresh_token(client, realm)
        roles_data = client.get_realm_roles()
        return list(filter(lambda x: x["name"].startswith("VT_"), roles_data))

    def get_realm_roles(self: "Keycloak") -> list:
        """
        Returns keycloak realm roles
        eg: PF_CMS_ADMIN, PF_CMS_USER ...
        """
        return self._get_realm_roles(self.kc_client, self.realm)
