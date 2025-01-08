from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RoleResponseModel(BaseModel):
    """
    Data Model for roles list response
    """

    id: UUID = Field(description="Unique id")
    name: str = Field(description="Name of role")

    @classmethod
    def json_to_model(cls: "RoleResponseModel", data: dict) -> "RoleResponseModel":
        """
        Parse dict
        """
        return cls.parse_obj(data)


class UserResponseModel(BaseModel):
    id: UUID = Field(description="Unique id")
    username: str = Field(description="Username")
    email: EmailStr = Field(description="User Email")
    firstName: str = Field(description="First Name of User")
    lastName: str = Field(description="Last Name of User")
    roles: None | list[RoleResponseModel] = Field(None, description="User roles")
    status: bool = Field(description="User status")
    created: datetime = Field(description="Initial creation time")

    @classmethod
    def json_to_model(cls: "UserResponseModel", data: dict) -> "UserResponseModel":
        """
        Parse dict
        """
        data["created"] = data["createdTimestamp"]
        data["status"] = data["enabled"]
        return cls.parse_obj(data)


class CreateUserRequestModel(BaseModel):
    email: str
    username: str
    first_name: str | None = None
    last_name: str | None = None
    roles: list[RoleResponseModel] | None = None
    status: bool = True


class UpdateUserRequestModel(BaseModel):
    user_id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    added_roles: list[RoleResponseModel] | None = None
    deleted_roles: list[RoleResponseModel] | None = None
    status: bool = True


class GSuiteUser(BaseModel):
    class Name(BaseModel):
        givenName: str | None = None
        familyName: str | None = None
        fullName: str | None = None

    id: float
    primaryEmail: str
    name: Name | None = None
    aliases: list[str] | None = None
