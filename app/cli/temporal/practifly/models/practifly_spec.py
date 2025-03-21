from enum import Enum

from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec


class ResourceSpec(BaseResourceSpec):
    """
    ResourceSpec dataclass
    """

    limit_memory: str = "5000Mi"


class PractiflySpec(BaseSpec):
    """
    PractiflySpec dataclass
    """

    organization: str | None = None
    emailSent: bool = False
    serverSpec: ResourceSpec | None = ResourceSpec()
    cliSpec: ResourceSpec | None = ResourceSpec()


class PractiflyJobEnum(str, Enum):
    """
    PractiflyJobEnum enum
    """

    DEPLOYMENT = "deployment"
    PROVISIONING = "provisioning"

    @classmethod
    def get_job_name(cls: "PractiflyJobEnum", enum_value: "PractiflyJobEnum") -> str:
        """
        Get the job name for the given enum value
        """
        match enum_value:
            case cls.DEPLOYMENT:
                return "practifly-tenant-deployment-job"
            case cls.PROVISIONING:
                return "practifly-tenant-provisioning-job"
            case _:
                raise ValueError(f"Invalid job type: {enum_value}")

    @classmethod
    def get_argument(cls: "PractiflyJobEnum", enum_value: "PractiflyJobEnum") -> str:
        """
        Get the argument for the given enum value
        """
        match enum_value:
            case cls.DEPLOYMENT:
                return (
                    "cd /app && python3 /app/provisioning/alembic_.py "
                    "--config /provisioningConfig/provisioning-config.json"
                )
            case cls.PROVISIONING:
                return (
                    "cd /app && python3 /app/provisioning/provisioning_.py "
                    "--config /provisioningConfig/provisioning-config.json"
                )
            case _:
                raise ValueError(f"Invalid job type: {enum_value}")

    @classmethod
    def get_expected_log_messages(cls: "PractiflyJobEnum", enum_value: "PractiflyJobEnum") -> list[str]:
        """
        Get the expected log message for the given enum value
        """
        match enum_value:
            case cls.DEPLOYMENT:
                return [
                    "{namespace} Alembic run succeeded!",
                    "{namespace} Deployment run succeeded!",
                ]
            case cls.PROVISIONING:
                return [
                    "{namespace} Provisioning succeeded!",
                ]
            case _:
                raise ValueError(f"Invalid job type: {enum_value}")
