from enum import Enum
from typing import Type

from app.cli.jeeves.models.jeevesSpec import JeevesSpec
from app.cli.veritable.models.veritableSpec import VeritableSpec
from app.cli.veritable.veritable import VeritableWorkflow
from app.cli.jeeves.jeeves import JeevesWorkflow
from app.cli.dexit.dexit import DexitWorkflow


class ProductEnum(str, Enum):
    jeeves = "Jeeves"
    veritable = "Veritable"
    dexit = "Dexit"

    @classmethod
    def get_class(cls, enum_value: 'ProductEnum') -> Type:
        match enum_value:
            case cls.jeeves:
                return JeevesWorkflow
            case cls.veritable:
                return VeritableWorkflow
            case cls.dexit:
                return DexitWorkflow
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")

    @classmethod
    def get_input_model_class(cls, enum_value: 'ProductEnum') -> Type:
        match enum_value:
            case cls.jeeves:
                return JeevesSpec
            case cls.veritable:
                return VeritableSpec
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")
