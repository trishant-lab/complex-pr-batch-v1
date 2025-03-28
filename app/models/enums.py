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


class FeatureStatus(IntEnum):
    inactive = -1
    legacy = 0
    active = 1


class OnboardingStatus(str, Enum):
    IN_PROGRESS = "InProgress"
    PROVISIONED = "Provisioned"


class PaymentStatus(str, Enum):
    succeeded = "succeeded"
    pending = "pending"
    failed = "failed"


class SubscriptionType(str, Enum):
    initial = "initial"
    renewal = "renewal"
    upgrade = "upgrade"
    downgrade = "downgrade"


class AddOn(str, Enum):
    pass


class Feature(str, Enum):
    pass


class Provider(str, Enum):
    STRIPE = "stripe"


class BillingTime(str, Enum):
    ANNIVERSARY = "anniversary"
    CALENDAR = "calendar"


class EmailTemplateName(str, Enum):
    before_provisioning = "beforeprovisioning"
    after_provisioning = "afterprovisioning"
