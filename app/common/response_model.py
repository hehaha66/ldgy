from typing import Generic, TypeVar, Optional
from pydantic import BaseModel
from fastapi import HTTPException

T = TypeVar('T')

class ResponseModel(BaseModel, Generic[T]):
    code: int = 200
    msg: str = "success"
    data: Optional[T] = None

class APIException(HTTPException):
    def __init__(self, code: int, msg: str, headers: Optional[dict] = None):
        self.code = code
        self.msg = msg
        super().__init__(status_code=code, detail=msg, headers=headers)