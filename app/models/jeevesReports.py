from pydantic import BaseModel


class AssetsViewedResponseModel(BaseModel):
    total_assets_viewed: int
    assets_viewed_per_user: int | None


class AssetsDownloadResponseModel(BaseModel):
    total_assets_downloaded: int
    assets_downloaded_per_user: int | None


class AssetsSharedResponseModel(BaseModel):
    total_assets_shared: int
    assets_shared_per_user: int | None


class QueriesReportResponseModel(BaseModel):
    total_queries: int
    queries_per_user: int | None


class UserReportResponseModel(BaseModel):
    total_users: int
    session_per_user: int | None


class SessionReportResponseModel(BaseModel):
    total_sessions: int
    average_session_duration: str | None


class AssignmentsCreatedResponseModel(BaseModel):
    total_assignments_created: int
    assignments_per_user: int
