# 文件: app/routers/subscription.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from .. import schemas, models, crud, plans
from ..database import get_db
from ..common.dependencies import get_current_active_user
from ..common.response_model import ResponseModel, APIException

router = APIRouter()


@router.post("/upgrade", response_model=ResponseModel[schemas.UserInfo])
def upgrade_subscription(
    sub_data: schemas.SubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    duration_days = plans.PLANS_PRICING.get(sub_data.plan, {}).get(sub_data.duration)
    if not duration_days:
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg="Invalid plan or duration")

    try:
        updated_user = plans.grant_subscription(current_user, sub_data.plan, duration_days)
        crud.update_user(db, user=updated_user)
        return ResponseModel(data=updated_user)
    except ValueError as e:
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg=str(e))


@router.get("/plans", response_model=ResponseModel[dict])
def get_available_plans():
    return ResponseModel(data=plans.PLANS_CONFIG)