from enum import IntEnum


class PlanStatus(IntEnum):
    Inactive = -1
    legacy = 0
    active = 1
    enterprise = 2


class MarketingType(IntEnum):
    normal = 0
    popular = 1
    recommended = 2


class FeatureStatus(IntEnum):
    inactive = -1
    legacy = 0
    active = 1
