from app.cli.temporal.core.base import LaunchpadCLIBaseModel


class CreateStarRocksCatalogActivityModel(LaunchpadCLIBaseModel):
    """
    CreateStarRocksCatalogActivityModel
    """

    tenant: str = ""
    catalog_name: str = ""
    warehouse_access_key: str = ""
    warehouse_secret_key: str = ""
