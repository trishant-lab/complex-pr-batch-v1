"""
Jeeves
"""

from os import path

TemplatePath = path.abspath(path.join(path.dirname(__file__), "templates"))

ProductName = "jeeves"
OnePasswordVaultName = "Jeeves"
JeevesSystemUser = "jeeves-systemuser@314ecorp.com"

JEEVES_CLIENT_ROLES: list[str] = [
    "_access-broadcast",
    "_access-assignment",
    "_access-analytics",
    "_access-setting",
    "_allow-add-edit-asset",
    "_allow-delete-asset",
    "_allow-publish-asset",
    "_allow-review-asset",
    "_allow-standalone-launch",
    "_allow-view-asset",
    "_access-user-list",
    "_can-manage-user",
    "_developer",
    "_JEEVESALL",
]

# Internal users for production
JEEVES_PRODUCTION_INTERNAL_USERS: list[dict] = [
    {
        "username": "casey.post@314ecorp.com",
        "email": "casey.post@314ecorp.com",
        "firstname": "Casey",
        "lastname": "Post",
    },
    {
        "username": "nick.dejongh@314ecorp.com",
        "email": "nick.dejongh@314ecorp.com",
        "firstname": "Nick",
        "lastname": "DeJongh",
    },
    {
        "username": "ankush.govil@314ecorp.com",
        "email": "ankush.govil@314ecorp.com",
        "firstname": "Ankush",
        "lastname": "Govil",
        "roles": ["_JEEVESALL"],
    },
    {
        "username": JeevesSystemUser,
        "email": JeevesSystemUser,
        "firstname": "System",
        "lastname": "User",
    },
    {
        "username": "julie.menefee@314ecorp.com",
        "email": "julie.menefee@314ecorp.com",
        "firstname": "Julie",
        "lastname": "Menefee",
    },
    {
        "username": "sumanth.sm@314ecorp.com",
        "email": "sumanth.sm@314ecorp.com",
        "firstname": "Sumanth",
        "lastname": "S M",
        "roles": ["_JEEVESALL"],
    },
]

# Internal users for non-production (integration/test)
JEEVES_NON_PRODUCTION_INTERNAL_USERS: list[dict] = [
    {
        "username": JeevesSystemUser,
        "email": JeevesSystemUser,
        "firstname": "System",
        "lastname": "User",
    },
    {
        "username": "sumanth.sm@314ecorp.com",
        "email": "sumanth.sm@314ecorp.com",
        "firstname": "Sumanth",
        "lastname": "S M",
        "roles": ["_JEEVESALL"],
    },
    {
        "username": "soumya.ramesh@314ecorp.com",
        "email": "soumya.ramesh@314ecorp.com",
        "firstname": "Soumya",
        "lastname": "Ramesh",
        "roles": ["_JEEVESALL"],
    },
]
