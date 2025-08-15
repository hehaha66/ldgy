# 文件: app/models.py (最终修正版 - 添加ForeignKey)

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey  # 导入 ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    plan = Column(String(20), default="freemium", nullable=False)
    expires_at = Column(DateTime, nullable=True)
    api_token = Column(String(100), unique=True, index=True, nullable=True)
    nickname = Column(String(50), nullable=True)

    # 定义关系：一个用户可以拥有多个工作区
    workspaces = relationship("MonitorWorkspace", back_populates="owner")


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    code = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)


class MonitorWorkspace(Base):
    __tablename__ = "monitor_workspaces"
    id = Column(Integer, primary_key=True, index=True)
    # 【核心修正1】明确定义 user_id 是一个指向 'users.id' 的外键
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    entities = relationship("WorkspaceEntity", back_populates="workspace", cascade="all, delete-orphan")
    # 定义反向关系，方便从工作区访问其拥有者
    owner = relationship("User", back_populates="workspaces")


class WorkspaceEntity(Base):
    __tablename__ = "workspace_entities"
    id = Column(Integer, primary_key=True, index=True)
    # 【核心修正2】明确定义 workspace_id 是一个指向 'monitor_workspaces.id' 的外键
    workspace_id = Column(Integer, ForeignKey("monitor_workspaces.id"), index=True, nullable=False)
    entity_type = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    definition = Column(JSON, nullable=False)
    display_order = Column(Integer, default=0)

    workspace = relationship("MonitorWorkspace", back_populates="entities")