from enum import Enum
from typing import Type

from app.cli.veritable.veritable import VeritableWorkflow
from app.cli.jeeves.jeeves import JeevesWorkflow


class ProductEnum(str, Enum):
    jeeves = "Jeeves"
    veritable = "Veritable"

    @classmethod
    def get_class(cls, enum_value: 'ProductEnum') -> Type:
        match enum_value:
            case cls.jeeves:
                return JeevesWorkflow
            case cls.veritable:
                return VeritableWorkflow
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")