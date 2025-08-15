# 文件: app/routers/admin.py (最终修正版 - 兼容原有代码)

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from .. import schemas, crud, models, plans  # 确保导入了 plans
from ..database import get_db
from ..common.dependencies import get_current_active_superuser
from ..common.response_model import ResponseModel, APIException

router = APIRouter(dependencies=[Depends(get_current_active_superuser)])


# 定义一个辅助函数，专门用于为用户对象附加完整的权限信息
# 这是一个好的实践，可以避免在多个地方重复代码
def enrich_user_with_permissions(user: models.User) -> Dict[str, Any]:
    """将数据库用户对象转换为包含完整权限信息的字典。"""
    user_plan_config = plans.PLANS_CONFIG.get(user.plan, plans.PLANS_CONFIG["freemium"])

    # 手动创建一个字典，包含所有 UserInfo 和 UserOut 中定义的字段
    response_data = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "nickname": getattr(user, 'nickname', None),
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "plan": user.plan,
        "expires_at": user.expires_at,
        "api_token": user.api_token,
        **user_plan_config  # 合并权限配置
    }
    return response_data


# 【【核心修改点 1】】
# 修改了 response_model 来适应我们返回的、更丰富的数据结构
@router.get("/users", response_model=ResponseModel[Dict[str, Any]])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有用户列表（仅限超级管理员）。"""
    users = crud.get_users(db, skip=skip, limit=limit)
    total = db.query(models.User).count()  # 获取总数，以便未来做分页

    # 【【核心修改点 2】】
    # 遍历用户列表，为每个用户附加权限信息
    users_with_permissions = [enrich_user_with_permissions(user) for user in users]

    # 返回一个包含了 users 列表和 total 数量的字典
    return ResponseModel(data={"users": users_with_permissions, "total": total})


# 【【核心修改点 3】】
# 后续所有返回 UserInfo 的接口，都应该返回包含了完整权限的数据
# 我们修改 response_model 并使用辅助函数
@router.put("/users/{user_id}/authorize", response_model=ResponseModel[schemas.UserOut])
def authorize_user(user_id: int, user_in: schemas.UserAuthorizeUpdate, db: Session = Depends(get_db)):
    """授权或取消用户的超级管理员权限。"""
    user = crud.get_user_by_id(db, user_id=user_id)
    if not user:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="User not found")

    user.is_superuser = user_in.is_superuser
    # 如果设为管理员，plan也应对应调整
    if user.is_superuser:
        user.plan = 'admin'
    else:
        user.plan = 'freemium'  # 取消管理员后，可以降级为免费版

    updated_user = crud.update_user(db, user)

    return ResponseModel(data=enrich_user_with_permissions(updated_user))


@router.put("/users/{user_id}/status", response_model=ResponseModel[schemas.UserOut])
def update_user_status(user_id: int, user_in: schemas.UserStatusUpdate, db: Session = Depends(get_db)):
    """激活或禁用用户账户。"""
    user = crud.get_user_by_id(db, user_id=user_id)
    if not user:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="User not found")

    user.is_active = user_in.is_active
    updated_user = crud.update_user(db, user)

    return ResponseModel(data=enrich_user_with_permissions(updated_user))


@router.delete("/users/{user_id}", response_model=ResponseModel)
def delete_user_route(user_id: int, db: Session = Depends(get_db)):
    """删除一个用户。"""
    # 删除操作的返回可以保持简单
    user = crud.get_user_by_id(db, user_id=user_id)
    if not user:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="User not found")
    if user.is_superuser:
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg="不能删除管理员账户")

    crud.delete_user(db, user_id=user_id)
    return ResponseModel(msg=f"User (ID: {user_id}) deleted successfully")