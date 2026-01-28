import os
import re
from enum import Enum
from functools import lru_cache
from typing import Any

from loguru import logger

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
from app.core.product_settings.common import SelfSignupSettings, Stripe
from app.models.add_ons.veritable import VeritableAddOn, VeritableFeature
from app.models.enums import AddOn, Feature

# Base directory for product templates
_TEMPLATES_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pattern for unquoted template variables like: <<varname | safe>> or <<varname | tojson>> - these break JSON
_UNQUOTED_TEMPLATE_VAR_PATTERN = re.compile(r"<<\w+\s*\|\s*(?:safe|tojson)>>")


def _substitute_template_variables(content: str) -> str:
    """
    Substitute template variables in keycloak_realm.json to make it valid JSON.

    - Unquoted variables like `<<customerClientRoles | safe>>` or `<<customerClientRoles | tojson>>`
      are replaced with `[]` (these are raw template expressions that would be replaced with arrays)
    - Quoted variables like `"<<tenant>>"` are left as-is since they're valid JSON strings
    """
    return _UNQUOTED_TEMPLATE_VAR_PATTERN.sub("[]", content)


@lru_cache(maxsize=16)
def _load_client_roles_from_template(product: "ProductEnum") -> list[str]:
    """
    Load client roles from the product's keycloak_realm.json template.
    Used for portal link lookup to filter out default/system roles.

    The template file contains <<placeholder>> syntax. Unquoted ones like
    `<<customerClientRoles | safe>>` break JSON parsing, so we substitute
    them with dummy values before parsing.
    """
    from app.core.ijson import ijson_loads
    from app.utils.file_operations import get_opendal_file_client

    product_name = product.value.lower()
    template_path = os.path.join(
        _TEMPLATES_BASE_DIR,
        "cli",
        "temporal",
        product_name,
        "templates",
        "keycloak_realm.json",
    )

    if not os.path.exists(template_path):
        logger.warning(f"Keycloak realm template not found: {template_path}")
        return []

    content = get_opendal_file_client().read_file_sync_str(template_path)

    # Substitute unquoted template variables to make valid JSON
    content = _substitute_template_variables(content)

    realm_config = ijson_loads(content)
    client_roles = realm_config.get("roles", {}).get("client", {})

    # Get roles for the product's client (client name = product name lowercase)
    product_client_roles = client_roles.get(product_name, [])
    return [role["name"] for role in product_client_roles if isinstance(role, dict) and "name" in role]


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
    def get_stripe_settings(cls: "ProductEnum", enum_value: "ProductEnum") -> Stripe:
        """
        return stripe secret key based on product
        """
        from ..core.settings import AppSettings, get_settings

        settings: AppSettings = get_settings()
        match enum_value:
            case cls.veritable:
                return settings.veritable.stripe
            case cls.pricedx:
                return settings.pricedx.stripe
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

    @classmethod
    def get_client_roles(cls: "ProductEnum", enum_value: "ProductEnum") -> list[str]:
        """
        Get the valid client roles for a product by reading from keycloak realm template.
        Used for portal link lookup to filter out default/system roles.
        """
        return _load_client_roles_from_template(enum_value)


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
