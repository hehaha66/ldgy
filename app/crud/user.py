# 文件: app/crud/user.py (最终清理版)
from typing import Optional

from sqlalchemy.orm import Session
import datetime
import secrets

from .. import models, schemas
from ..common.dependencies import get_password_hash, verify_password


# from ..plans import grant_subscription # <- 已移除未使用的 import

# PEP 8: 函数之间空两行
def get_user_by_id(db: Session, user_id: int):
    # type: ignore
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    # type: ignore
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str):
    # type: ignore
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_api_token(db: Session, api_token: str):
    # type: ignore
    return db.query(models.User).filter(models.User.api_token == api_token).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).order_by(models.User.id).offset(skip).limit(limit).all()


def create_user(db: Session, user_data: schemas.UserCreate) -> models.User:
    """
    创建新用户，并立即为其生成一个唯一的、永久的 freemium API Token。
    """
    hashed_password = get_password_hash(user_data.password)
    username_to_set = user_data.username or user_data.email

    new_api_token = f"ldst_free_{secrets.token_urlsafe(24)}"

    db_user = models.User(
        username=username_to_set,
        email=user_data.email,
        hashed_password=hashed_password,
        api_token=new_api_token,
        plan="freemium"
    )
    db.add(db_user)
    return db_user


def update_user(db: Session, user: models.User):
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int):
    db_obj = db.query(models.User).get(user_id)
    if db_obj:
        db.delete(db_obj)
        db.commit()
    return db_obj


def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    user = get_user_by_email(db, email=email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_or_update_verification_code(db: Session, email: str, code: str, expires: datetime.datetime):
    # type: ignore
    code_obj = db.query(models.VerificationCode).filter(models.VerificationCode.email == email).first()
    if code_obj:
        code_obj.code = code
        code_obj.expires_at = expires
    else:
        code_obj = models.VerificationCode(email=email, code=code, expires_at=expires)
    db.add(code_obj)
    return code_obj


def get_verification_code(db: Session, email: str):
    # type: ignore
    return db.query(models.VerificationCode).filter(models.VerificationCode.email == email).first()


def delete_verification_code(db: Session, email: str):
    # type: ignore
    db.query(models.VerificationCode).filter(models.VerificationCode.email == email).delete()

def get_user_by_api_token(db: Session, api_token: str) -> Optional[models.User]:
    """通过 API Token 查找用户。"""
    return db.query(models.User).filter(models.User.api_token == api_token).first()
