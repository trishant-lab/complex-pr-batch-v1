from loguru import logger
from pydantic import BaseModel
import mysql.connector

from app.core.product_settings.muspell_archive import MuspellArchiveSettings


class CreateStarRocksInputModel(BaseModel):
    muspell_config: MuspellArchiveSettings
    tenant: str
    warehouse_access_key: str
    warehouse_secret_key: str
    catalog_name: str


async def create_starrocks_catalog(starrocks_input: CreateStarRocksInputModel) -> None:
    """
    Create a StarRocks catalog
    """
    muspell_config = starrocks_input.muspell_config
    tenant = starrocks_input.tenant
    catalog_name = starrocks_input.catalog_name

    create_catalog_sql = f"""
        CREATE EXTERNAL CATALOG IF NOT EXISTS `{catalog_name}`
        PROPERTIES (
            "aws.s3.access_key"  =  "{starrocks_input.warehouse_access_key}",
            "aws.s3.secret_key"  =  "{starrocks_input.warehouse_secret_key}",
            "client.factory"  =  "com.starrocks.connector.iceberg.IcebergAwsClientFactory",
            "aws.s3.endpoint"  =  "{muspell_config.s3_endpoint}",
            "iceberg.catalog.uri"  =  "{muspell_config.lakekeeper_uri}",
            "aws.s3.enable_path_style_access"  =  "true",\
            "iceberg.catalog.security"  =  "none",
            "iceberg.catalog.warehouse"  =  "{catalog_name}",
            "type"  =  "iceberg",
            "iceberg.catalog.type"  =  "rest"
        )
    """

    try:
        conn = mysql.connector.connect(
            host=muspell_config.starrocks_host,
            port=muspell_config.starrocks_port,
            user=muspell_config.starrocks_user,
            password=muspell_config.starrocks_password,
        )
        cursor = conn.cursor()

        cursor.execute(create_catalog_sql)

        logger.info(f"Successfully created StarRocks external catalog '{catalog_name}' for tenant '{tenant}'")

        # Close connections
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Failed to create StarRocks external catalog: {e!r}")
        raise StarRocksCatalogCreationError(f"Failed to create StarRocks external catalog: {e!r}")


class StarRocksCatalogCreationError(Exception):
    """
    Exception raised when creating a StarRocks catalog fails
    """

    pass


class RegisterStarrocksUserModel(BaseModel):
    muspell_config: MuspellArchiveSettings
    tenant: str
    user_name: str
    user_password: str
    catalog_name: str


async def register_user(starrocks_input: RegisterStarrocksUserModel) -> None:
    """
    Create a StarRocks user
    """
    muspell_config = starrocks_input.muspell_config
    tenant = starrocks_input.tenant
    catalog_name = starrocks_input.catalog_name

    try:
        conn = mysql.connector.connect(
            host=muspell_config.starrocks_host,
            port=muspell_config.starrocks_port,
            user=muspell_config.starrocks_user,
            password=muspell_config.starrocks_password,
        )
        cursor = conn.cursor()

        cursor.execute(f"""
        CREATE USER IF NOT EXISTS {starrocks_input.user_name} IDENTIFIED WITH mysql_native_password BY
        '{starrocks_input.user_password}'  PROPERTIES ('catalog'='{catalog_name}');""")
        cursor.execute(f"GRANT ALL ON ALL GLOBAL FUNCTIONS TO {starrocks_input.user_name};")
        cursor.execute(f"GRANT USAGE ON CATALOG {catalog_name} TO USER {starrocks_input.user_name};")
        cursor.execute(f"SET CATALOG {catalog_name};")
        cursor.execute(f"GRANT ALL ON ALL DATABASES TO {starrocks_input.user_name};")
        cursor.execute(f"GRANT ALL ON ALL TABLES IN ALL DATABASES TO {starrocks_input.user_name};")
        cursor.execute(f"GRANT USAGE ON CATALOG externaldata TO USER {starrocks_input.user_name};")
        cursor.execute("SET CATALOG externaldata;")
        cursor.execute(f"GRANT ALL ON ALL DATABASES TO USER {starrocks_input.user_name};")
        cursor.execute(f"GRANT ALL ON ALL TABLES IN ALL DATABASES TO USER {starrocks_input.user_name};")

        logger.info(f"Successfully created StarRocks user for tenant '{tenant}'")

        # Close connections
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Failed to create StarRocks user: {e!r}")
        raise RegisterStarrocksUserError(f"Failed to create StarRocks user: {e!r}")


class RegisterStarrocksUserError(Exception):
    """
    Exception raised when creating a starrocks user fails
    """

    pass
