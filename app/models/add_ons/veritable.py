from app.models.enums import AddOn, Feature


class VeritableFeature(Feature):
    default = "default"
    payments = "a_payments"
    insurance_discovery = "insurance_discovery"
    mbi_lookup = "mbi_lookup"


class VeritableAddOn(AddOn):
    payments = "a_payments"
