from pydantic import BaseModel, RootModel

from app.models.lago.base_model import BaseResponseModel


class UsageThreshold(BaseModel):
    id: str | None
    threshold_display_name: str | None
    amount_cents: int | None
    recurring: bool | None


class UsageThresholds(RootModel):
    root: list[UsageThreshold]


class UsageThresholdResponse(BaseResponseModel):
    lago_id: str
    amount_cents: int
    threshold_display_name: str | None = None
    recurring: bool
    created_at: str | None = None
    updated_at: str | None = None


class UsageThresholdsResponse(RootModel):
    root: list[UsageThresholdResponse]


class UsageThresholdOverrides(BaseModel):
    amount_cents: int | None
    threshold_display_name: str | None
    recurring: bool | None


class UsageThresholdsOverrides(RootModel):
    root: list[UsageThresholdOverrides]
