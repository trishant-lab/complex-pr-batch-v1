from pydantic import BaseModel, RootModel


class TaxResponse(BaseModel):
    lago_id: str
    name: str
    code: str
    rate: float
    description: str | None = None
    add_ons_count: int | None = None
    customers_count: int | None = None
    plans_count: int | None = None
    charges_count: int | None = None
    applied_to_organization: bool
    created_at: str


class TaxesResponse(RootModel):
    root: list[TaxResponse]
