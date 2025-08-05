# 文件: app/routers/admin.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from .. import schemas, crud, models
from ..database import get_db
from ..common.dependencies import get_current_active_superuser
from ..common.response_model import ResponseModel, APIException


router = APIRouter(dependencies=[Depends(get_current_active_superuser)])


@router.get("/users", response_model=ResponseModel[List[schemas.UserInfo]])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有用户列表（仅限超级管理员）。"""
    users = crud.get_users(db, skip=skip, limit=limit)
    return ResponseModel(data=users)


@router.put("/users/{user_id}/authorize", response_model=ResponseModel[schemas.UserInfo])
def authorize_user(user_id: int, user_in: schemas.UserAuthorizeUpdate, db: Session = Depends(get_db)):
    """授权或取消用户的超级管理员权限。"""
    user = crud.get_user_by_id(db, user_id=user_id)
    if not user:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="User not found")

    user.is_superuser = user_in.is_superuser
    updated_user = crud.update_user(db, user)
    return ResponseModel(data=updated_user)


@router.put("/users/{user_id}/status", response_model=ResponseModel[schemas.UserInfo])
def update_user_status(user_id: int, user_in: schemas.UserStatusUpdate, db: Session = Depends(get_db)):
    """激活或禁用用户账户。"""
    user = crud.get_user_by_id(db, user_id=user_id)
    if not user:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="User not found")

    user.is_active = user_in.is_active
    updated_user = crud.update_user(db, user)
    return ResponseModel(data=updated_user)


@router.delete("/users/{user_id}", response_model=ResponseModel[schemas.UserInfo])
def delete_user_route(user_id: int, db: Session = Depends(get_db)):
    """删除一个用户。"""
    user = crud.delete_user(db, user_id=user_id)
    if not user:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="User not found")

    return ResponseModel(data=user, msg="User deleted successfully")