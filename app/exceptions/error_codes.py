# C - Common
# R - Route errors
# T - Task error

# 1000-Application Error
# 2000-Internal Service Error, self hosted (Postgres, Celery, Temporal, Minio, Redis, etc)
# 3000-External Service Error (Google Analytics, Google Search Console, Turnstile, Cloudflare, keycloak)
# 4000-Configuration Error, error in settings
# 5000-Authentication Authorization Error

from starlette import status

C1000 = {
    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "displayMessage": "Unexpected error encountered, ",
    "errorMessage": "",
    "followUpAction": [],
    "possibleResolutions": ["please contact support!"],
}

C1001 = {
    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "displayMessage": "Error deploying workflow {e}",
    "followUpAction": [],
    "possibleResolutions": ["Please retry deployment"],
}

C1002 = {
    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "displayMessage": "Error retrying provisioning {e}",
    "followUpAction": [],
    "possibleResolutions": ["Please retry provisioning"],
}

C1003 = {
    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "displayMessage": "Error fetching workflow history {e}",
    "followUpAction": [],
    "possibleResolutions": [],
}

C2001 = {
    "displayMessage": "Some Error Occurred while performing Database Action!",
    "followUpAction": [],
    "possibleResolutions": ["Possible resolution will be done. Support will contact you."],
}

C3001 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Some error occurred while send OTP!",
    "followUpAction": [],
    "possibleResolutions": ["Please check your email and try again!"],
}

C3002 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Some Error Occurred while sending Tenant Link!",
    "followUpAction": [],
    "possibleResolutions": ["Please check your email and try again!"],
}

C3003 = {
    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "displayMessage": "Error while Updating Role",
    "followUpAction": [],
    "possibleResolutions": [],
}

C3004 = {
    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "displayMessage": "Error while Adding Role",
    "followUpAction": [],
    "possibleResolutions": [],
}

C4002 = {
    "statusCode": status.HTTP_403_FORBIDDEN,
    "displayMessage": "Invalid Request!",
    "followUpAction": [],
    "possibleResolutions": ["Request not allowed"],
}

# Authentication authorization errors
C5001 = {
    "statusCode": status.HTTP_401_UNAUTHORIZED,
    "displayMessage": "Not authenticated!",
    "errorMessage": "",
    "followUpAction": [],
    "possibleResolutions": ["please login again or contact support!"],
}


C5003 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "",
    "errorMessage": "",
    "followUpAction": [],
    "possibleResolutions": ["please contact admin/support!"],
}

V5003 = {
    "statusCode": status.HTTP_403_FORBIDDEN,
    "displayMessage": "Please complete veritable onboarding",
}


R1001 = {
    "statusCode": status.HTTP_404_NOT_FOUND,
    "displayMessage": "Customer not found!",
    "followUpAction": [],
    "possibleResolutions": [
        "Please contact Support. Customer details provided do not exist.",
    ],
}

R1002 = {
    "statusCode": status.HTTP_404_NOT_FOUND,
    "displayMessage": "Tenant not found!",
    "followUpAction": [],
    "possibleResolutions": [
        "Please contact Support. Tenant ID provided does not exist.",
    ],
}

R1003 = {
    "statusCode": status.HTTP_404_NOT_FOUND,
    "displayMessage": "Product not found!",
    "followUpAction": [],
    "possibleResolutions": ["Please contact Support. Product provided does not exist."],
}

R1004 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Invalid value for fields,",
    "followUpAction": [],
    "possibleResolutions": ["Please correct the fields"],
}

R1005 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Invalid value for phone no.,",
    "followUpAction": [],
    "possibleResolutions": ["Please correct the fields"],
}

R1006 = {
    "statusCode": status.HTTP_403_FORBIDDEN,
    "displayMessage": "Requested plan resource not found!",
    "followUpAction": [],
    "possibleResolutions": ["Please request with correct plan code"],
}


R1007 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Payment details not found!",
    "followUpAction": [],
    "possibleResolutions": ["Please add card details before subscription."],
}


R1008 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Unsupported Operation,",
    "followUpAction": [],
    "possibleResolutions": ["Please refresh the page"],
}

R1009 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Max number of attempts reached,",
    "followUpAction": [],
    "possibleResolutions": ["Please generate a new OTP and try again."],
}

R1010 = {
    "statusCode": status.HTTP_409_CONFLICT,
    "displayMessage": "Tenant already in use!",
    "followUpAction": [],
    "possibleResolutions": ["Please retry with a different name"],
}


R1011 = {
    "statusCode": status.HTTP_401_UNAUTHORIZED,
    "displayMessage": "Invalid re-captcha received.",
    "followUpAction": [],
    "possibleResolutions": [
        "Please refresh the page, clear cookies or try in incognito mode.",
    ],
}

R1012 = {
    "statusCode": status.HTTP_403_FORBIDDEN,
    "displayMessage": "Plan does not exist or is no longer active!",
    "followUpAction": [],
    "possibleResolutions": ["Please select a valid plan!"],
}

R1013 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Invalid schema missing required fields mapping!",
    "followUpAction": [],
    "possibleResolutions": ["Please check the schema and try again."],
}

R1014 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Invalid email address!",
    "followUpAction": [],
    "possibleResolutions": ["Please provide a valid work email address."],
}

R1015 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Invalid OTP!",
    "followUpAction": [],
    "possibleResolutions": ["Re-enter correct OTP."],
}

R1016 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Invalid Coupon Code!",
    "followUpAction": [],
    "possibleResolutions": ["Please retry with a valid coupon code."],
}


R1017 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Explicit words not allowed!",
    "followUpAction": [],
    "possibleResolutions": ["Please retry with a different name"],
}


R1018 = {
    "statusCode": status.HTTP_400_BAD_REQUEST,
    "displayMessage": "Following required fields are missing: {fields}",
    "followUpAction": [],
    "possibleResolutions": ["Please fill all required fields"],
}
