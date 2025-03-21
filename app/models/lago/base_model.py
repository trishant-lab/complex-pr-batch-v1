from typing import Any, Generic, TypeVar

from loguru import logger
from pydantic import BaseModel, ConfigDict, RootModel

T = TypeVar("T", bound="LagoBaseModel")


class LagoBaseModel(BaseModel):
    @classmethod
    def from_lago(cls: type[T], lago_model: Any) -> T:
        """Common conversion method for all Lago models"""
        try:
            return cls.model_validate(lago_model.dict())
        except Exception as e:
            logger.error(f"Failed to convert Lago model to {cls.__name__}: {e}")
            raise


class BaseResponseModel(LagoBaseModel):
    model_config = ConfigDict(frozen=True)


T2 = TypeVar("T2", BaseResponseModel, LagoBaseModel)


class BaseListResponseModel(LagoBaseModel, RootModel[list[T2]], Generic[T2]):
    model_config = ConfigDict(frozen=True)
    root: list[T2]

    def __iter__(self) -> Any:
        """Return an iterator over the root elements."""
        return super().__iter__()

    def __getitem__(self, item: int) -> T2:
        """Return the item at the specified index from the root list."""
        return self.root[item]
