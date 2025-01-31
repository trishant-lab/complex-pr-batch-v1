from datetime import timedelta
from uuid import uuid4

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.keycloakUtils import KeycloakAdminClient, get_keycloak_manager
from app.cli.temporal.core.base import Activity
from app.cli.temporal.penknife.models.penknifespec import PenknifeSpec


class PenknifeUserSetupActivity(Activity):
    """
    PenknifeUserSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=300)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PenknifeUserSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from datetime import datetime

        import orjson
        from loguru import logger

        from app.cli.temporal.activities.penknifeNovuSetup import NovuSetup
        from app.cli.temporal.core.log import log_info
        from app.core.db import DBManager, get_db_manager
        from app.core.settings import PenknifeSettings, get_settings

        subscriber_id = str(uuid4())

        NovuSetup(penknife=penknife).create_subscriber_in_novu(subscriber_id=subscriber_id)

        keycloak_client: KeycloakAdminClient = get_keycloak_manager()
        keycloak_user_id = keycloak_client.get_user_id(username=penknife.email, realm_name=penknife.tenant)

        penknife_config: PenknifeSettings = get_settings().penknife

        try:
            db: DBManager = await get_db_manager(dsn=penknife_config.postgres.dsn)
            attributes = orjson.dumps({"email": penknife.email}).decode("utf-8")
            await db.execute_raw_sql("""SELECT set_config('myvars.user_email', 'api@penknife.app', false);""")
            await db.fetch_one(
                sqlfile="penknife/insertSubscriptionmapping.sql",
                db_schema_name=penknife.tenant,
                **{
                    "schema": penknife.tenant,
                    "user_id": keycloak_user_id,
                    "subscriber_id": subscriber_id,
                    "attributes": attributes,
                },
            )
            await db.fetch_one(
                sqlfile="penknife/insertUseraudit.sql",
                db_schema_name=penknife.tenant,
                **{"schema": penknife.tenant, "email": penknife.email, "datetime": datetime.now()},
            )
            await db.fetch_one(
                sqlfile="penknife/updateOrganization.sql",
                db_schema_name=penknife.tenant,
                **{"schema": penknife.tenant, "companydomain": penknife.companyDomain},
            )

            log_info("User detail is added to postgres")

        except Exception as e:
            logger.error(f"Error while updating user entry in useraudit: {e}")
            raise e
