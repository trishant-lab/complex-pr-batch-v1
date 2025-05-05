from enum import Enum
from typing import Any

from app.cli.temporal.dexit.dexit import DexitWorkflow
from app.cli.temporal.dexit.models.dexit_spec import DexitSpec
from app.cli.temporal.hdp.hdp import HdpWorkflow
from app.cli.temporal.hdp.models.hdp_spec import HDPSpec
from app.cli.temporal.jeeves.jeeves import JeevesWorkflow
from app.cli.temporal.jeeves.models.jeeves_spec import JeevesSpec

from app.cli.temporal.muspell.models.muspellSpec import MuspellArchiveSpec
from app.cli.temporal.muspell.muspell import MuspellArchiveWorkflow
from app.cli.temporal.penknife.models.penknife_spec import PenknifeSpec
from app.cli.temporal.penknife.penknife import PenknifeWorkflow
from app.cli.temporal.practifly.models.practifly_spec import PractiflySpec
from app.cli.temporal.practifly.practifly import PractiflyWorkflow
from app.cli.temporal.pricedx.models.pricedx_spec import PricedxSpec
from app.cli.temporal.pricedx.pricedx import PricedxWorkflow
from app.cli.temporal.veritable.models.veritable_spec import VeritableSpec
from app.cli.temporal.veritable.veritable import VeritableWorkflow
from app.cli.temporal.zsegment.models.zsegment_spec import ZSegmentSpec
from app.cli.temporal.zsegment.zsegment import ZSegmentWorkflow
from app.core.product_settings.common import SelfSignupSettings
from app.models.add_ons.veritable import VeritableAddOn, VeritableFeature
from app.models.enums import AddOn, Feature


class ProductEnum(str, Enum):
    jeeves = "Jeeves"
    veritable = "Veritable"
    dexit = "Dexit"
    penknife = "Penknife"
    hdp = "Hdp"
    zsegment = "Zsegment"
    practifly = "Practifly"
    pricedx = "Pricedx"
    muspell = "Muspell"

    @classmethod
    def _missing_(cls, value: object) -> "ProductEnum":
        """Handle case-insensitive lookup of enum values"""
        if not isinstance(value, str):
            raise TypeError(f"{value} is not of type str")

        normalized = value.title()
        for member in cls:
            if member.value == normalized:
                return member

        raise ValueError(f"{value} is not a valid {cls.__name__}")

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
            case cls.pricedx:
                return PricedxWorkflow
            case cls.muspell:
                return MuspellArchiveWorkflow
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
            case cls.pricedx:
                return PricedxSpec
            case cls.muspell:
                return MuspellArchiveSpec
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")

    @classmethod
    def get_product_settings(cls: "ProductEnum", enum_value: "ProductEnum") -> Any:
        """
        Get the product settings for the given enum value
        """
        from ..core.settings import AppSettings, get_settings

        settings: AppSettings = get_settings()

        match enum_value:
            case cls.veritable:
                return settings.veritable
            case cls.jeeves:
                return settings.jeeves
            case cls.dexit:
                return settings.dexit
            case cls.penknife:
                return settings.penknife
            case cls.hdp:
                return settings.hdp
            case cls.zsegment:
                return settings.zsegment
            case cls.practifly:
                return settings.practifly
            case cls.pricedx:
                return settings.pricedx
            case cls.muspell:
                return settings.muspell
            case _:
                raise ValueError(f"Product {enum_value} not found")

    @classmethod
    def get_onepassword_vault_name(cls: "ProductEnum", enum_value: "ProductEnum") -> str:
        """
        Get the onepassword vault name for the given enum value
        """
        match enum_value:
            case cls.veritable:
                return "Practifly"
            case cls.practifly:
                return "Practifly"
            case _:
                raise ValueError(f"Not Implemented for product: {enum_value.value}")

    @classmethod
    def get_domain(cls: "ProductEnum", enum_value: "ProductEnum") -> str:
        """
        Get the domain for the given enum value
        """
        return cls.get_product_settings(enum_value).domain_name

    @classmethod
    def get_stripe_secret_key(cls: "ProductEnum", enum_value: "ProductEnum") -> str:
        """
        return stripe secret key based on product
        """
        from ..core.settings import AppSettings, get_settings

        settings: AppSettings = get_settings()
        match enum_value:
            case cls.veritable:
                return settings.veritable.stripe.secret_key
            case cls.pricedx:
                return settings.pricedx.stripe.secret_key
            case _:
                raise ValueError(f"Not Implemented for product: {enum_value.value}")

    @classmethod
    def get_feature_enum(cls: "ProductEnum", enum_value: "ProductEnum") -> type[Feature]:
        """
        Get the feature enum for the given enum value
        """
        match enum_value:
            case cls.veritable:
                return VeritableFeature
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")

    @classmethod
    def get_add_on_enum(cls: "ProductEnum", enum_value: "ProductEnum") -> type[AddOn]:
        """
        Get the add on enum for the given enum value
        """
        match enum_value:
            case cls.veritable:
                return VeritableAddOn
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")

    @classmethod
    def get_self_signup_products(cls: "ProductEnum") -> list["ProductEnum"]:
        """
        Get the self signup products
        """
        return [cls.veritable, cls.pricedx]


def validate_self_signup_products() -> None:
    """
    Validate the self signup products
    """
    missing_settings: list[ProductEnum] = []
    for product in ProductEnum.get_self_signup_products():
        settings = ProductEnum.get_product_settings(product)
        if not isinstance(settings, SelfSignupSettings):
            missing_settings.append(product)

    if missing_settings:
        raise TypeError(f"Products missing SelfSignupSettings: {missing_settings}")
