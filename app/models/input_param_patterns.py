"""
Input param patterns
"""

TENANT_NAME_PATTERN = r"^[a-z][a-z0-9]{2,14}$"  # start with alphabet, lower alphabet & numbers, len 3 to 15
TOKEN_PATTERN = r"^[a-zA-Z0-9]{30,100}$"  # upper and lower case alphabets, numbers, len 30 to 100
