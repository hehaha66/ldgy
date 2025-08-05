# 文件: app/common/dependencies.py

from fastapi import Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import datetime
import os

from ..database import get_db
from .. import models, crud, plans
from .response_model import APIException

# --- 配置 ---
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_if_not_in_env")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 *7))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


# --- Token 创建 & 解码 ---
def create_token(data: dict, expires_delta: datetime.timedelta):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict):
    return create_token(data, datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(data: dict):
    return create_token(data, datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ==========================================================
#                  Web App JWT 认证
# ==========================================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def get_current_user_from_jwt(token: Optional[str] = Depends(oauth2_scheme),
                              db: Session = Depends(get_db)) -> models.User:
    """依赖项：通过 JWT (Bearer Token) 获取用户，这是Web App认证的基础。"""
    if token is None:
        raise APIException(code=status.HTTP_401_UNAUTHORIZED, msg="Authorization token is missing")

    payload = decode_token(token)
    if payload is None:
        raise APIException(code=status.HTTP_401_UNAUTHORIZED, msg="Invalid or expired token")

    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise APIException(code=status.HTTP_401_UNAUTHORIZED, msg="Invalid token payload")

    user = crud.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="User not found")

    return user


# ==========================================================
#                   SaaS 静态 Token 认证
# ==========================================================
def get_user_by_api_token(
        token: Optional[str] = Query(None, description="用户的静态 API Token"),
        db: Session = Depends(get_db)
) -> models.User:
    """依赖项：通过静态 API Token (URL查询参数) 获取用户，用于SaaS服务。"""
    if token is None:
        raise APIException(code=status.HTTP_401_UNAUTHORIZED, msg="API Token is missing in query parameters.")
    user = crud.get_user_by_api_token(db, api_token=token)
    if user is None:
        raise APIException(code=status.HTTP_401_UNAUTHORIZED, msg="Invalid API Token.")
    return user


# ==========================================================
#                   权限检查依赖
# ==========================================================
def get_current_active_user(current_user: models.User = Depends(get_current_user_from_jwt)) -> models.User:
    """依赖项：确保通过 JWT 登录的用户是激活状态并应用套餐限制。"""
    if not current_user.is_active:
        raise APIException(code=status.HTTP_403_FORBIDDEN, msg="Inactive user")
    return plans.apply_plan_limits(current_user)


def get_current_active_superuser(current_user: models.User = Depends(get_current_active_user)) -> models.User:
    """依赖项：确保通过 JWT 登录的用户是超级管理员。"""
    if not current_user.is_superuser:
        raise APIException(code=status.HTTP_403_FORBIDDEN, msg="Admin privileges required")
    return current_user


# --- 混合认证模式 (用于 Monitor, AI 等接口) ---
def get_user_from_header_or_query(
        request: Request,
        db: Session = Depends(get_db)
) -> models.User:
    """
    一个灵活的依赖，自动检测使用 JWT 还是静态 Token 进行认证。
    优先检查 Authorization Header (JWT)，如果不存在，则检查 token 查询参数 (静态 Token)。
    """
    auth_header = request.headers.get("Authorization")
    token_query = request.query_params.get("token")

    user = None
    if auth_header and auth_header.lower().startswith("bearer "):
        jwt_token = auth_header.split(" ")[1]
        user = get_current_user_from_jwt(jwt_token, db)
    elif token_query:
        user = get_user_by_api_token(token_query, db)
    else:
        raise APIException(code=status.HTTP_401_UNAUTHORIZED,
                           msg="Authentication required. Provide Bearer token or API token in query.")

    # 对通过两种方式获取到的用户进行统一的权限检查
    if not user.is_active:
        raise APIException(code=status.HTTP_403_FORBIDDEN, msg="Inactive user")

    return plans.apply_plan_limits(user)