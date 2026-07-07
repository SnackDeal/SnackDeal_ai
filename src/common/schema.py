from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class CommonResponse(BaseModel, Generic[T]):
    success: bool
    code: str
    message: str
    data: T | None = None

