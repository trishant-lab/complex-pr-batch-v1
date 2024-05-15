from typing import List, Dict
from uuid import UUID

from pydantic import BaseModel


class VeritableResourceModel(BaseModel):
    request_cpu: str = "500m"
    request_memory: str = "500Mi"
    limit_cpu: str = "3000m"
    limit_memory: str = "3000Mi"


class CustomerDetails(BaseModel):
    customerId: UUID
    customerUserName: str
    customerEmail: str
    customerRealmRoles: List[str] = ["VT_CUSTOMER_ADMIN"]
    orgName: str


class VeritableSchema(BaseModel):
    tenant: str
    imageTag: str
    customerDetails: None | CustomerDetails = None
    serverSpec: VeritableResourceModel = VeritableResourceModel()
    cliSpec: VeritableResourceModel = VeritableResourceModel()
