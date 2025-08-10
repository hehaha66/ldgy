# 文件: app/schemas.py
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
    username: Optional[str] = None # 用户名在创建时可以是可选的
    email: EmailStr
    is_active: bool
    is_superuser: bool
    plan: str
    expires_at: Optional[datetime.datetime] = None
    api_token: Optional[str] = None
    nickname: Optional[str] = None # 将nickname添加到基础用户信息中，因为前端有用到

    class Config:
        from_attributes = True # Pydantic v2+ 使用 from_attributes 替代 orm_mode

# --- 【新增】用于前端展示的、包含完整权限的用户模型 ---
# UserOut 继承自 UserInfo，复用了所有基础字段
# 并在此基础上，添加了所有必需的权限字段。
class UserOut(UserInfo):
    min_interval: float
    max_codes: int
    max_connections: int
    api_access_level: str
    max_custom_indicators: int
    max_stock_groups: int
    max_alerts: int

# --- 【重要修改】更新Token模型，使其在登录时返回完整的用户信息 ---
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_info: UserOut # <-- 重要修改：从 UserInfo 改为 UserOut

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