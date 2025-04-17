import traceback

from asyncpg.exceptions import ForeignKeyViolationError, PostgresError, UniqueViolationError
from loguru import logger
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from app.exceptions.error_code_mapper import LaunchpadHTTPException, ServerErrorModel


async def launchpad_http_exception_handler(_request: Request, exc: LaunchpadHTTPException) -> JSONResponse:
    """
    Exception Handler function for all the HTTPExceptions
    raised within the application code
    """
    content: dict = {"detail": exc.detail}
    print(traceback.format_exc())
    return JSONResponse(content=content, status_code=exc.status_code, headers=exc.headers)


async def postgres_exception_handler(_request: Request, exc: PostgresError) -> JSONResponse:
    """
    Exception Handler function for all the Database
    based errors
    """
    db_error: ServerErrorModel = ServerErrorModel.initialize("C2001")
    db_error.status_code = HTTP_400_BAD_REQUEST
    if isinstance(exc, UniqueViolationError | ForeignKeyViolationError):
        db_error.status_code = HTTP_409_CONFLICT
    print(traceback.format_exc())
    db_error.error_message = f"{exc!r}"
    logger.error(
        db_error.error_message,
        status_code=db_error.status_code,
        error_code=db_error.code,
    )
    detail = db_error.model_dump(by_alias=True, exclude={"status_code", "error_message"})
    return JSONResponse(content={"detail": detail}, status_code=db_error.status_code)


async def generic_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """
    Exception Handler to Encounter any unexpected error
    """
    unexpected_error = ServerErrorModel.initialize("C1000")
    print(traceback.format_exc())
    unexpected_error.error_message += (
        f"exception={_exc!r},  status_code={unexpected_error.status_code},  error_code={unexpected_error.code} "
        f"product='launchpad',  api_path={_request.url.path}"
    )
    ServerErrorModel.log(unexpected_error.status_code)(unexpected_error.error_message)
    detail = unexpected_error.model_dump(by_alias=True, exclude={"status_code", "error_message"})
    return JSONResponse(content={"detail": detail}, status_code=unexpected_error.status_code)
