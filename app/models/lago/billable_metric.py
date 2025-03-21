from app.models.lago.base_model import BaseListResponseModel, BaseResponseModel, LagoBaseModel


class BillableMetricFilter(LagoBaseModel):
    key: str | None
    values: list[str] | None


class BillableMetricFilters(BaseListResponseModel[BillableMetricFilter]):
    root: list[BillableMetricFilter]


class BillableMetricResponse(BaseResponseModel):
    lago_id: str
    name: str
    code: str
    description: str | None
    recurring: bool | None
    rounding_function: str | None
    rounding_precision: int | None
    aggregation_type: str | None
    weighted_interval: str | None
    expression: str | None
    field_name: str | None
    created_at: str
    filters: BillableMetricFilters
