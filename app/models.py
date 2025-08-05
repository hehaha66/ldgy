# 文件: app/models.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from .database import Base
import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # --- 权限和订阅相关字段 ---
    plan = Column(String, default="freemium", nullable=False)
    expires_at = Column(DateTime, nullable=True)  # null 表示永不过期
    api_token = Column(String, unique=True, index=True, nullable=True)


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)