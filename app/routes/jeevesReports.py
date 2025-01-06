from datetime import date

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from pydantic import TypeAdapter
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.db import DBManager, get_db_manager
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings
from app.models.jeevesReports import (
    AssetsViewedResponseModel,
    QueriesReportResponseModel,
    UserReportResponseModel,
    SessionReportResponseModel,
    AssetsDownloadResponseModel,
    AssignmentsCreatedResponseModel,
    AssetsSharedResponseModel,
    AssetsUploadResponseModel,
    AssetsRecordedResponseModel,
    AssetsTipSheetCreatedResponseModel,
)

JEEVES_REPORTS_PER_USER_SQL = "jeevesReportsPerUser.sql"

jeeves_report_router = APIRouter()


@jeeves_report_router.get(
    "/listTenants",
    response_model=list[str],
    operation_id="reportGetTenants",
    summary="Returns list of tenants",
)
async def list_tenants(_params: dict = Depends(get_oauth_scheme())) -> list[str]:
    """
    Returns list of tenants
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.jeeves.postgres.dsn)

    try:
        result: list = await db.fetch_all("getJeevesTenants.sql")
        return [row["tenant"] for row in result]
    except Exception as e:
        logger.error(f"Error while fetching tenants : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch tenants. Please try again in sometime",
        ) from e


@jeeves_report_router.get(
    "/assetsViewedSummary",
    response_model=AssetsViewedResponseModel | None,
    operation_id="reportGetAssetsViewedSummary",
    summary="Returns details of assets viewed",
)
async def assets_viewed_details(
    tenant: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> AssetsViewedResponseModel:
    """
    Return total assets viewed, number of users who viewed assets and assets viewed per user
    :param tenant: tenant name
    :param start_date: format YYYY-MM-DD
    :param end_date: format YYYY-MM-DD
    :param _params:
    :return:
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

    try:
        result: list = await db.fetch_all(
            "assetViewedPerUser.sql",
            tenant=tenant,
            site_id=config.jeeves.reporting_site_id,
            startdate=start_date.isoformat() if start_date else None,
            enddate=end_date.isoformat() if end_date else None,
        )

        total_views: int = sum(row["views"] for row in result)
        total_users: int = len(result)

        return AssetsViewedResponseModel(
            total_assets_viewed=total_views,
            assets_viewed_per_user=int(total_views / total_users) if total_users else 0,
        )
    except Exception as e:
        logger.error(f"Error while fetching view details for assets : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch assets views details. Please try again in sometime",
        ) from e


@jeeves_report_router.get(
    "/assetsDownloadSummary",
    response_model=AssetsDownloadResponseModel | None,
    operation_id="reportGetAssetsDownloadSummary",
    summary="Returns details of assets downloaded",
)
async def assets_download_details(
    tenant: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> AssetsDownloadResponseModel:
    """
    Return total assets download, number of users who downloaded assets and assets downloaded per user
    :param tenant: tenant name
    :param start_date: format YYYY-MM-DD
    :param end_date: format YYYY-MM-DD
    :param _params:
    :return:
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

    try:
        result: list = await db.fetch_all(
            JEEVES_REPORTS_PER_USER_SQL,
            tenant=tenant,
            site_id=config.jeeves.reporting_site_id,
            event_category="Assets",
            event_action="Download",
            startdate=start_date.isoformat() if start_date else None,
            enddate=end_date.isoformat() if end_date else None,
        )

        total_downloads: int = sum(row["count_"] for row in result)
        total_users: int = len(result)

        return AssetsDownloadResponseModel(
            total_assets_downloaded=total_downloads,
            assets_downloaded_per_user=int(total_downloads / total_users) if total_users else 0,
        )
    except Exception as e:
        logger.error(f"Error while fetching download details for assets : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch assets downloaded details. Please try again in sometime",
        ) from e


@jeeves_report_router.get(
    "/assetsShared",
    response_model=AssetsSharedResponseModel | None,
    operation_id="reportGetAssetsShared",
    summary="Returns details of assets shared",
)
async def assets_shared_details(
    tenant: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> AssetsSharedResponseModel:
    """
    Return total assets shared, number of users who shared assets and assets shared per user
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

    try:
        result: list = await db.fetch_all(
            JEEVES_REPORTS_PER_USER_SQL,
            tenant=tenant,
            event_category="Assets",
            event_action="Share",
            site_id=config.jeeves.reporting_site_id,
            startdate=start_date.isoformat() if start_date else None,
            enddate=end_date.isoformat() if end_date else None,
        )

        total_shared: int = sum(row["count_"] for row in result)
        total_users: int = len(result)

        return AssetsSharedResponseModel(
            total_assets_shared=total_shared,
            assets_shared_per_user=int(total_shared / total_users) if total_users else 0,
        )
    except Exception as e:
        logger.error(f"Error while fetching shared details for assets : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch assets shared details. Please try again in sometime",
        ) from e


@jeeves_report_router.get(
    "/query",
    response_model=QueriesReportResponseModel | None,
    operation_id="reportGetQuery",
    summary="Returns details of queries searched",
)
async def queries_details(
    tenant: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> QueriesReportResponseModel:
    """
    Return total searches, number of users who performed searches and searches per user
    :param start_date: format YYYY-MM-DD
    :param end_date: format YYYY-MM-DD
    :param tenant:
    :param _params:
    :return:
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

    try:
        result: list = await db.fetch_all(
            "queriesPerUser.sql",
            tenant=tenant,
            site_id=config.jeeves.reporting_site_id,
            startdate=start_date.isoformat() if start_date else None,
            enddate=end_date.isoformat() if end_date else None,
        )

        total_queries: int = sum(row["searches"] for row in result)
        total_users: int = len(result)

        return QueriesReportResponseModel(
            total_queries=total_queries,
            queries_per_user=int(total_queries / total_users) if total_users else 0,
        )
    except Exception as e:
        logger.error(f"Error while fetching queries details : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch queries details. Please try again in sometime",
        ) from e


@jeeves_report_router.get(
    "/user",
    response_model=UserReportResponseModel | None,
    operation_id="reportGetUser",
    summary="Returns details of users",
)
async def total_users_count(
    tenant: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> UserReportResponseModel:
    """
    Return total users and sessions per user count
    :param start_date: format YYYY-MM-DD
    :param end_date: format YYYY-MM-DD
    :param tenant:
    :param _params:
    :return:
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

    try:
        result = await db.fetch_one(
            "getTotalUsers.sql",
            tenant=tenant,
            site_id=config.jeeves.reporting_site_id,
            startdate=start_date.isoformat() if start_date else None,
            enddate=end_date.isoformat() if end_date else None,
        )
        return TypeAdapter(UserReportResponseModel).validate_python(dict(result))
    except Exception as e:
        logger.error(f"Error while fetching total users count : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch total users count. Please try again in sometime",
        ) from e


@jeeves_report_router.get(
    "/session",
    response_model=SessionReportResponseModel | None,
    operation_id="reportGetSession",
    summary="Returns details of session",
)
async def session_duration_details(
    tenant: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> SessionReportResponseModel:
    """
    Return total sessions number and their average duration
    :param start_date: format YYYY-MM-DD
    :param end_date: format YYYY-MM-DD
    :param tenant:
    :param _params:
    :return:
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)
    try:
        result = await db.fetch_one(
            "totalSessionsAndAvgDuration.sql",
            tenant=tenant,
            site_id=config.jeeves.reporting_site_id,
            startdate=start_date.isoformat() if start_date else None,
            enddate=end_date.isoformat() if end_date else None,
        )
        return TypeAdapter(SessionReportResponseModel).validate_python(dict(result))
    except Exception as e:
        logger.error(f"Error while fetching session duration details : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch session duration details. Please try again in sometime",
        ) from e


@jeeves_report_router.get(
    "/AssignmentsCreated",
    operation_id="reportGetAssignmentsCreated",
    summary="Returns details of assignments created",
    response_model=AssignmentsCreatedResponseModel | None,
)
async def assignments_created_details(
    tenant: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> AssignmentsCreatedResponseModel:
    """
    Return total assignments created number and their average duration
    :param start_date: format YYYY-MM-DD
    :param end_date: format YYYY-MM-DD
    :param tenant:
    :param _params:
    :return:
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)
    try:
        result = await db.fetch_all(
            JEEVES_REPORTS_PER_USER_SQL,
            tenant=tenant,
            site_id=config.jeeves.reporting_site_id,
            event_category="Assignments",
            event_action="Create",
            startdate=start_date.isoformat() if start_date else None,
            enddate=end_date.isoformat() if end_date else None,
        )
        total_assignments_created: int = sum(row["count_"] for row in result)
        total_users: int = len(result)

        return AssignmentsCreatedResponseModel(
            total_assignments_created=total_assignments_created,
            assignments_per_user=int(total_assignments_created / total_users) if total_users else 0,
        )
    except Exception as e:
        logger.error(f"Error while fetching assignments created details : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch assignments created details. Please try again in sometime",
        ) from e


@jeeves_report_router.get(
    "/AssetUpload",
    operation_id="reportAssetUpload",
    summary="Returns details of uploaded assets",
    response_model=AssetsUploadResponseModel | None,
)
async def asset_upload_details(
    tenant: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> AssetsUploadResponseModel:
    """
    Return total assets uploaded number and their average duration
    :param start_date: format YYYY-MM-DD
    :param end_date: format YYYY-MM-DD
    :param tenant:
    :param _params:
    :return:
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)
    try:
        result = await db.fetch_all(
            JEEVES_REPORTS_PER_USER_SQL,
            tenant=tenant,
            site_id=config.jeeves.reporting_site_id,
            event_category="Add Asset",
            event_action="Upload Video",
            startdate=start_date.isoformat() if start_date else None,
            enddate=end_date.isoformat() if end_date else None,
        )
        total_assets_uploaded: int = sum(row["count_"] for row in result)
        total_users: int = len(result)

        return AssetsUploadResponseModel(
            total_assets_uploaded=total_assets_uploaded,
            assets_uploaded_per_user=int(total_assets_uploaded / total_users) if total_users else 0,
        )
    except Exception as e:
        logger.error(f"Error while fetching asset upload details : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch asset upload details. Please try again in sometime",
        ) from e


@jeeves_report_router.get(
    "/AssetRecord",
    operation_id="reportAssetRecord",
    summary="Returns details of recorded assets",
    response_model=AssetsRecordedResponseModel | None,
)
async def asset_record_details(
    tenant: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> AssetsRecordedResponseModel:
    """
    Return total assets recorded number and their average duration
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)
    try:
        result = await db.fetch_all(
            JEEVES_REPORTS_PER_USER_SQL,
            tenant=tenant,
            site_id=config.jeeves.reporting_site_id,
            event_category="Add Asset",
            event_action="Record Video",
            startdate=start_date.isoformat() if start_date else None,
            enddate=end_date.isoformat() if end_date else None,
        )
        total_assets_recorded: int = sum(row["count_"] for row in result)
        total_users: int = len(result)

        return AssetsRecordedResponseModel(
            total_assets_recorded=total_assets_recorded,
            assets_recorded_per_user=int(total_assets_recorded / total_users) if total_users else 0,
        )
    except Exception as e:
        logger.error(f"Error while fetching asset record details : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch asset record details. Please try again in sometime",
        ) from e


@jeeves_report_router.get(
    "/AssetTipSheet",
    operation_id="reportAssetTipSheet",
    summary="Returns details of the Tip Sheet",
    response_model=AssetsTipSheetCreatedResponseModel | None,
)
async def asset_tip_sheet_details(
    tenant: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> AssetsTipSheetCreatedResponseModel:
    """
    Return total assets tip sheet number and their average duration
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)
    try:
        result = await db.fetch_all(
            "jeevesTipSheetReportsPerUser.sql",
            tenant=tenant,
            site_id=config.jeeves.reporting_site_id,
            startdate=start_date.isoformat() if start_date else None,
            enddate=end_date.isoformat() if end_date else None,
        )
        total_assets_tip_sheet: int = sum(row["count_"] for row in result)
        total_users: int = len(result)

        return AssetsTipSheetCreatedResponseModel(
            total_tipsheet_created=total_assets_tip_sheet,
            tipsheet_created_per_user=int(total_assets_tip_sheet / total_users) if total_users else 0,
        )
    except Exception as e:
        logger.error(f"Error while fetching asset tip sheet details : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch asset tip sheet details. Please try again in sometime",
        ) from e
