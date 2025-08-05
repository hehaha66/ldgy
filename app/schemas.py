# 文件: app/schemas.py (最终版)

from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    verification_code: str
    username: Optional[str] = None

class UserInfo(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_superuser: bool
    plan: str
    expires_at: Optional[datetime.datetime] = None
    api_token: Optional[str] = None
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_info: UserInfo
class SendCodeRequest(BaseModel):
    email: EmailStr
class DevCodeResponse(BaseModel):
    message: str
    code: str
class UserStatusUpdate(BaseModel):
    is_active: bool
class UserAuthorizeUpdate(BaseModel):
    is_superuser: bool
class SubscriptionRequest(BaseModel):
    plan: str
    duration: str