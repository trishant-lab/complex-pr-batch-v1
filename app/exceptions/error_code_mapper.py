from collections.abc import Callable
from copy import copy
from functools import lru_cache

from fastapi.exceptions import HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from app.exceptions import error_codes


class LaunchpadHTTPException(HTTPException):
    """
    Launchpad custom HTTPException class
    """

    def __init__(
        self: "LaunchpadHTTPException",
        status_code: int,
        detail: dict,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)


class ServerErrorModel(BaseModel):
    code: str = "C1000"
    status_code: int = Field(500, alias="statusCode")
    display_message: str = Field("", alias="displayMessage")
    error_message: str = Field("", alias="errorMessage")
    follow_up_action: list[str] = Field([], alias="followUpAction")
    possible_resolutions: list[str] = Field([], alias="possibleResolutions")

    @classmethod
    def initialize(cls: type["ServerErrorModel"], code: str) -> "ServerErrorModel":
        """
        Initialize error for code
        """
        code = code if hasattr(error_codes, code) else "C1000"
        return cls(**getattr(error_codes, code), code=code)

    @staticmethod
    @lru_cache
    def log(status_code: int) -> Callable:
        """
        returns log level on the basis of status code
        """
        if status_code >= 500:
            return logger.error
        if 500 > status_code >= 400:
            return logger.warning
        return logger.info

    def exc(self: "ServerErrorModel", **params: object) -> LaunchpadHTTPException:
        """
        get exception from params
        """
        disp_message, err_message = copy(self.display_message), copy(self.error_message)
        disp_message = disp_message.format(**params)
        err_message = params.get("error_message", self.error_message)
        err_message = err_message.format(**params) if err_message else disp_message
        self.status_code = params.get("statusCode", self.status_code)
        self.possible_resolutions = params.get("possibleResolutions", self.possible_resolutions)
        self.log(self.status_code)(err_message)
        detail = self.model_dump(by_alias=True, exclude={"status_code"})
        detail["displayMessage"] = disp_message
        detail["errorMessage"] = err_message
        return LaunchpadHTTPException(self.status_code, detail)
