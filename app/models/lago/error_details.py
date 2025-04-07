from typing import Any

from app.models.lago.base_model import BaseListResponseModel, LagoBaseModel


class ErrorDetailResponse(LagoBaseModel):
    organization_id: str
    error_code: str
    details: dict[str, Any] | None = None


class ErrorDetailsResponse(BaseListResponseModel[ErrorDetailResponse]):
    root: list[ErrorDetailResponse]
