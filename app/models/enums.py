from enum import Enum, IntEnum


class PlanStatus(IntEnum):
    Inactive = -1
    legacy = 0
    active = 1
    enterprise = 2


class MarketingType(IntEnum):
    normal = 0
    popular = 1
    recommended = 2


class Feature(str, Enum):
    default = "default"
    payments = "a_payments"


class AddOn(str, Enum):
    payments = "a_payments"


class FeatureStatus(IntEnum):
    inactive = -1
    legacy = 0
    active = 1
