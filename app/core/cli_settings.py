from enum import Enum
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator


class WorkerQueues(str, Enum):
    dexit_onboarding = "dexit_onboarding"
    dexit_deboarding = "dexit_deboarding"
    jeeves_onboarding = "jeeves_onboarding"
    jeeves_deboarding = "jeeves_deboarding"
    hdp_onboarding = "hdp_onboarding"
    hdp_deboarding = "hdp_deboarding"
    penknife_onboarding = "penknife_onboarding"
    penknife_deboarding = "penknife_deboarding"
    practifly_onboarding = "practifly_onboarding"
    practifly_deboarding = "practifly_deboarding"
    zsegment_onboarding = "zsegment_onboarding"
    zsegment_deboarding = "zsegment_deboarding"


class WorkerConfig(BaseModel):
    workers: dict[WorkerQueues, set]
    count: int = Field(gt=0)

    @field_validator("workers", mode="before")
    @classmethod
    def validate_worker(cls: type["WorkerConfig"], workers: dict[WorkerQueues, set]) -> dict[WorkerQueues, set]:
        """
        Validates type of workers
        """
        if not workers:
            msg = "No workflows found"
            raise ValueError(msg)
        from app.cli.temporal.core.base import ScheduleWorkflow, Workflow

        invalid_workflows = []
        for _queue, _workflows in workers.items():
            if not _workflows:
                msg = f"No workflows for queue: {_queue}"
                raise ValueError(msg)
            for _workflow in _workflows:
                if not issubclass(_workflow, Workflow) and not issubclass(_workflow, ScheduleWorkflow):
                    invalid_workflows.append(_workflow)
        if invalid_workflows:
            msg = f"Invalid workflows: {invalid_workflows}"
            raise ValueError(msg)
        return workers


@lru_cache
def get_workers_config() -> dict[str, WorkerConfig]:
    """
    Get the workers configuration
    """
    from app.cli.temporal.dexit.workflows.onboarding import DexitOnboardingWorkflow
    from app.cli.temporal.dexit.workflows.deprovisioning import DexitDeProvisioningWorkflow
    from app.cli.temporal.jeeves.workflows.onboarding import JeevesOnboardingWorkflow
    from app.cli.temporal.jeeves.workflows.deprovisioning import JeevesDeProvisioningWorkflow
    from app.cli.temporal.hdp.workflows.onboarding import HDPOnboardingWorkflow
    from app.cli.temporal.penknife.workflows.onboarding import PenknifeOnboardingWorkflow
    from app.cli.temporal.penknife.workflows.deprovisioning import PenknifeDeProvisioningWorkflow
    from app.cli.temporal.practifly.workflows.onboarding import PractiflyOnboardingWorkflow
    from app.cli.temporal.practifly.workflows.deprovisioning import PractiflyDeProvisioningWorkflow
    from app.cli.temporal.zsegment.workflows.onboarding import ZSegmentOnboardingWorkflow

    workers_config = {
        "WORKER_1_PROCESS": {
            "workers": {
                WorkerQueues.dexit_onboarding: {DexitOnboardingWorkflow},
                WorkerQueues.jeeves_onboarding: {JeevesOnboardingWorkflow},
                WorkerQueues.hdp_onboarding: {HDPOnboardingWorkflow},
                WorkerQueues.penknife_onboarding: {PenknifeOnboardingWorkflow},
                WorkerQueues.practifly_onboarding: {PractiflyOnboardingWorkflow},
                WorkerQueues.zsegment_onboarding: {ZSegmentOnboardingWorkflow},
            },
            "count": 1,
        },
        "WORKER_2_PROCESS": {
            "workers": {
                WorkerQueues.dexit_deboarding: {DexitDeProvisioningWorkflow},
                WorkerQueues.jeeves_deboarding: {JeevesDeProvisioningWorkflow},
                WorkerQueues.penknife_deboarding: {PenknifeDeProvisioningWorkflow},
                WorkerQueues.practifly_deboarding: {PractiflyDeProvisioningWorkflow},
            },
            "count": 1,
        },
        # todo scheduler worker for k8s config check
    }

    return {k: WorkerConfig.model_validate(v) for k, v in workers_config.items()}
