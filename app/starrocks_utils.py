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
            "hive.metastore.type"  =  "hive",
            "aws.s3.secret_key"  =  "{starrocks_input.warehouse_secret_key}",
            "aws.s3.enable_path_stype_access" = "true",
            "aws.s3.endpoint"  =  "{muspell_config.s3_endpoint}",
            "hive.metastore.uris"  =  "thrift://{tenant}-metastore.datalake.svc.cluster.local:9083",
            "type"  =  "iceberg",
            "iceberg.catalog.type"  =  "hive"
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
