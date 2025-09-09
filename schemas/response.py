from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar('T')


class ResponseSchema(BaseModel, Generic[T]):
    status: int
    message: str
    data: Optional[T] = None
    success: bool

    # 工厂方法：成功响应
    @classmethod
    def ok(cls, message: str, data: Optional[T] = None) -> "ResponseSchema[T]":
        return cls(status=200, message=message, data=data, success=True)

    # 工厂方法：失败响应
    @classmethod
    def fail(cls, message: str, status: int = 400, data: Optional[T] = None) -> "ResponseSchema[T]":
        return cls(status=status, message=message, data=data, success=False)
