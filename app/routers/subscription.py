# 文件: app/routers/subscription.py (最终修正版)

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from .. import schemas, models, crud, plans
from ..database import get_db
# 确保导入了正确的依赖
from ..common.dependencies import get_current_active_user, get_user_from_header_or_query
from ..common.response_model import ResponseModel, APIException

router = APIRouter()


@router.post("/upgrade", response_model=ResponseModel[schemas.UserOut])  # 【优化】返回完整的 UserOut 模型
def upgrade_subscription(
        sub_data: schemas.SubscriptionRequest,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    if current_user.is_superuser:
        raise APIException(
            code=status.HTTP_403_FORBIDDEN,  # 返回 403 禁止访问错误
            msg="管理员账户不能执行升级操作，您已拥有最高权限。"
        )
    plan_pricing = plans.PLANS_PRICING.get(sub_data.plan)
    if not plan_pricing:
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg="无效的套餐名称")

    duration_info = plan_pricing.get(sub_data.duration)
    if not duration_info:
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg="无效的订阅时长 (请使用 'monthly' 或 'yearly')")

    duration_days = duration_info['days']

    try:
        updated_user = plans.grant_subscription(current_user, sub_data.plan, duration_days)
        updated_user = plans.reset_api_token(updated_user)
        crud.update_user(db, user=updated_user)
        from .auth import get_full_user_response_data  # 导入辅助函数
        full_user_info = get_full_user_response_data(updated_user)
        return ResponseModel(data=full_user_info, msg="套餐升级成功！")

    except ValueError as e:
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg=str(e))


@router.get("/plans", response_model=ResponseModel[dict])
def get_available_plans():
    # 这个接口无需修改，保持原样即可
    return ResponseModel(data=plans.PLANS_CONFIG)