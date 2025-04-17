from app.cli.temporal.core.exceptions import RetryableException


class InvoiceNotGeneratedException(RetryableException):
    pass


class InvoiceStatusPendingException(RetryableException):
    pass


class InvalidOnboardStatusException(RetryableException):
    pass
