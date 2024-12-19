from enum import Enum


class VeritableFeature(str, Enum):
    default = "default"
    payments = "a_payments"


class VeritableAddOn(str, Enum):
    payments = "a_payments"
