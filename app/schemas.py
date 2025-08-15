# 文件: app/schemas.py

from pydantic import BaseModel, EmailStr
from typing import Optional, List
import datetime

# ==================================
#   您原有的、已验证正确的模型
# ==================================
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    verification_code: str
    username: Optional[str] = None

class UserInfo(BaseModel):
    id: int
    username: Optional[str] = None
    email: EmailStr
    is_active: bool
    is_superuser: bool
    plan: str
    expires_at: Optional[datetime.datetime] = None
    api_token: Optional[str] = None
    nickname: Optional[str] = None

    class Config:
        from_attributes = True

class UserOut(UserInfo):
    min_interval: float
    max_codes: int
    max_connections: int
    api_access_level: str
    max_custom_indicators: int
    max_stock_groups: int
    max_alerts: int

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_info: UserOut

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

# 文件: app/schemas.py (在末尾修正并替换)

# ==========================================================
#   为“王牌功能” (Workspace) 准备的Pydantic模型
# ==========================================================

# --- WorkspaceEntity ---
# 【核心修正】确保这个创建模型存在
class WorkspaceEntityCreate(BaseModel):
    entity_type: str
    name: str
    definition: dict # 使用 dict 替代 Dict[str, Any] 更简洁

# 这个模型用于API返回单个实体的信息
class WorkspaceEntityOut(BaseModel):
    id: int
    entity_type: str
    name: str
    definition: dict
    display_order: int

    class Config:
        from_attributes = True

# --- MonitorWorkspace ---
# 创建工作区时，前端只需要提供一个名字
class MonitorWorkspaceCreate(BaseModel):
    name: str

# 从API返回工作区信息时，我们希望包含其内部的所有实体
class MonitorWorkspaceOut(BaseModel):
    id: int
    name: str
    is_active: bool
    entities: List[WorkspaceEntityOut] = []

    class Config:
        from_attributes = True