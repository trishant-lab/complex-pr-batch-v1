from enum import Enum
from app.cli.temporal.core.base import LaunchpadCLIBaseModel


class ResourceSpec(LaunchpadCLIBaseModel):
    """
    ResourceSpec dataclass
    """

    request_memory: str = "500Mi"
    request_cpu: str = "100m"
    limit_memory: str = "5000Mi"
    limit_cpu: str = "3000m"


class PractiflySpec(LaunchpadCLIBaseModel):
    """
    PractiflySpec dataclass
    """

    tenant: str
    firstName: str
    lastName: str
    email: str
    organization: None | str = None
    emailSent: bool = False
    serverSpec: None | ResourceSpec = ResourceSpec()
    cliSpec: None | ResourceSpec = ResourceSpec()


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
