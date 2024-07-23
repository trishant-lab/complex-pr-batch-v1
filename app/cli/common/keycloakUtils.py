from functools import lru_cache

from keycloak import KeycloakAdmin

from app.core.settings import KeycloakSettings, get_settings


class KeycloakAdminClient:
    def __init__(self: "KeycloakAdminClient", config: KeycloakSettings) -> None:
        self.kc_client: KeycloakAdmin = KeycloakAdmin(
            server_url=f"{config.auth_url}/auth/",
            client_id=config.admin_client_id,
            username=config.username,
            password=config.password,
        )
        self.realm = config.admin_realm
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

    def create_realm(self: "KeycloakAdminClient", realm_config: dict, skip_exists: bool = True) -> None:
        """
        Create keycloak realm
        """
        self.kc_client.connection.refresh_token()
        self.kc_client.create_realm(payload=realm_config, skip_exists=skip_exists)

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

    def create_user(self: "KeycloakAdminClient", user_config: dict, realm_name: str) -> str | dict:
        """
        Create keycloak user
        """
        self.kc_client.connection.realm_name = realm_name
        return self.kc_client.create_user(payload=user_config, exist_ok=True)

    def get_user_id(self: "KeycloakAdminClient", username: str, realm_name: str) -> str:
        """
        Returns keycloak user id
        """
        self.kc_client.connection.realm_name = realm_name
        return self.kc_client.get_user_id(username=username)

    def get_users(
        self: "KeycloakAdminClient",
        realm_name: str,
        query: None | dict = None,
    ) -> list:
        """
        Returns keycloak users
        """
        self.kc_client.connection.realm_name = realm_name
        return self.kc_client.get_users(query=query)

    def get_user(self: "KeycloakAdminClient", user_id: str, realm_name: str) -> dict:
        """
        Returns keycloak user
        """
        self.kc_client.connection.realm_name = realm_name
        return self.kc_client.get_user(user_id=user_id)

    def set_user_password(self: "KeycloakAdminClient", user_id: str, password: str, realm_name: str) -> None:
        """
        Set keycloak user password
        """
        self.kc_client.connection.realm_name = realm_name
        self.kc_client.set_user_password(user_id=user_id, password=password)

    def create_client(self: "KeycloakAdminClient", client_config: dict, realm_name: str) -> None:
        """
        Create keycloak client
        """
        self.kc_client.connection.realm_name = realm_name
        self.kc_client.create_client(payload=client_config, skip_exists=True)

    def get_client_id(self: "KeycloakAdminClient", client: str, realm_name: str) -> str:
        """
        Returns keycloak client
        """
        self.kc_client.connection.realm_name = realm_name
        return self.kc_client.get_client_id(client_id=client)

    def create_client_role(self: "KeycloakAdminClient", client_id: str, role_config: dict, realm_name: str) -> None:
        """
        Create keycloak client role
        """
        self.kc_client.connection.realm_name = realm_name
        self.kc_client.create_client_role(payload=role_config, client_role_id=client_id, skip_exists=True)

    def get_client_roles(self: "KeycloakAdminClient", client_id: str, realm_name: str) -> list:
        """
        Returns keycloak client roles
        """
        self.kc_client.connection.realm_name = realm_name
        return self.kc_client.get_client_roles(client_id=client_id)

    def get_realm_roles(self: "KeycloakAdminClient", realm_name: str) -> list:
        """
        Returns keycloak realm roles
        """
        self.kc_client.connection.realm_name = realm_name
        return self.kc_client.get_realm_roles()

    def assign_client_role(
        self: "KeycloakAdminClient", realm_name: str, user_id: str, client_id: str, roles: list
    ) -> None:
        """
        Assign client roles
        """
        self.kc_client.connection.realm_name = realm_name
        self.kc_client.assign_client_role(user_id=user_id, client_id=client_id, roles=roles)

    def create_authentication_flow(self: "KeycloakAdminClient", flow_config: dict, realm_name: str) -> None:
        """
        Create keycloak authentication flow
        """
        self.kc_client.connection.realm_name = realm_name
        self.kc_client.create_authentication_flow(payload=flow_config, skip_exists=True)

    def get_authentication_flows(self: "KeycloakAdminClient", realm_name: str) -> list:
        """
        Returns keycloak authentication flows
        """
        self.kc_client.connection.realm_name = realm_name
        return self.kc_client.get_authentication_flows()

    def create_identity_provider(self: "KeycloakAdminClient", idp_config: dict, realm_name: str) -> None:
        """
        Create keycloak identity provider
        """
        self.kc_client.connection.realm_name = realm_name
        self.kc_client.create_idp(payload=idp_config)

    def get_identity_providers(self: "KeycloakAdminClient", realm_name: str) -> list:
        """
        Returns keycloak identity providers
        """
        self.kc_client.connection.realm_name = realm_name
        return self.kc_client.get_idps()

    def add_mapper_to_idp(self: "KeycloakAdminClient", idp_alias: str, mapper_config: dict, realm_name: str) -> None:
        """
        Add mapper to identity provider
        """
        self.kc_client.connection.realm_name = realm_name
        self.kc_client.add_mapper_to_idp(idp_alias=idp_alias, payload=mapper_config)

    def get_mappers(self: "KeycloakAdminClient", idp_alias: str, realm_name: str) -> list:
        """
        Returns keycloak mappers
        """
        self.kc_client.connection.realm_name = realm_name
        return self.kc_client.get_idp_mappers(idp_alias=idp_alias)


@lru_cache
def get_keycloak_manager() -> "KeycloakAdminClient":
    """
    Returns Keycloak client instance
    """
    config = get_settings().keycloak
    return KeycloakAdminClient(config=config)
