from app.exceptions import ServerErrorModel

# common
DEPLOYMENT_ERROR: ServerErrorModel = ServerErrorModel.initialize("C1001")
RETRY_PROVISIONING_ERROR: ServerErrorModel = ServerErrorModel.initialize("C1002")
WORKFLOW_HISTORY_FETCH_ERROR: ServerErrorModel = ServerErrorModel.initialize("C1003")
UPDATE_ROLE_ERROR: ServerErrorModel = ServerErrorModel.initialize("C3003")
ADD_ROLE_ERROR: ServerErrorModel = ServerErrorModel.initialize("C3004")

# core/settings
OTP_NOT_SENT: ServerErrorModel = ServerErrorModel.initialize("C3001")
INVALID_REQUEST: ServerErrorModel = ServerErrorModel.initialize("C4002")

# core/auth
NOT_AUTHENTICATED = ServerErrorModel.initialize("C5001")

# ROUTES
# customer
CUSTOMER_NOT_FOUND: ServerErrorModel = ServerErrorModel.initialize("R1001")
INVALID_VALUES: ServerErrorModel = ServerErrorModel.initialize("R1004")
INVALID_PHONE_NUMBER: ServerErrorModel = ServerErrorModel.initialize("R1005")

# plans
PLAN_RESOURCE_NOT_FOUND: ServerErrorModel = ServerErrorModel.initialize("R1006")
PLAN_INACTIVE_ERROR: ServerErrorModel = ServerErrorModel.initialize("R1018")

# subscription
PAYMENT_METHOD_NOT_ADDED: ServerErrorModel = ServerErrorModel.initialize("R1008")

# verification
INVALID_OPERATION: ServerErrorModel = ServerErrorModel.initialize(code="R1012")
INVALID_EMAIL: ServerErrorModel = ServerErrorModel.initialize(code="R1020")
INVALID_OTP: ServerErrorModel = ServerErrorModel.initialize(code="R1021")
OTP_RETRY: ServerErrorModel = ServerErrorModel.initialize(code="R1013")
ALREADY_ALLOCATED_TENANT_NAME: ServerErrorModel = ServerErrorModel.initialize(
    code="R1014",
)
EXPLICIT_WORDS_NOT_ALLOWED: ServerErrorModel = ServerErrorModel.initialize(code="R1025")
RECAPTCHA_FAILED: ServerErrorModel = ServerErrorModel.initialize(code="R1017")

# provisioning
INVALID_SCHEMA: ServerErrorModel = ServerErrorModel.initialize(code="R1019")

# product
PRODUCT_NOT_FOUND: ServerErrorModel = ServerErrorModel.initialize(code="R1003")

# tenant
TENANT_NOT_FOUND: ServerErrorModel = ServerErrorModel.initialize(code="R1002")

# coupon
INVALID_COUPON_CODE: ServerErrorModel = ServerErrorModel.initialize(code="R1022")


# tenant_link
TENANT_LINK_NOT_SENT: ServerErrorModel = ServerErrorModel.initialize(code="C3002")
