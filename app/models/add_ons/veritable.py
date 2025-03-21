from app.models.enums import AddOn, Feature


class VeritableFeature(Feature):
    default = "default"
    payments = "a_payments"


class VeritableAddOn(AddOn):
    payments = "a_payments"
