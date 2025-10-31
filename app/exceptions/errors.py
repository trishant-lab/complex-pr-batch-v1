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
PLAN_INACTIVE_ERROR: ServerErrorModel = ServerErrorModel.initialize("R1012")

# subscription
PAYMENT_METHOD_NOT_ADDED: ServerErrorModel = ServerErrorModel.initialize("R1007")

# verification
INVALID_OPERATION: ServerErrorModel = ServerErrorModel.initialize(code="R1008")
INVALID_EMAIL: ServerErrorModel = ServerErrorModel.initialize(code="R1014")
INVALID_OTP: ServerErrorModel = ServerErrorModel.initialize(code="R1015")
OTP_RETRY: ServerErrorModel = ServerErrorModel.initialize(code="R1009")
ALREADY_ALLOCATED_TENANT_NAME: ServerErrorModel = ServerErrorModel.initialize(
    code="R1010",
)
EXPLICIT_WORDS_NOT_ALLOWED: ServerErrorModel = ServerErrorModel.initialize(code="R1017")
RECAPTCHA_FAILED: ServerErrorModel = ServerErrorModel.initialize(code="R1011")

# provisioning
INVALID_SCHEMA: ServerErrorModel = ServerErrorModel.initialize(code="R1013")
REQUIRED_FIELD_MISSING: ServerErrorModel = ServerErrorModel.initialize(code="R1018")
SELF_SIGNUP_PRODUCT_PROVISIONING_NOT_ALLOWED: ServerErrorModel = ServerErrorModel.initialize(code="R1020")

# product
PRODUCT_NOT_FOUND: ServerErrorModel = ServerErrorModel.initialize(code="R1003")

# tenant
TENANT_NOT_FOUND: ServerErrorModel = ServerErrorModel.initialize(code="R1002")
TENANT_DETAILS_CANNOT_BE_UPDATED: ServerErrorModel = ServerErrorModel.initialize(code="R1019")

# coupon
INVALID_COUPON_CODE: ServerErrorModel = ServerErrorModel.initialize(code="R1016")


# tenant_link
TENANT_LINK_NOT_SENT: ServerErrorModel = ServerErrorModel.initialize(code="C3002")

# space
SPACE_ALREADY_EXISTS: ServerErrorModel = ServerErrorModel.initialize(code="R1021")
SPACE_NOT_FOUND: ServerErrorModel = ServerErrorModel.initialize(code="R1022")
