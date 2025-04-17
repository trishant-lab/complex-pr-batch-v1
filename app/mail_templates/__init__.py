"""
mail templates here
"""

from .main import (
    internal_payment_failure_mail,
    kube_config_expiry_mail,
    otp_verification_mail,
    payment_failure_mail,
    periodic_invoice_mail,
    provisioning_failure_mail,
    provisioning_success_mail,
    sign_in_detected,
)

__all__ = [
    "internal_payment_failure_mail",
    "kube_config_expiry_mail",
    "otp_verification_mail",
    "payment_failure_mail",
    "periodic_invoice_mail",
    "provisioning_failure_mail",
    "provisioning_success_mail",
    "sign_in_detected",
]
