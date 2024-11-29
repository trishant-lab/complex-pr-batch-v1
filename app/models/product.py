from enum import Enum

from app.cli.temporal.dexit.dexit import DexitWorkflow
from app.cli.temporal.dexit.models.dexitSpec import DexitSpec
from app.cli.temporal.jeeves.jeeves import JeevesWorkflow
from app.cli.temporal.jeeves.models.jeevesSpec import JeevesSpec
from app.cli.temporal.penknife.models.penknifespec import PenknifeSpec
from app.cli.temporal.penknife.penknife import PenknifeWorkflow
from app.cli.temporal.hdp.hdp import HdpWorkflow
from app.cli.temporal.hdp.models.hdpSpec import HDPSpec
from app.cli.temporal.practifly.models.practiflySpec import PractiflySpec
from app.cli.temporal.practifly.practifly import PractiflyWorkflow
from app.cli.temporal.zsegment.zsegment import ZSegmentWorkflow
from app.cli.temporal.zsegment.models.zsegmentSpec import ZSegmentSpec
from app.cli.temporal.veritable.veritable import VeritableWorkflow
from app.cli.temporal.veritable.models.veritableSpec import VeritableSpec


class ProductEnum(str, Enum):
    jeeves = "Jeeves"
    veritable = "Veritable"
    dexit = "Dexit"
    penknife = "Penknife"
    hdp = "Hdp"
    zsegment = "Zsegment"
    practifly = "Practifly"

    @classmethod
    def get_class(cls: "ProductEnum", enum_value: "ProductEnum") -> type:
        """
        Get the class for the given enum value
        """
        match enum_value:
            case cls.jeeves:
                return JeevesWorkflow
            case cls.veritable:
                return VeritableWorkflow
            case cls.dexit:
                return DexitWorkflow
            case cls.penknife:
                return PenknifeWorkflow
            case cls.hdp:
                return HdpWorkflow
            case cls.zsegment:
                return ZSegmentWorkflow
            case cls.practifly:
                return PractiflyWorkflow
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")

    @classmethod
    def get_input_model_class(cls: "ProductEnum", enum_value: "ProductEnum") -> type:
        """
        Get the input model class for the given enum value
        """
        match enum_value:
            case cls.jeeves:
                return JeevesSpec
            case cls.veritable:
                return VeritableSpec
            case cls.dexit:
                return DexitSpec
            case cls.penknife:
                return PenknifeSpec
            case cls.hdp:
                return HDPSpec
            case cls.zsegment:
                return ZSegmentSpec
            case cls.practifly:
                return PractiflySpec
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")

    @classmethod
    def get_domain(cls: "ProductEnum", enum_value: "ProductEnum") -> str:
        """
        Get the domain for the given enum value
        """
        from ..core.settings import AppSettings, get_settings

        config: AppSettings = get_settings()
        match enum_value:
            case cls.jeeves:
                return config.jeeves.domain_name
            case cls.veritable:
                return config.veritable.domain_name
            case cls.dexit:
                return config.dexit.domain_name
            case cls.hdp:
                return config.hdp.domain_name
            case cls.zsegment:
                return config.zsegment.domain_name
            case cls.practifly:
                return config.practifly.domain_name
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")
