from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.db import DBManager, get_db_manager
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings

reports_router = APIRouter()

RESULT_PER_USER = "int(sum(row['count_'] for row in {result}) / len({result}))"
SUM_RESULT = "sum(row['count_'] for row in {result})"
JEEVES_REPORTS_PER_USER_SQL = "jeevesReportsPerUser.sql"

REPORT_NAMES: dict = {
    "jeeves": {
        "assetsViewedSummary": {
            "query": "asset_viewed_per_user.sql",
            "response_model": {
                "total_assets_viewed": SUM_RESULT,
                "assets_viewed_per_user": RESULT_PER_USER,
            },
        },
        "assetsDownloadSummary": {
            "query": JEEVES_REPORTS_PER_USER_SQL,
            "input_params": {"event_category": "Assets", "event_action": "Download"},
            "response_model": {
                "total_assets_downloaded": SUM_RESULT,
                "assets_downloaded_per_user": RESULT_PER_USER,
            },
        },
        "assetsShared": {
            "query": JEEVES_REPORTS_PER_USER_SQL,
            "input_params": {"event_category": "Assets", "event_action": "Share"},
            "response_model": {
                "total_assets_shared": SUM_RESULT,
                "assets_shared_per_user": RESULT_PER_USER,
            },
        },
        "queriesSearched": {
            "query": "queries_per_user.sql",
            "response_model": {
                "total_searches": SUM_RESULT,
                "searches_per_user": RESULT_PER_USER,
            },
        },
        "users": {
            "query": "get_total_users.sql",
            "response_model": {
                "total_users": "'{result[0][total_users]}'",
                "users_per_session": "'{result[0][session_per_user]}'",
            },
        },
        "totalSessionsAndAvgDuration": {
            "query": "total_sessions_and_avg_duration.sql",
            "response_model": {
                "total_sessions": "'{result[0][total_sessions]}'",
                "avg_duration": "'{result[0][average_session_duration]}'",
            },
        },
        "assignmentsCreatedPerUser": {
            "query": "jeeves_reports_per_user.sql",
            "input_params": {"event_category": "Assignments", "event_action": "Create"},
            "response_model": {
                "total_assignments_created": SUM_RESULT,
                "assignments_per_user": RESULT_PER_USER,
            },
        },
        "assetUpload": {
            "query": JEEVES_REPORTS_PER_USER_SQL,
            "input_params": {"event_category": "Add Asset", "event_action": "Upload Video"},
            "response_model": {
                "total_assets_uploaded": SUM_RESULT,
                "assets_uploaded_per_user": RESULT_PER_USER,
            },
        },
        "assetRecord": {
            "query": JEEVES_REPORTS_PER_USER_SQL,
            "input_params": {"event_category": "Add Asset", "event_action": "Record Video"},
            "response_model": {
                "total_assets_recorded": SUM_RESULT,
                "assets_recorded_per_user": RESULT_PER_USER,
            },
        },
        "assetsTipSheetCreatedPerUser": {
            "query": "jeeves_tip_sheet_reports_per_user.sql",
            "response_model": {
                "total_assets_tip_sheet": SUM_RESULT,
                "tipsheet_created_per_user": RESULT_PER_USER,
            },
        },
    }
}


@reports_router.get("/getreportsNames", operation_id="getReportsNames")
async def get_reports_names(product_name: str) -> list[str]:
    """
    Get all the reports names for a given product
    """
    return list(REPORT_NAMES[product_name].keys())


@reports_router.get("/")
async def get_report_data(
    product_name: str,
    tenant: str,
    report_name: str,
    start_date: date | None = None,
    end_date: date | None = None,
    _params: dict = Depends(get_oauth_scheme()),
) -> dict:
    """
    Get the report data for a given report name
    """
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(dsn=config.postgres.dsn)

    report_details: dict = REPORT_NAMES[product_name][report_name]
    site_id: str = config.jeeves.reporting_site_id

    parameters = {
        "tenant": tenant,
        "site_id": site_id,
        "startdate": start_date.isoformat() if start_date else None,
        "enddate": end_date.isoformat() if end_date else None,
    }

    if "input_params" in report_details:
        parameters.update(report_details["input_params"])

    try:
        result = await db.fetch_all(
            report_details["query"],
            **parameters,
        )

        if not result:
            return {}

        response_model = {}
        result = [dict(row) for row in result]
        for key, value in report_details["response_model"].items():
            response_model[key] = eval(value.format(result=result))  # noqa: S307  # nosec

        return response_model
    except Exception as e:
        logger.error(f"Error while fetching report data : {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch report data. Please try again in sometime",
        ) from e
